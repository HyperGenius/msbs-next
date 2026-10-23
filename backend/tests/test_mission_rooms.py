"""作戦ルームのエントリー・マッチング・バッチ実行のテスト."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.core.auth import get_current_user
from app.models.models import (
    BattleEntry,
    BattleResult,
    BattleRoom,
    Mission,
    MobileSuit,
    Team,
    TeamMember,
    Vector3,
    Weapon,
)
from app.services.battle_room_service import BattleRoomService
from app.services.drop_service import DropScope, DropService
from app.services.matching_service import MatchingService
from main import app
from scripts import run_batch

USER_ID = "test_mission_user"
MISSION_ID = 501


def _make_suit(session: Session, user_id: str = USER_ID) -> MobileSuit:
    suit = MobileSuit(
        name="Hero",
        user_id=user_id,
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[Weapon(id="w1", name="Beam Rifle", power=300, range=600, accuracy=90)],
        side="PLAYER",
    )
    session.add(suit)
    session.commit()
    session.refresh(suit)
    return suit


def _make_mission(
    session: Session, mission_id: int = MISSION_ID, is_active: bool = True
) -> Mission:
    mission = Mission(
        id=mission_id,
        name=f"作戦 {mission_id}",
        description="テスト用の作戦",
        environment="GROUND",
        enemy_config={
            "enemies": [
                {
                    "name": "追撃機",
                    "max_hp": 50,
                    "role": "VANGUARD",
                    "squad_id": "alpha",
                    "position": {"x": 1500, "y": 0, "z": 1500},
                }
            ]
        },
        allies_config=[{"name": "負傷機", "max_hp": 300, "role": "WITHDRAW"}],
        layout={
            "retreat_points": [
                {
                    "position": {"x": 200, "y": 0, "z": 200},
                    "radius": 150,
                    "team_id": "PLAYER",
                }
            ]
        },
        is_active=is_active,
    )
    session.add(mission)
    session.commit()
    session.refresh(mission)
    return mission


@pytest.fixture(name="user_client")
def user_client_fixture(client: TestClient) -> Iterator[TestClient]:
    """ログイン済みのクライアントを返す."""
    app.dependency_overrides[get_current_user] = lambda: USER_ID
    yield client


def _rooms(session: Session) -> list[BattleRoom]:
    session.expire_all()
    return list(session.exec(select(BattleRoom)).all())


def _entries(session: Session) -> list[BattleEntry]:
    return list(session.exec(select(BattleEntry)).all())


# --- エントリー ---


def test_entry_without_mission_goes_to_battle_royale(
    user_client: TestClient, session: Session
) -> None:
    """作戦ID なしのエントリーは、今どおりデイリーバトルロイヤルのルームに入る."""
    suit = _make_suit(session)

    body = user_client.post("/api/entries", json={"mobile_suit_id": str(suit.id)})

    assert body.status_code == 200
    assert body.json()["mission_id"] is None
    [room] = _rooms(session)
    assert room.mission_id is None
    assert str(room.id) == body.json()["room_id"]


def test_entry_with_mission_creates_mission_room(
    user_client: TestClient, session: Session
) -> None:
    """作戦ID を付けると、同じ開催・同じ戦域の作戦ルームを作って入る."""
    suit = _make_suit(session)
    _make_mission(session)

    body = user_client.post(
        "/api/entries",
        json={"mobile_suit_id": str(suit.id), "mission_id": MISSION_ID},
    ).json()

    assert body["mission_id"] == MISSION_ID
    rooms = _rooms(session)
    open_room = next(r for r in rooms if r.mission_id is None)
    mission_room = next(r for r in rooms if r.mission_id == MISSION_ID)
    assert body["room_id"] == str(mission_room.id)
    assert mission_room.status == "OPEN"
    assert mission_room.scheduled_at == open_room.scheduled_at
    assert mission_room.theater_id == open_room.theater_id
    assert mission_room.minovsky_density == open_room.minovsky_density
    # 作戦ルームはバトルロイヤルの募集中ルームとして扱わない
    assert BattleRoomService.find_open_room(session) == open_room


@pytest.mark.parametrize("is_active", [True, False])
def test_entry_rejects_missing_or_inactive_mission(
    user_client: TestClient, session: Session, is_active: bool
) -> None:
    """無い作戦・無効な作戦にはエントリーできない."""
    suit = _make_suit(session)
    if not is_active:
        _make_mission(session, is_active=False)

    response = user_client.post(
        "/api/entries",
        json={"mobile_suit_id": str(suit.id), "mission_id": MISSION_ID},
    )

    assert response.status_code == 404
    assert _entries(session) == []


def test_entry_switches_between_battle_royale_and_mission(
    user_client: TestClient, session: Session
) -> None:
    """1開催に出られるのはどちらか1つ。出撃先を変えると前のエントリーを消す."""
    suit = _make_suit(session)
    _make_mission(session)
    _make_mission(session, mission_id=MISSION_ID + 1)

    def enter(mission_id: int | None) -> None:
        response = user_client.post(
            "/api/entries",
            json={"mobile_suit_id": str(suit.id), "mission_id": mission_id},
        )
        assert response.status_code == 200

    enter(None)
    enter(MISSION_ID)
    [entry] = _entries(session)
    assert session.get(BattleRoom, entry.room_id).mission_id == MISSION_ID  # type: ignore[union-attr]

    # 別の作戦に変えると、前の作戦ルームは消える
    enter(MISSION_ID + 1)
    assert sorted(r.mission_id or 0 for r in _rooms(session)) == [0, MISSION_ID + 1]

    # 同じ作戦なら機体を上書きするだけで、ルームは作り直さない
    mission_room_id = _entries(session)[0].room_id
    enter(MISSION_ID + 1)
    [entry] = _entries(session)
    assert entry.room_id == mission_room_id

    enter(None)
    [entry] = _entries(session)
    assert [r.mission_id for r in _rooms(session)] == [None]


def test_status_and_cancel_mission_entry(
    user_client: TestClient, session: Session
) -> None:
    """作戦のエントリーも状況に出て、キャンセルすると作戦ルームも消える."""
    suit = _make_suit(session)
    _make_mission(session)
    user_client.post(
        "/api/entries",
        json={"mobile_suit_id": str(suit.id), "mission_id": MISSION_ID},
    )

    status = user_client.get("/api/entries/status").json()
    assert status["is_entered"] is True
    assert status["entry"]["mission_id"] == MISSION_ID
    # 次回の開催はバトルロイヤルのルームを返す
    open_room = BattleRoomService.find_open_room(session)
    assert open_room is not None
    assert status["next_room"]["id"] == str(open_room.id)
    # 待機人数はバトルロイヤルのルームだけ数える
    assert user_client.get("/api/entries/count").json() == {"count": 0}

    assert user_client.delete("/api/entries").status_code == 200
    assert _entries(session) == []
    assert [r.mission_id for r in _rooms(session)] == [None]
    assert user_client.get("/api/entries/status").json()["is_entered"] is False
    assert user_client.delete("/api/entries").status_code == 404


def test_team_entry_rejects_member_in_mission(
    user_client: TestClient, session: Session
) -> None:
    """作戦にエントリー済みのメンバーがいると、チームでエントリーできない."""
    suit = _make_suit(session)
    _make_suit(session, user_id="teammate")
    _make_mission(session)
    user_client.post(
        "/api/entries",
        json={"mobile_suit_id": str(suit.id), "mission_id": MISSION_ID},
    )
    team = Team(name="T", owner_user_id=USER_ID, status="READY")
    session.add(team)
    session.commit()
    session.refresh(team)
    for member in (USER_ID, "teammate"):
        session.add(TeamMember(team_id=team.id, user_id=member, is_ready=True))
    session.commit()

    response = user_client.post(
        "/api/teams/entry",
        json={"team_id": str(team.id), "mobile_suit_id": str(suit.id)},
    )

    assert response.status_code == 409
    assert len(_entries(session)) == 1


# --- マッチング ---


def _make_mission_room(
    session: Session, scheduled_at: datetime, with_entry: bool = True
) -> BattleRoom:
    open_room, _ = BattleRoomService.get_or_create_open_room(session)
    room = BattleRoomService.create_mission_room(session, open_room, MISSION_ID)
    room.scheduled_at = scheduled_at
    session.add(room)
    if with_entry:
        suit = _make_suit(session)
        session.add(
            BattleEntry(
                user_id=USER_ID,
                room_id=room.id,
                mobile_suit_id=suit.id,
                mobile_suit_snapshot=suit.model_dump(mode="json"),
            )
        )
    session.commit()
    session.refresh(room)
    return room


def test_matching_does_not_fill_mission_room_with_npcs(session: Session) -> None:
    """作戦ルームは NPC で埋めずに実行待ちにする."""
    _make_mission(session)
    room = _make_mission_room(session, datetime.now(UTC) - timedelta(hours=1))

    created = MatchingService(session, room_size=10).create_rooms()

    assert room in created
    session.refresh(room)
    assert room.status == "WAITING"
    entries = session.exec(
        select(BattleEntry).where(BattleEntry.room_id == room.id)
    ).all()
    assert [e.is_npc for e in entries] == [False]


def test_matching_removes_empty_mission_room(session: Session) -> None:
    """エントリーの無い作戦ルームは延期せずに消す."""
    _make_mission(session)
    past = datetime.now(UTC) - timedelta(hours=1)
    room = _make_mission_room(session, past, with_entry=False)
    room_id = room.id

    MatchingService(session, room_size=10).create_rooms()

    session.expire_all()
    assert session.get(BattleRoom, room_id) is None
    # バトルロイヤルの空のルームは残す
    assert BattleRoomService.find_open_room(session) is not None


# --- バッチ実行 ---


def test_process_mission_room_saves_objective_result(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """作戦ルームを作戦マスターの敵・友軍で実行し、作戦の結果つきで保存する."""
    _make_mission(session)
    room = _make_mission_room(session, datetime.now(UTC))
    room.status = "WAITING"
    room.theater_id = None
    room.minovsky_density = None
    session.add(room)
    session.commit()
    scopes: list[DropScope] = []

    def fake_roll(session, user_id, scope, **kwargs):  # type: ignore[no-untyped-def]
        scopes.append(scope)
        return []

    monkeypatch.setattr(DropService, "roll", fake_roll)
    monkeypatch.setattr(run_batch, "_MAX_SIMULATION_STEPS", 30)

    run_batch._process_room(session, room)

    result = session.exec(
        select(BattleResult).where(BattleResult.room_id == room.id)
    ).one()
    assert result.mission_id == MISSION_ID
    assert result.objective_status in ("SUCCESS", "FAILURE", "DRAW")
    assert result.objective_progress == 0
    assert result.objective_required == 0
    assert (
        result.win_loss
        == {"SUCCESS": "WIN", "FAILURE": "LOSE", "DRAW": "DRAW"}[
            result.objective_status
        ]
    )
    # 戦域の無い開催は作戦の環境で戦う
    assert result.environment == "GROUND"
    assert result.enemies_info is not None
    assert sorted(u["name"] for u in result.enemies_info) == ["負傷機", "追撃機"]
    assert scopes == [DropScope.mission(MISSION_ID)]
    session.refresh(room)
    assert room.status == "COMPLETED"
    # 作戦の敵機・友軍はエントリーとして保存しない
    assert not session.exec(
        select(BattleEntry).where(
            BattleEntry.room_id == room.id, col(BattleEntry.is_npc)
        )
    ).all()


def test_batch_runs_mission_and_battle_royale_rooms(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """デイリーバッチは、バトルロイヤルのルームと作戦ルームを両方実行する."""
    _make_mission(session)
    mission_room = _make_mission_room(session, datetime.now(UTC))
    open_room = BattleRoomService.find_open_room(session)
    assert open_room is not None
    other = _make_suit(session, user_id="royale_user")
    session.add(
        BattleEntry(
            user_id="royale_user",
            room_id=open_room.id,
            mobile_suit_id=other.id,
            mobile_suit_snapshot=other.model_dump(mode="json"),
        )
    )
    session.commit()
    monkeypatch.setattr(run_batch, "_MAX_SIMULATION_STEPS", 5)

    run_batch.run_matching_phase(session)
    run_batch.run_simulation_phase(session)

    results = session.exec(select(BattleResult)).all()
    by_room = {r.room_id: r for r in results}
    assert by_room[mission_room.id].mission_id == MISSION_ID
    assert by_room[open_room.id].mission_id is None
    # バトルロイヤルにも殲滅の結果を保存する
    assert by_room[open_room.id].objective_status in ("SUCCESS", "FAILURE")


# --- 作戦の一覧 ---


def test_available_missions_lists_active_missions(
    client: TestClient, session: Session
) -> None:
    """有効な作戦だけを、次回の開催の戦域と一緒に返す."""
    _make_mission(session)
    _make_mission(session, mission_id=MISSION_ID + 1, is_active=False)
    room, _ = BattleRoomService.get_or_create_open_room(session)
    room.theater_id = "southeast_asia_jungle"
    room.minovsky_density = 0.4
    session.add(room)
    session.commit()

    body = client.get("/api/missions/available").json()

    assert body["theater"]["theater_id"] == "southeast_asia_jungle"
    [mission] = body["missions"]
    assert mission["id"] == MISSION_ID
    assert mission["objective_type"] == "ANNIHILATION"
    assert mission["environment"] == "FOREST"
    assert (mission["ally_count"], mission["enemy_count"]) == (1, 1)


def test_objective_fields_include_viewer_data() -> None:
    """撤退ポイントとロールを objective_detail に入れ、友軍を数えない目標でも渡す."""
    from types import SimpleNamespace

    from app.engine.objectives import ObjectiveResult, ObjectiveStatus
    from app.engine.unit_roles import UnitAssignment
    from app.models.models import RetreatPoint, Vector3

    simulator = SimpleNamespace(
        retreat_points=[
            RetreatPoint(position=Vector3(x=1, y=0, z=2), radius=50, team_id="PLAYER")
        ],
        unit_assignments={
            "a": UnitAssignment(role="WITHDRAW"),
            "b": UnitAssignment(squad_id="s1"),
        },
    )
    result = ObjectiveResult(status=ObjectiveStatus.SUCCESS, progress=2, required=2)

    fields = run_batch._objective_fields(result, simulator)  # type: ignore[arg-type]
    detail = fields["objective_detail"]
    assert detail["retreat_points"] == [
        {"position": {"x": 1.0, "y": 0.0, "z": 2.0}, "radius": 50, "team_id": "PLAYER"}
    ]
    # ロールが無いユニットは含めない
    assert detail["unit_roles"] == {"a": "WITHDRAW"}

    # シミュレーターを渡さない・撤退ポイントもロールも無いときは従来どおり
    assert run_batch._objective_fields(result)["objective_detail"] is None
    empty = SimpleNamespace(retreat_points=[], unit_assignments={})
    assert run_batch._objective_fields(result, empty)["objective_detail"] is None  # type: ignore[arg-type]

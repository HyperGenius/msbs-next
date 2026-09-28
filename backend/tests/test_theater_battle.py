"""定期バトルへの戦域の適用と、バトル結果への記録のテスト."""

import logging
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth import get_current_user, get_current_user_optional
from app.engine.simulation import BattleSimulator
from app.models.models import (
    BattleEntry,
    BattleResult,
    BattleRoom,
    MobileSuit,
    Vector3,
    Weapon,
)
from app.services.theater_service import BattleConditions, TheaterService
from main import app
from scripts import run_batch

USER_ID = "test_theater_user"


def _make_unit(name: str, side: str) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[Weapon(id="w1", name="Beam Rifle", power=100, range=500, accuracy=80)],
        side=side,
    )


# --- 戦闘条件の組み立て ---


def test_conditions_without_theater_are_legacy(session: Session) -> None:
    """戦域の無いルームは宇宙・濃度0・障害物 MEDIUM で戦う."""
    conditions = TheaterService.battle_conditions(session, None, None)

    assert conditions == BattleConditions()
    sim = BattleSimulator(
        _make_unit("A", "PLAYER"),
        [_make_unit("B", "ENEMY")],
        **conditions.simulator_kwargs(),
    )
    assert sim.environment == "SPACE"
    assert sim.environment_profile is None
    assert sim.minovsky_density == 0.0
    assert sim.battlefield.obstacle_density == "MEDIUM"


def test_conditions_of_forest_theater(session: Session) -> None:
    """森林の戦域は環境タイプの効果・濃度・障害物の既定値で戦う."""
    conditions = TheaterService.battle_conditions(
        session, "southeast_asia_jungle", 0.62
    )

    assert conditions.theater_id == "southeast_asia_jungle"
    assert conditions.environment == "FOREST"
    assert conditions.minovsky_density == 0.62
    assert conditions.environment_profile is not None
    assert conditions.environment_profile.sensor_range_multiplier == 0.8

    sim = BattleSimulator(
        _make_unit("A", "PLAYER"),
        [_make_unit("B", "ENEMY")],
        **conditions.simulator_kwargs(),
    )
    assert sim.environment == "FOREST"
    assert sim.minovsky_density == 0.62
    assert sim.battlefield.obstacle_density == "DENSE"


def test_conditions_use_theater_obstacle_density(session: Session) -> None:
    """戦域が障害物密度を指定したら、環境タイプの既定値より優先する."""
    from app.models.models import MasterTheater

    jungle = session.get(MasterTheater, "southeast_asia_jungle")
    assert jungle is not None
    jungle.obstacle_density = "SPARSE"
    session.add(jungle)
    session.commit()

    conditions = TheaterService.battle_conditions(session, "southeast_asia_jungle", 0.6)
    sim = BattleSimulator(
        _make_unit("A", "PLAYER"),
        [_make_unit("B", "ENEMY")],
        **conditions.simulator_kwargs(),
    )
    assert sim.battlefield.obstacle_density == "SPARSE"


def test_conditions_fall_back_when_theater_is_missing(
    session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    """戦域のマスターが無ければ既定の条件で戦い、警告を出す."""
    with caplog.at_level(logging.WARNING):
        conditions = TheaterService.battle_conditions(session, "deleted", 0.5)

    assert conditions == BattleConditions()
    assert "deleted" in caplog.text


def test_conditions_fall_back_when_environment_is_missing(
    session: Session,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """環境タイプのマスターが無ければ既定の条件で戦い、警告を出す."""
    monkeypatch.setattr(TheaterService, "resolve_environment_profile", lambda *_: None)
    with caplog.at_level(logging.WARNING):
        conditions = TheaterService.battle_conditions(session, "solomon", 0.5)

    assert conditions == BattleConditions()
    assert "SPACE" in caplog.text


# --- 定期バトル ---


def test_run_simulation_applies_conditions(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """定期バトルのシミュレーターに戦域の条件を渡す."""
    monkeypatch.setattr(run_batch, "_MAX_SIMULATION_STEPS", 1)
    conditions = TheaterService.battle_conditions(session, "southeast_asia_jungle", 0.6)

    simulator, *_ = run_batch._run_simulation(
        _make_unit("A", "PLAYER"), [_make_unit("B", "ENEMY")], conditions
    )

    assert simulator.environment == "FOREST"
    assert simulator.minovsky_density == 0.6
    assert simulator.battlefield.obstacle_density == "DENSE"


def _make_room_with_entry(
    session: Session, theater_id: str | None, minovsky_density: float | None
) -> tuple[BattleRoom, BattleEntry, MobileSuit]:
    room = BattleRoom(
        status="WAITING",
        scheduled_at=datetime.now(UTC),
        theater_id=theater_id,
        minovsky_density=minovsky_density,
    )
    suit = _make_unit("Hero", "PLAYER")
    snapshot = suit.model_dump(mode="json")
    session.add(room)
    session.add(suit)
    session.commit()
    session.refresh(room)
    entry = BattleEntry(
        user_id=USER_ID,
        room_id=room.id,
        mobile_suit_id=suit.id,
        mobile_suit_snapshot=snapshot,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return room, entry, run_batch._convert_snapshot_to_mobile_suit(dict(snapshot))


@pytest.mark.parametrize(
    ("theater_id", "minovsky_density", "expected"),
    [
        ("southeast_asia_jungle", 0.58, ("FOREST", "southeast_asia_jungle", 0.58)),
        (None, None, ("SPACE", None, 0.0)),
    ],
)
def test_process_room_records_theater(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
    theater_id: str | None,
    minovsky_density: float | None,
    expected: tuple[str, str | None, float],
) -> None:
    """バトル結果に環境タイプ・戦域・濃度を記録する."""
    room, entry, unit = _make_room_with_entry(session, theater_id, minovsky_density)
    simulator = MagicMock()
    simulator.units = [unit]
    simulator.logs = []
    simulator.obstacles = []
    simulator.map_bounds = (0.0, 1000.0)
    captured: dict[str, BattleConditions | None] = {}

    def fake_run_simulation(player_unit, enemy_units, conditions=None):  # type: ignore[no-untyped-def]
        captured["conditions"] = conditions
        return simulator, True, 0, 1

    monkeypatch.setattr(run_batch, "_run_simulation", fake_run_simulation)
    npc = BattleEntry(
        room_id=room.id,
        mobile_suit_id=unit.id,
        mobile_suit_snapshot=_make_unit("NPC", "ENEMY").model_dump(mode="json"),
        is_npc=True,
    )
    session.add(npc)
    session.commit()

    run_batch._process_room(session, room)

    conditions = captured["conditions"]
    assert conditions is not None
    assert (
        conditions.environment,
        conditions.theater_id,
        conditions.minovsky_density,
    ) == expected
    result = session.exec(
        select(BattleResult).where(BattleResult.room_id == room.id)
    ).one()
    assert (result.environment, result.theater_id, result.minovsky_density) == expected


# --- バトル結果の API ---


@pytest.fixture(name="user_client")
def user_client_fixture(client: TestClient) -> TestClient:
    """ログイン済みのクライアントを返す."""
    app.dependency_overrides[get_current_user] = lambda: USER_ID
    app.dependency_overrides[get_current_user_optional] = lambda: USER_ID
    return client


def test_battle_endpoints_include_theater_names(
    user_client: TestClient, session: Session
) -> None:
    """一覧・未読・詳細のレスポンスに戦域名・環境タイプ名・描画プリセットを含める."""
    battle = BattleResult(
        user_id=USER_ID,
        win_loss="WIN",
        environment="FOREST",
        theater_id="southeast_asia_jungle",
        minovsky_density=0.42,
    )
    session.add(battle)
    session.commit()

    history = user_client.get("/api/battles").json()
    unread = user_client.get("/api/battles/unread").json()
    detail = user_client.get(f"/api/battles/{battle.id}").json()

    for body in (history[0], unread[0], detail):
        assert body["theater_id"] == "southeast_asia_jungle"
        assert body["theater_name"] == "東南アジア密林"
        assert body["environment_name"] == "森林"
        assert body["viewer_preset"] == "FOREST"
        assert body["minovsky_density"] == 0.42


def test_labels_for_battles_without_master(session: Session) -> None:
    """戦域の無いバトルやマスターに無い環境タイプは、名前を None にする.

    マスターに無い戦域は、戦域IDを名前にする。
    """
    solo = BattleResult(win_loss="WIN", environment="GROUND")
    legacy = BattleResult(win_loss="WIN")
    deleted_theater = BattleResult(
        win_loss="WIN", environment="SPACE", theater_id="a_baoa_qu"
    )

    labels = TheaterService.labels_for(session, [solo, legacy, deleted_theater])

    assert labels[0].theater_name is None
    assert labels[0].environment_name is None
    assert labels[0].viewer_preset is None
    assert labels[1].theater_name is None
    assert labels[1].environment_name == "宇宙"
    assert labels[1].viewer_preset == "SPACE"
    assert labels[2].theater_name == "a_baoa_qu"

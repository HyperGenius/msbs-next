"""バトルログの書き込み経路（配信用ログの保存と解析用ログの保存）のテスト."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app.core.auth import get_current_user_optional
from app.engine.objectives import AnnihilationObjective
from app.engine.replay_log import REPLAY_LOG_VERSION, to_replay_logs
from app.models.models import (
    BattleEntry,
    BattleLog,
    BattleLogRecord,
    BattleResult,
    BattleRoom,
    Mission,
    MobileSuit,
    Pilot,
    Vector3,
    Weapon,
)
from main import app

USER_ID = "test_write_path_user"
MISSION_ID = 9636
HEADER = {"replay_version": REPLAY_LOG_VERSION}


@pytest.fixture(name="mission")
def mission_fixture(session: Session) -> Iterator[Mission]:
    """ソロミッションを作成する。conftest はミッションを削除しないため後始末する."""
    mission = Mission(
        id=MISSION_ID,
        name="Write Path Mission",
        enemy_config={
            "enemies": [
                {
                    "name": "ボール",
                    "max_hp": 300,
                    "armor": 0,
                    "position": {"x": 300, "y": 0, "z": 0},
                    "weapon": {"power": 1, "range": 100, "accuracy": 1},
                }
            ]
        },
    )
    session.add(mission)
    session.commit()
    yield mission
    session.exec(delete(Mission).where(col(Mission.id) == MISSION_ID))  # type: ignore[call-overload]
    session.commit()


@pytest.fixture(name="analysis_calls")
def analysis_calls_fixture(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """`save_analysis_log` に渡された引数を記録する."""
    calls: list[tuple] = []
    monkeypatch.setattr(
        "main.save_analysis_log", lambda log_id, logs: calls.append((log_id, logs))
    )
    return calls


@pytest.fixture(name="solo_client")
def solo_client_fixture(
    client: TestClient,
    session: Session,
    mission: Mission,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    """ログイン済みでソロミッションを実行できるクライアントを返す."""
    session.add(Pilot(user_id=USER_ID, name="Write Path Pilot", faction="ZEON"))
    session.add(
        MobileSuit(
            user_id=USER_ID,
            name="Zaku",
            max_hp=1000,
            current_hp=1000,
            armor=50,
            mobility=1.5,
            weapons=[Weapon(id="w1", name="MG", power=100, range=500, accuracy=90)],
        )
    )
    session.commit()
    monkeypatch.setattr("main.offload_battle_log_to_gcs", lambda *args: None)
    app.dependency_overrides[get_current_user_optional] = lambda: USER_ID
    return client


def _has_key(entries: list[dict], key: str) -> bool:
    return any(key in entry for entry in entries)


def test_simulate_responds_and_saves_replay_logs(
    solo_client: TestClient, session: Session, analysis_calls: list[tuple]
) -> None:
    """ソロミッションは、配信用ログをレスポンスで返し、DBにも保存する."""
    response = solo_client.post(f"/api/battle/simulate?mission_id={MISSION_ID}")

    assert response.status_code == 200
    logs = response.json()["logs"]
    assert logs[0] == HEADER
    assert len(logs) > 1
    assert not _has_key(logs, "fuzzy_scores")
    assert not any(entry.get("action_type") == "AI_DECISION" for entry in logs)

    result = session.exec(
        select(BattleResult).where(BattleResult.user_id == USER_ID)
    ).one()
    record = session.get(BattleLogRecord, result.battle_log_id)
    assert record is not None
    assert record.logs == logs

    replay = solo_client.get(f"/api/battles/{result.id}/logs")
    assert replay.status_code == 200
    assert replay.text.splitlines()[0] == '{"replay_version": 1}'


def test_simulate_saves_engine_logs_as_analysis_log(
    solo_client: TestClient, session: Session, analysis_calls: list[tuple]
) -> None:
    """解析用ログには、配信用に変換する前のエンジンのログを渡す."""
    response = solo_client.post(f"/api/battle/simulate?mission_id={MISSION_ID}")
    assert response.status_code == 200

    result = session.exec(
        select(BattleResult).where(BattleResult.user_id == USER_ID)
    ).one()
    assert len(analysis_calls) == 1
    log_id, engine_logs = analysis_calls[0]
    assert log_id == result.battle_log_id
    assert all(isinstance(log, BattleLog) for log in engine_logs)
    assert to_replay_logs(engine_logs) == response.json()["logs"]


def test_simulate_succeeds_when_analysis_upload_fails(
    solo_client: TestClient, session: Session
) -> None:
    """解析用ログの保存に失敗しても、戦闘結果は保存される.

    conftest が GCS への接続を止めているため、実際の保存処理は失敗する。
    """
    response = solo_client.post(f"/api/battle/simulate?mission_id={MISSION_ID}")

    assert response.status_code == 200
    assert session.exec(
        select(BattleResult).where(BattleResult.user_id == USER_ID)
    ).one()


def _make_batch_entry(session: Session, room: BattleRoom) -> BattleEntry:
    suit = MobileSuit(
        user_id=USER_ID,
        name="Batch MS",
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[Weapon(id="w1", name="MG", power=100, range=500, accuracy=80)],
    )
    session.add(suit)
    session.commit()
    session.refresh(suit)
    entry = BattleEntry(
        user_id=USER_ID,
        room_id=room.id,
        mobile_suit_id=suit.id,
        mobile_suit_snapshot=suit.model_dump(mode="json"),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def test_batch_saves_replay_logs_and_analysis_log(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """バッチは配信用ログを保存し、コミットの後に解析用ログを保存する."""
    from app.services.battle_execution import snapshot_to_mobile_suit
    from scripts.run_batch import _save_battle_results

    room = BattleRoom(status="WAITING", scheduled_at=datetime.now(UTC))
    session.add(room)
    session.commit()
    session.refresh(room)
    entry = _make_batch_entry(session, room)
    unit = snapshot_to_mobile_suit(dict(entry.mobile_suit_snapshot))
    unit.team_id = str(unit.id)
    engine_logs = [
        BattleLog(
            timestamp=0.1,
            actor_id=unit.id,
            action_type="AI_DECISION",
            message="decide",
            position_snapshot=Vector3(x=0, y=0, z=0),
            fuzzy_scores={"attack": 0.8},
        ),
        BattleLog(
            timestamp=0.1,
            actor_id=unit.id,
            action_type="MOVE",
            message="move",
            position_snapshot=Vector3(x=1, y=0, z=0),
        ),
    ]
    simulator = MagicMock()
    simulator.units = [unit]
    simulator.logs = engine_logs
    simulator.evaluate_objective.side_effect = (
        lambda team_id: AnnihilationObjective().evaluate([unit], {}, team_id)
    )
    simulator.obstacles = []
    simulator.map_bounds = (0.0, 1000.0)

    analysis_calls: list[tuple] = []

    def save_and_check_committed(log_id: uuid.UUID, logs: list[BattleLog]) -> None:
        # 別のセッションから見えれば、コミット済みである。
        with Session(session.get_bind()) as other:
            assert other.get(BattleLogRecord, log_id) is not None
        analysis_calls.append((log_id, logs))

    monkeypatch.setattr("scripts.run_batch.save_analysis_log", save_and_check_committed)

    _save_battle_results(
        session=session,
        room=room,
        player_entries=[entry],
        npc_entries=[],
        simulator=simulator,
        primary_player_win=True,
        player_unit=unit,
        enemy_units=[],
    )

    result = session.exec(
        select(BattleResult).where(BattleResult.room_id == room.id)
    ).one()
    record = session.get(BattleLogRecord, result.battle_log_id)
    assert record is not None
    assert record.logs == to_replay_logs(engine_logs)
    assert record.logs[0] == HEADER
    assert analysis_calls == [(record.id, engine_logs)]

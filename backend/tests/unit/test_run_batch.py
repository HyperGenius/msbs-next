"""Tests for run_batch._save_battle_results."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.db import json_serializer
from app.models.models import (
    BattleEntry,
    BattleResult,
    BattleRoom,
    MobileSuit,
    Vector3,
    Weapon,
)


@pytest.fixture
def in_memory_session():
    """Create an in-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:", json_serializer=json_serializer)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_snapshot(name: str = "Test Gundam") -> dict:
    suit = MobileSuit(
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[Weapon(id="w1", name="Beam Rifle", power=100, range=500, accuracy=80)],
        side="PLAYER",
    )
    return suit.model_dump()


def _make_room(session: Session) -> BattleRoom:
    from datetime import UTC, datetime

    room = BattleRoom(status="WAITING", scheduled_at=datetime.now(UTC))
    session.add(room)
    session.commit()
    session.refresh(room)
    return room


def _make_entry(
    session: Session, room: BattleRoom, user_id: str, snapshot: dict
) -> BattleEntry:
    suit = MobileSuit(
        name=snapshot["name"],
        max_hp=snapshot["max_hp"],
        current_hp=snapshot["current_hp"],
        armor=snapshot["armor"],
        mobility=snapshot["mobility"],
        position=Vector3(x=0, y=0, z=0),
        weapons=[Weapon(id="w1", name="Beam Rifle", power=100, range=500, accuracy=80)],
        side="PLAYER",
    )
    session.add(suit)
    session.commit()
    session.refresh(suit)

    entry = BattleEntry(
        user_id=user_id,
        room_id=room.id,
        mobile_suit_id=suit.id,
        mobile_suit_snapshot=snapshot,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def _make_simulator_mock(units, logs=None):
    sim = MagicMock()
    sim.units = units
    sim.logs = logs or []
    return sim


def test_save_battle_results_sets_detail_fields(in_memory_session):
    """BattleResult に詳細フィールドが正しくセットされること."""
    from sqlmodel import select

    from scripts.run_batch import _save_battle_results

    session = in_memory_session
    room = _make_room(session)

    snapshot = _make_snapshot("Hero Gundam")
    # スナップショットの team_id を明示的にセット（勝利判定のため）
    entry_suit = MobileSuit(
        **{k: v for k, v in snapshot.items() if k in MobileSuit.model_fields}
    )
    snapshot["team_id"] = (
        str(entry_suit.id) if entry_suit.team_id is None else entry_suit.team_id
    )

    entry = _make_entry(session, room, "user_hero", snapshot)

    # シミュレーター: エントリー機体が生存（勝利）
    from scripts.run_batch import _convert_snapshot_to_mobile_suit

    alive_unit = _convert_snapshot_to_mobile_suit(dict(snapshot))
    alive_unit.current_hp = 500
    alive_unit.team_id = snapshot["team_id"]

    simulator = _make_simulator_mock([alive_unit])

    player_unit = _convert_snapshot_to_mobile_suit(dict(snapshot))
    player_unit.side = "PLAYER"
    player_unit.team_id = snapshot["team_id"]

    _save_battle_results(
        session=session,
        room=room,
        player_entries=[entry],
        npc_entries=[],
        simulator=simulator,
        primary_player_win=True,
        kills=1,
        player_unit=player_unit,
        enemy_units=[],
    )

    results = list(
        session.exec(select(BattleResult).where(BattleResult.room_id == room.id)).all()
    )
    assert len(results) == 1
    result = results[0]

    # 詳細フィールドが保存されていること
    assert result.ms_snapshot is not None
    assert result.ms_snapshot["name"] == "Hero Gundam"
    assert result.kills == 1
    assert result.exp_gained > 0
    assert result.credits_gained > 0
    assert result.level_before == 1  # 新規パイロットのデフォルトレベル
    assert result.level_after >= result.level_before
    assert result.level_up == (result.level_after > result.level_before)
    assert result.is_read is False
    assert result.win_loss == "WIN"


def test_save_battle_results_lose(in_memory_session):
    """敗北時は kills=0、報酬が少ないこと."""
    from sqlmodel import select

    from scripts.run_batch import _convert_snapshot_to_mobile_suit, _save_battle_results

    session = in_memory_session
    room = _make_room(session)

    snapshot = _make_snapshot("Loser Zaku")
    snapshot["team_id"] = str(uuid4())  # 生存チームに含まれないID

    entry = _make_entry(session, room, "user_loser", snapshot)

    # 生存ユニットに entry のチームIDを含めない（敗北）
    other_unit = MobileSuit(
        name="Other",
        max_hp=1000,
        current_hp=500,
        armor=50,
        mobility=1.0,
        position=Vector3(x=0, y=0, z=0),
        weapons=[Weapon(id="w2", name="Rifle", power=50, range=300, accuracy=70)],
    )
    other_unit.team_id = str(uuid4())

    simulator = _make_simulator_mock([other_unit])

    player_unit = _convert_snapshot_to_mobile_suit(dict(snapshot))
    player_unit.side = "PLAYER"

    _save_battle_results(
        session=session,
        room=room,
        player_entries=[entry],
        npc_entries=[],
        simulator=simulator,
        primary_player_win=False,
        kills=0,
        player_unit=player_unit,
        enemy_units=[other_unit],
    )

    results = list(
        session.exec(select(BattleResult).where(BattleResult.room_id == room.id)).all()
    )
    assert len(results) == 1
    result = results[0]

    assert result.win_loss == "LOSE"
    assert result.kills == 0
    assert result.is_read is False
    assert result.ms_snapshot["name"] == "Loser Zaku"


def test_save_battle_results_snapshot_immutability(in_memory_session):
    """BattleResult の ms_snapshot がエントリー時のスナップショットと一致すること."""
    from sqlmodel import select

    from scripts.run_batch import _convert_snapshot_to_mobile_suit, _save_battle_results

    session = in_memory_session
    room = _make_room(session)

    original_snapshot = _make_snapshot("Immutable Gundam")
    original_snapshot["team_id"] = str(uuid4())

    entry = _make_entry(session, room, "user_immutable", original_snapshot)

    alive_unit = _convert_snapshot_to_mobile_suit(dict(original_snapshot))
    alive_unit.current_hp = 100
    alive_unit.team_id = original_snapshot["team_id"]

    simulator = _make_simulator_mock([alive_unit])
    player_unit = _convert_snapshot_to_mobile_suit(dict(original_snapshot))
    player_unit.side = "PLAYER"
    player_unit.team_id = original_snapshot["team_id"]

    _save_battle_results(
        session=session,
        room=room,
        player_entries=[entry],
        npc_entries=[],
        simulator=simulator,
        primary_player_win=True,
        kills=0,
        player_unit=player_unit,
        enemy_units=[],
    )

    results = list(
        session.exec(select(BattleResult).where(BattleResult.room_id == room.id)).all()
    )
    result = results[0]

    # スナップショットはエントリー時のものと一致する
    assert result.ms_snapshot["name"] == original_snapshot["name"]
    assert result.ms_snapshot["max_hp"] == original_snapshot["max_hp"]

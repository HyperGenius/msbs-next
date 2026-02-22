"""Tests for NPC persistence and autonomous growth system."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.db import json_serializer
from app.models.models import (
    BattleEntry,
    BattleRoom,
    MobileSuit,
    Pilot,
    Vector3,
    Weapon,
)
from app.services.matching_service import MatchingService
from app.services.pilot_service import PilotService


@pytest.fixture
def in_memory_session():
    """Create an in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:", json_serializer=json_serializer)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def create_test_mobile_suit(
    name: str = "Test Suit", user_id: str = "test_user"
) -> MobileSuit:
    """Create a test mobile suit."""
    return MobileSuit(
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="test_weapon",
                name="Test Weapon",
                power=100,
                range=500,
                accuracy=80,
            )
        ],
        side="PLAYER",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        user_id=user_id,
    )


# --- Pilot model tests ---


def test_pilot_has_is_npc_field(in_memory_session):
    """Pilot モデルに is_npc フィールドがあることをテスト."""
    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        is_npc=False,
    )
    assert pilot.is_npc is False

    npc_pilot = Pilot(
        user_id="npc-abc123",
        name="NPC Pilot",
        is_npc=True,
        npc_personality="AGGRESSIVE",
    )
    assert npc_pilot.is_npc is True
    assert npc_pilot.npc_personality == "AGGRESSIVE"


def test_pilot_is_npc_defaults_to_false(in_memory_session):
    """Pilot.is_npc のデフォルト値が False であることをテスト."""
    pilot = Pilot(user_id="user123", name="Player")
    assert pilot.is_npc is False
    assert pilot.npc_personality is None


# --- PilotService NPC creation tests ---


def test_create_npc_pilot(in_memory_session):
    """NPC パイロット作成をテスト."""
    service = PilotService(in_memory_session)
    pilot = service.create_npc_pilot("Zaku NPC", "AGGRESSIVE")

    assert pilot.is_npc is True
    assert pilot.npc_personality == "AGGRESSIVE"
    assert pilot.name == "Zaku NPC"
    assert pilot.user_id.startswith("npc-")
    assert pilot.level == 1
    assert pilot.exp == 0
    assert pilot.credits == 0


def test_create_npc_pilot_persisted_in_db(in_memory_session):
    """NPC パイロットが DB に保存されることをテスト."""
    service = PilotService(in_memory_session)
    pilot = service.create_npc_pilot("Dom NPC", "CAUTIOUS")

    # DB から取得して確認
    db_pilot = in_memory_session.exec(
        select(Pilot).where(Pilot.user_id == pilot.user_id)
    ).first()
    assert db_pilot is not None
    assert db_pilot.is_npc is True
    assert db_pilot.name == "Dom NPC"


def test_get_npc_pilot(in_memory_session):
    """get_npc_pilot で NPC パイロットを取得できることをテスト."""
    service = PilotService(in_memory_session)
    created = service.create_npc_pilot("Gouf NPC", "SNIPER")

    found = service.get_npc_pilot(created.user_id)
    assert found is not None
    assert found.user_id == created.user_id
    assert found.is_npc is True


def test_get_npc_pilot_returns_none_for_player(in_memory_session):
    """get_npc_pilot がプレイヤーを返さないことをテスト."""
    # プレイヤーパイロットを作成
    player_pilot = Pilot(user_id="player_user", name="Player", is_npc=False)
    in_memory_session.add(player_pilot)
    in_memory_session.commit()

    service = PilotService(in_memory_session)
    result = service.get_npc_pilot("player_user")
    assert result is None


def test_npc_pilot_grows_with_add_rewards(in_memory_session):
    """NPC パイロットが add_rewards で成長することをテスト."""
    service = PilotService(in_memory_session)
    npc_pilot = service.create_npc_pilot("Growing NPC", "AGGRESSIVE")

    assert npc_pilot.level == 1
    assert npc_pilot.exp == 0

    updated, logs = service.add_rewards(npc_pilot, exp_gained=100, credits_gained=0)

    assert updated.level == 2  # レベルアップ
    assert any("レベルアップ" in log for log in logs)


# --- MatchingService NPC persistence tests ---


def test_select_npcs_for_room_empty_db(in_memory_session):
    """DB が空のとき select_npcs_for_room が空リストを返すことをテスト."""
    service = MatchingService(in_memory_session)
    result = service.select_npcs_for_room(3)
    assert result == []


def test_select_npcs_for_room_with_existing_npcs(in_memory_session):
    """既存 NPC が DB にある場合に select_npcs_for_room が返すことをテスト."""
    pilot_service = PilotService(in_memory_session)

    # NPC パイロットと機体を作成
    npc_pilot = pilot_service.create_npc_pilot("Persistent NPC", "AGGRESSIVE")
    npc_suit = MobileSuit(
        name="Zaku II (NPC)",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.2,
        position=Vector3(x=0, y=0, z=0),
        weapons=[],
        side="ENEMY",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        user_id=npc_pilot.user_id,
        personality="AGGRESSIVE",
    )
    in_memory_session.add(npc_suit)
    in_memory_session.commit()

    matching_service = MatchingService(in_memory_session)
    result = matching_service.select_npcs_for_room(1)

    assert len(result) == 1
    suit, pilot = result[0]
    assert suit.user_id == npc_pilot.user_id
    assert pilot.is_npc is True


def test_create_rooms_creates_npc_pilots(in_memory_session):
    """create_rooms が NPC パイロットを DB に保存することをテスト."""
    # ルームを作成
    room = BattleRoom(
        status="OPEN",
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
    )
    in_memory_session.add(room)
    in_memory_session.commit()
    in_memory_session.refresh(room)

    # プレイヤーエントリーを1件作成
    suit = create_test_mobile_suit("Player Suit", "player_user")
    in_memory_session.add(suit)
    in_memory_session.commit()

    entry = BattleEntry(
        user_id="player_user",
        room_id=room.id,
        mobile_suit_id=suit.id,
        mobile_suit_snapshot=suit.model_dump(),
        is_npc=False,
    )
    in_memory_session.add(entry)
    in_memory_session.commit()

    # マッチング実行（room_size=3 → NPC 2体生成）
    service = MatchingService(in_memory_session, room_size=3, npc_persistence_rate=0.0)
    service.create_rooms()

    # NPC パイロットが作成されたことを確認
    npc_pilots = in_memory_session.exec(
        select(Pilot).where(Pilot.is_npc == True)  # noqa: E712
    ).all()
    assert len(npc_pilots) == 2
    for pilot in npc_pilots:
        assert pilot.user_id.startswith("npc-")
        assert pilot.npc_personality is not None


def test_create_rooms_npc_snapshot_includes_pilot_level(in_memory_session):
    """NPC エントリーのスナップショットに npc_pilot_level が含まれることをテスト."""
    room = BattleRoom(
        status="OPEN",
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
    )
    in_memory_session.add(room)
    in_memory_session.commit()
    in_memory_session.refresh(room)

    suit = create_test_mobile_suit("Player Suit", "player_user")
    in_memory_session.add(suit)
    in_memory_session.commit()

    entry = BattleEntry(
        user_id="player_user",
        room_id=room.id,
        mobile_suit_id=suit.id,
        mobile_suit_snapshot=suit.model_dump(),
        is_npc=False,
    )
    in_memory_session.add(entry)
    in_memory_session.commit()

    service = MatchingService(in_memory_session, room_size=2, npc_persistence_rate=0.0)
    service.create_rooms()

    npc_entries = in_memory_session.exec(
        select(BattleEntry).where(
            BattleEntry.room_id == room.id,
            BattleEntry.is_npc == True,  # noqa: E712
        )
    ).all()

    assert len(npc_entries) == 1
    assert "npc_pilot_level" in npc_entries[0].mobile_suit_snapshot
    assert npc_entries[0].mobile_suit_snapshot["npc_pilot_level"] == 1


def test_create_rooms_reuses_persistent_npcs(in_memory_session):
    """2回目のマッチングで既存 NPC が再利用されることをテスト."""
    pilot_service = PilotService(in_memory_session)

    # 永続化された NPC をあらかじめ作成
    npc_pilot = pilot_service.create_npc_pilot("Rival NPC", "AGGRESSIVE")
    npc_suit = MobileSuit(
        name="Rival Zaku",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.2,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="rival_weapon",
                name="Rival Machine Gun",
                power=100,
                range=400,
                accuracy=70,
            )
        ],
        side="ENEMY",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        user_id=npc_pilot.user_id,
        personality="AGGRESSIVE",
    )
    in_memory_session.add(npc_suit)
    in_memory_session.commit()

    # ルームとプレイヤーエントリーを作成
    room = BattleRoom(
        status="OPEN",
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
    )
    in_memory_session.add(room)
    in_memory_session.commit()
    in_memory_session.refresh(room)

    player_suit = create_test_mobile_suit("Player", "player_user")
    in_memory_session.add(player_suit)
    in_memory_session.commit()

    entry = BattleEntry(
        user_id="player_user",
        room_id=room.id,
        mobile_suit_id=player_suit.id,
        mobile_suit_snapshot=player_suit.model_dump(),
        is_npc=False,
    )
    in_memory_session.add(entry)
    in_memory_session.commit()

    # 100% 永続化NPC を使うよう設定
    service = MatchingService(in_memory_session, room_size=2, npc_persistence_rate=1.0)
    service.create_rooms()

    npc_entries = in_memory_session.exec(
        select(BattleEntry).where(
            BattleEntry.room_id == room.id,
            BattleEntry.is_npc == True,  # noqa: E712
        )
    ).all()

    # 既存 NPC が再利用されていること
    assert len(npc_entries) == 1
    assert npc_entries[0].user_id == npc_pilot.user_id

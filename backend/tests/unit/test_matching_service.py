"""Tests for the matching service."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, create_engine

from app.models.models import (
    BattleEntry,
    BattleRoom,
    MobileSuit,
    Team,
    TeamMember,
    Vector3,
    Weapon,
)
from app.services.matching_service import MatchingService


@pytest.fixture
def in_memory_session():
    """Create an in-memory database session for testing."""
    from app.db import json_serializer

    engine = create_engine("sqlite:///:memory:", json_serializer=json_serializer)

    # Create tables
    from sqlmodel import SQLModel

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


def create_test_mobile_suit(name: str = "Test Suit") -> MobileSuit:
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
        user_id="test_user",
    )


def test_matching_service_initialization(in_memory_session):
    """Test that MatchingService initializes correctly."""
    service = MatchingService(in_memory_session, room_size=8)

    assert service.session == in_memory_session
    assert service.room_size == 8


def test_create_rooms_no_open_rooms(in_memory_session):
    """Test create_rooms when there are no open rooms."""
    service = MatchingService(in_memory_session)

    rooms = service.create_rooms()

    assert len(rooms) == 0


def test_create_rooms_with_entries(in_memory_session):
    """Test create_rooms with player entries."""
    # Create a test room
    room = BattleRoom(
        status="OPEN",
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
    )
    in_memory_session.add(room)
    in_memory_session.commit()
    in_memory_session.refresh(room)

    # Create test mobile suits
    suit1 = create_test_mobile_suit("Player 1")
    suit2 = create_test_mobile_suit("Player 2")
    in_memory_session.add(suit1)
    in_memory_session.add(suit2)
    in_memory_session.commit()

    # Create entries
    entry1 = BattleEntry(
        user_id="user_1",
        room_id=room.id,
        mobile_suit_id=suit1.id,
        mobile_suit_snapshot=suit1.model_dump(),
        is_npc=False,
    )
    entry2 = BattleEntry(
        user_id="user_2",
        room_id=room.id,
        mobile_suit_id=suit2.id,
        mobile_suit_snapshot=suit2.model_dump(),
        is_npc=False,
    )
    in_memory_session.add(entry1)
    in_memory_session.add(entry2)
    in_memory_session.commit()

    # Run matching
    service = MatchingService(in_memory_session, room_size=4)
    rooms = service.create_rooms()

    # Verify
    assert len(rooms) == 1
    assert rooms[0].status == "WAITING"

    # Verify NPCs were created
    from sqlmodel import select

    all_entries = in_memory_session.exec(
        select(BattleEntry).where(BattleEntry.room_id == room.id)
    ).all()

    assert len(all_entries) == 4  # 2 players + 2 NPCs
    npc_entries = [e for e in all_entries if e.is_npc]
    assert len(npc_entries) == 2


def test_create_npc_mobile_suit(in_memory_session):
    """Test NPC mobile suit creation."""
    service = MatchingService(in_memory_session)

    npc = service._create_npc_mobile_suit()

    # Verify NPC properties
    assert "NPC" in npc.name
    assert npc.side == "ENEMY"
    assert npc.user_id is None
    assert npc.max_hp > 0
    assert npc.current_hp == npc.max_hp
    assert len(npc.weapons) > 0
    assert npc.tactics is not None


def test_create_rooms_with_no_entries(in_memory_session):
    """Test create_rooms when room has no entries."""
    # Create a test room without entries
    room = BattleRoom(
        status="OPEN",
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
    )
    in_memory_session.add(room)
    in_memory_session.commit()

    # Run matching
    service = MatchingService(in_memory_session)
    rooms = service.create_rooms()

    # Room should not be processed
    assert len(rooms) == 0
    assert room.status == "OPEN"


def test_create_rooms_with_no_entries_past_schedule(in_memory_session):
    """Test create_rooms when room has no entries and scheduled_at is in the past."""
    # Create a test room without entries and scheduled_at in the past
    past_time = datetime.now(UTC) - timedelta(hours=2)
    room = BattleRoom(
        status="OPEN",
        scheduled_at=past_time,
    )
    in_memory_session.add(room)
    in_memory_session.commit()
    in_memory_session.refresh(room)

    original_scheduled_at = room.scheduled_at

    # Run matching
    service = MatchingService(in_memory_session)
    rooms = service.create_rooms()

    # Room should not be processed but scheduled_at should be updated
    assert len(rooms) == 0

    # Refresh the room to get updated data
    in_memory_session.refresh(room)

    # Room status should still be OPEN
    assert room.status == "OPEN"

    # scheduled_at should be updated to next day (24 hours later)
    # Handle timezone-naive datetime from database
    expected_scheduled_at = original_scheduled_at + timedelta(days=1)
    if expected_scheduled_at.tzinfo is None:
        expected_scheduled_at = expected_scheduled_at.replace(tzinfo=UTC)

    room_scheduled_at = room.scheduled_at
    if room_scheduled_at.tzinfo is None:
        room_scheduled_at = room_scheduled_at.replace(tzinfo=UTC)

    assert room_scheduled_at == expected_scheduled_at
    assert room_scheduled_at > datetime.now(UTC)


def test_create_rooms_fills_to_capacity(in_memory_session):
    """Test that create_rooms fills room to exact capacity."""
    # Create a test room
    room = BattleRoom(
        status="OPEN",
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
    )
    in_memory_session.add(room)
    in_memory_session.commit()
    in_memory_session.refresh(room)

    # Create 1 player entry
    suit = create_test_mobile_suit("Player 1")
    in_memory_session.add(suit)
    in_memory_session.commit()

    entry = BattleEntry(
        user_id="user_1",
        room_id=room.id,
        mobile_suit_id=suit.id,
        mobile_suit_snapshot=suit.model_dump(),
        is_npc=False,
    )
    in_memory_session.add(entry)
    in_memory_session.commit()

    # Run matching with room size 8
    service = MatchingService(in_memory_session, room_size=8)
    service.create_rooms()

    # Verify
    from sqlmodel import select

    all_entries = in_memory_session.exec(
        select(BattleEntry).where(BattleEntry.room_id == room.id)
    ).all()

    # Should have 1 player + 7 NPCs = 8 total
    assert len(all_entries) == 8
    npc_count = len([e for e in all_entries if e.is_npc])
    assert npc_count == 7


def test_npc_has_valid_attributes(in_memory_session):
    """Test that generated NPCs have valid game attributes."""
    service = MatchingService(in_memory_session)

    npc = service._create_npc_mobile_suit()

    # Check HP is reasonable
    assert 600 <= npc.max_hp <= 900
    assert npc.current_hp == npc.max_hp

    # Check armor is reasonable
    assert 30 <= npc.armor <= 70

    # Check mobility is reasonable
    assert 0.8 <= npc.mobility <= 1.5

    # Check weapons
    assert len(npc.weapons) >= 1
    for weapon in npc.weapons:
        assert weapon.power > 0
        assert weapon.range > 0
        assert weapon.accuracy > 0

    # Check tactics
    assert npc.tactics["priority"] in ["CLOSEST", "WEAKEST", "RANDOM"]
    assert npc.tactics["range"] in ["MELEE", "RANGED", "BALANCED"]


def test_apply_team_grouping_marks_members(in_memory_session):
    """Test that _apply_team_grouping adds team_id to snapshot for team members."""
    # Create a team with two players
    team = Team(owner_user_id="user_a", name="Alpha Squad")
    in_memory_session.add(team)
    in_memory_session.flush()

    member_a = TeamMember(team_id=team.id, user_id="user_a", is_ready=True)
    member_b = TeamMember(team_id=team.id, user_id="user_b", is_ready=True)
    in_memory_session.add(member_a)
    in_memory_session.add(member_b)
    in_memory_session.commit()

    # Create mobile suits and entries for both team members
    suit_a = create_test_mobile_suit("Suit A")
    suit_a.user_id = "user_a"
    suit_b = create_test_mobile_suit("Suit B")
    suit_b.user_id = "user_b"
    in_memory_session.add(suit_a)
    in_memory_session.add(suit_b)
    in_memory_session.commit()

    entry_a = BattleEntry(
        user_id="user_a",
        room_id=team.id,  # room_id doesn't matter for grouping test
        mobile_suit_id=suit_a.id,
        mobile_suit_snapshot=suit_a.model_dump(),
        is_npc=False,
    )
    entry_b = BattleEntry(
        user_id="user_b",
        room_id=team.id,
        mobile_suit_id=suit_b.id,
        mobile_suit_snapshot=suit_b.model_dump(),
        is_npc=False,
    )

    entries = [entry_a, entry_b]
    service = MatchingService(in_memory_session)
    service._apply_team_grouping(entries)

    # Both entries should have team_id in their snapshot
    tid = str(team.id)
    assert entry_a.mobile_suit_snapshot.get("team_id") == tid
    assert entry_b.mobile_suit_snapshot.get("team_id") == tid
    assert entry_a.mobile_suit_snapshot.get("side") == "PLAYER"
    assert entry_b.mobile_suit_snapshot.get("side") == "PLAYER"


def test_apply_team_grouping_skips_solo_players(in_memory_session):
    """Test that _apply_team_grouping does not mark entries with no team."""
    suit = create_test_mobile_suit("Solo Suit")
    suit.user_id = "solo_user"
    in_memory_session.add(suit)
    in_memory_session.commit()

    entry = BattleEntry(
        user_id="solo_user",
        room_id=suit.id,
        mobile_suit_id=suit.id,
        mobile_suit_snapshot=suit.model_dump(),
        is_npc=False,
    )
    entries = [entry]
    service = MatchingService(in_memory_session)
    service._apply_team_grouping(entries)

    # Solo player should not have team_id set
    assert "team_id" not in entry.mobile_suit_snapshot

"""Tests for NPC personality and ace pilot features."""

import pytest
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, create_engine

from app.models.models import BattleEntry, BattleRoom, MobileSuit, Vector3, Weapon
from app.services.matching_service import MatchingService
from app.core.npc_data import ACE_PILOTS, PERSONALITY_TYPES, BATTLE_CHATTER


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


def test_personality_types_defined():
    """Test that personality types are properly defined."""
    assert len(PERSONALITY_TYPES) == 3
    assert "AGGRESSIVE" in PERSONALITY_TYPES
    assert "CAUTIOUS" in PERSONALITY_TYPES
    assert "SNIPER" in PERSONALITY_TYPES


def test_battle_chatter_defined():
    """Test that battle chatter is defined for all personalities."""
    for personality in PERSONALITY_TYPES:
        assert personality in BATTLE_CHATTER
        assert "attack" in BATTLE_CHATTER[personality]
        assert "hit" in BATTLE_CHATTER[personality]
        assert "destroyed" in BATTLE_CHATTER[personality]
        assert "miss" in BATTLE_CHATTER[personality]
        # Each category should have at least one line
        assert len(BATTLE_CHATTER[personality]["attack"]) > 0
        assert len(BATTLE_CHATTER[personality]["hit"]) > 0
        assert len(BATTLE_CHATTER[personality]["destroyed"]) > 0
        assert len(BATTLE_CHATTER[personality]["miss"]) > 0


def test_ace_pilots_defined():
    """Test that ace pilots are properly defined."""
    assert len(ACE_PILOTS) > 0
    
    for ace in ACE_PILOTS:
        # Required fields
        assert "id" in ace
        assert "name" in ace
        assert "pilot_name" in ace
        assert "personality" in ace
        assert "mobile_suit" in ace
        assert "bounty_exp" in ace
        assert "bounty_credits" in ace
        
        # Validate personality
        assert ace["personality"] in PERSONALITY_TYPES
        
        # Validate mobile suit data
        ms = ace["mobile_suit"]
        assert "name" in ms
        assert "max_hp" in ms
        assert "armor" in ms
        assert "mobility" in ms
        assert "weapons" in ms
        assert "tactics" in ms
        assert len(ms["weapons"]) > 0


def test_npc_creation_with_personality(in_memory_session):
    """Test that NPCs are created with personality."""
    service = MatchingService(in_memory_session)
    
    # Create multiple NPCs to test randomization
    npcs = [service._create_npc_mobile_suit() for _ in range(10)]
    
    for npc in npcs:
        # Each NPC should have a personality
        assert npc.personality is not None
        assert npc.personality in PERSONALITY_TYPES
        
        # Personality should affect tactics
        if npc.personality == "AGGRESSIVE":
            assert npc.tactics["range"] == "MELEE"
        elif npc.personality == "CAUTIOUS":
            assert npc.tactics["range"] == "BALANCED"
        elif npc.personality == "SNIPER":
            assert npc.tactics["range"] == "RANGED"


def test_ace_pilot_creation(in_memory_session):
    """Test that ace pilots are created correctly."""
    service = MatchingService(in_memory_session)
    
    # Create ace pilot
    ace = service._create_ace_pilot()
    
    # Validate ace pilot properties
    assert ace.is_ace is True
    assert ace.ace_id is not None
    assert ace.pilot_name is not None
    assert ace.personality in PERSONALITY_TYPES
    assert ace.bounty_exp > 0
    assert ace.bounty_credits > 0
    
    # Ace should be stronger than normal NPCs
    assert ace.max_hp >= 1100  # Minimum ace HP
    assert ace.mobility >= 2.0  # Minimum ace mobility


def test_ace_spawn_rate(in_memory_session):
    """Test ace pilot spawn probability."""
    # Test with 100% spawn rate
    service = MatchingService(in_memory_session, room_size=8, ace_spawn_rate=1.0)
    
    room = BattleRoom(
        status="OPEN",
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
    )
    in_memory_session.add(room)
    in_memory_session.commit()
    in_memory_session.refresh(room)
    
    # Create at least one player entry (required for matching to process)
    player_suit = MobileSuit(
        name="Player Suit",
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
        user_id="test_user",
    )
    in_memory_session.add(player_suit)
    in_memory_session.commit()
    
    player_entry = BattleEntry(
        user_id="test_user",
        room_id=room.id,
        mobile_suit_id=player_suit.id,
        mobile_suit_snapshot=player_suit.model_dump(),
        is_npc=False,
    )
    in_memory_session.add(player_entry)
    in_memory_session.commit()
    
    # Process the room (should spawn an ace)
    created_rooms = service.create_rooms()
    
    assert len(created_rooms) == 1
    
    # Check that at least one ace was created
    from sqlmodel import select
    entries = in_memory_session.exec(
        select(BattleEntry).where(BattleEntry.room_id == room.id)
    ).all()
    
    assert len(entries) == 8  # Should be full
    
    # Check if any entry is an ace
    ace_found = False
    for entry in entries:
        snapshot = entry.mobile_suit_snapshot
        if snapshot.get("is_ace", False):
            ace_found = True
            assert snapshot.get("pilot_name") is not None
            assert snapshot.get("bounty_exp", 0) > 0
            break
    
    assert ace_found, "No ace pilot found with 100% spawn rate"


def test_no_ace_spawn_with_zero_rate(in_memory_session):
    """Test that no ace spawns with 0% rate."""
    # Test with 0% spawn rate
    service = MatchingService(in_memory_session, room_size=8, ace_spawn_rate=0.0)
    
    room = BattleRoom(
        status="OPEN",
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
    )
    in_memory_session.add(room)
    in_memory_session.commit()
    in_memory_session.refresh(room)
    
    # Create at least one player entry (required for matching to process)
    player_suit = MobileSuit(
        name="Player Suit",
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
        user_id="test_user",
    )
    in_memory_session.add(player_suit)
    in_memory_session.commit()
    
    player_entry = BattleEntry(
        user_id="test_user",
        room_id=room.id,
        mobile_suit_id=player_suit.id,
        mobile_suit_snapshot=player_suit.model_dump(),
        is_npc=False,
    )
    in_memory_session.add(player_entry)
    in_memory_session.commit()
    
    # Process the room (should not spawn an ace)
    created_rooms = service.create_rooms()
    
    assert len(created_rooms) == 1
    
    # Check that no ace was created
    from sqlmodel import select
    entries = in_memory_session.exec(
        select(BattleEntry).where(BattleEntry.room_id == room.id)
    ).all()
    
    # Check that no entry is an ace
    for entry in entries:
        snapshot = entry.mobile_suit_snapshot
        assert not snapshot.get("is_ace", False)


def test_ace_pilot_data_integrity():
    """Test that all ace pilot data is valid."""
    for ace in ACE_PILOTS:
        # Test that weapons are valid Weapon objects
        ms = ace["mobile_suit"]
        for weapon in ms["weapons"]:
            assert isinstance(weapon, Weapon)
            assert weapon.id is not None
            assert weapon.name is not None
            assert weapon.power > 0
            assert weapon.range > 0
            assert weapon.accuracy > 0
        
        # Test that bounty rewards are reasonable
        assert 0 < ace["bounty_exp"] <= 1000
        assert 0 < ace["bounty_credits"] <= 5000
        
        # Test that stats are higher than normal NPCs
        assert ms["max_hp"] >= 1100
        assert ms["mobility"] >= 2.0


def test_personality_affects_tactics():
    """Test that personality properly affects tactical settings."""
    from app.services.matching_service import MatchingService
    from sqlmodel import Session, create_engine
    from app.db import json_serializer
    
    engine = create_engine("sqlite:///:memory:", json_serializer=json_serializer)
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        service = MatchingService(session)
        
        # Create many NPCs to verify personality-tactics mapping
        aggressive_count = 0
        cautious_count = 0
        sniper_count = 0
        
        for _ in range(30):
            npc = service._create_npc_mobile_suit()
            
            if npc.personality == "AGGRESSIVE":
                assert npc.tactics["range"] == "MELEE"
                aggressive_count += 1
            elif npc.personality == "CAUTIOUS":
                assert npc.tactics["range"] == "BALANCED"
                cautious_count += 1
            elif npc.personality == "SNIPER":
                assert npc.tactics["range"] == "RANGED"
                sniper_count += 1
        
        # Verify we got a mix of personalities
        assert aggressive_count > 0
        assert cautious_count > 0
        assert sniper_count > 0

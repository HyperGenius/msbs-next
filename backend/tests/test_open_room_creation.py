#!/usr/bin/env python3
"""Test for OPEN room creation to fix countdown timer issue.

This test verifies that:
1. Batch processing creates a new OPEN room after completing simulations
2. API /status endpoint always returns next_room information
"""

import os
import sys
from datetime import UTC, datetime, timedelta

# Set environment variables for testing
os.environ["NEON_DATABASE_URL"] = os.environ.get(
    "NEON_DATABASE_URL", "postgresql://test:test@localhost:5432/test"
)
os.environ["CLERK_JWKS_URL"] = os.environ.get(
    "CLERK_JWKS_URL", "https://test.clerk.accounts.dev/.well-known/jwks.json"
)
os.environ["CLERK_SECRET_KEY"] = os.environ.get("CLERK_SECRET_KEY", "test_secret_key")

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlmodel import Session, select

from app.db import engine
from app.models.models import BattleEntry, BattleRoom, MobileSuit, Vector3, Weapon


def test_batch_creates_next_open_room():
    """Test that batch processing creates next OPEN room after simulation."""
    print("\nTest: Batch creates next OPEN room")
    print("-" * 60)

    with Session(engine) as session:
        # Clean up existing rooms for this test
        statement = select(BattleRoom)
        rooms = session.exec(statement).all()
        for room in rooms:
            session.delete(room)
        session.commit()

        # Create test mobile suit
        suit = MobileSuit(
            name="Test Gundam",
            user_id="test_user_batch",
            max_hp=1000,
            current_hp=1000,
            armor=100,
            mobility=1.5,
            position=Vector3(x=0, y=0, z=0),
            weapons=[
                Weapon(
                    id="beam_rifle",
                    name="Beam Rifle",
                    power=300,
                    range=600,
                    accuracy=85,
                )
            ],
            side="PLAYER",
            tactics={"priority": "CLOSEST", "range": "BALANCED"},
        )
        session.add(suit)
        session.commit()
        session.refresh(suit)

        # Create OPEN room with entry
        open_room = BattleRoom(
            status="OPEN",
            scheduled_at=datetime.now(UTC) + timedelta(hours=1),
        )
        session.add(open_room)
        session.commit()
        session.refresh(open_room)

        entry = BattleEntry(
            user_id="test_user_batch",
            room_id=open_room.id,
            mobile_suit_id=suit.id,
            mobile_suit_snapshot=suit.model_dump(),
            is_npc=False,
        )
        session.add(entry)
        session.commit()

        print(f"  Created OPEN room: {open_room.id}")

        # Import and run batch
        from scripts.run_batch import create_next_open_room, run_matching_phase

        # Run matching to transition room to WAITING
        run_matching_phase(session)

        # Verify room is now WAITING
        session.refresh(open_room)
        assert open_room.status == "WAITING", "Room should be WAITING after matching"
        print(f"  Room transitioned to WAITING: {open_room.id}")

        # Manually update room to COMPLETED (simulating simulation phase)
        open_room.status = "COMPLETED"
        session.add(open_room)
        session.commit()
        print(f"  Room marked as COMPLETED: {open_room.id}")

        # Run the create_next_open_room function
        create_next_open_room(session)

        # Verify new OPEN room was created
        statement = select(BattleRoom).where(BattleRoom.status == "OPEN")
        new_open_room = session.exec(statement).first()

        assert new_open_room is not None, "New OPEN room should be created"
        assert new_open_room.id != open_room.id, "New room should have different ID"
        print(f"  New OPEN room created: {new_open_room.id}")
        print(f"  Scheduled at: {new_open_room.scheduled_at}")

        # Verify scheduled time is correct (next 12:00 UTC)
        now = datetime.now(UTC)
        expected_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if now.hour >= 12:
            expected_time += timedelta(days=1)

        assert new_open_room.scheduled_at == expected_time, (
            f"Scheduled time should be {expected_time}, got {new_open_room.scheduled_at}"
        )
        print("  ✓ Scheduled time is correct")

        print("  ✓ Test passed: Batch creates next OPEN room\n")


def test_api_always_returns_next_room():
    """Test that API /status endpoint always returns next_room."""
    print("Test: API always returns next_room")
    print("-" * 60)

    with Session(engine) as session:
        # Clean up existing rooms
        statement = select(BattleRoom)
        rooms = session.exec(statement).all()
        for room in rooms:
            session.delete(room)
        session.commit()

        # Verify no OPEN rooms exist
        statement = select(BattleRoom).where(BattleRoom.status == "OPEN")
        existing_room = session.exec(statement).first()
        assert existing_room is None, "Should start with no OPEN rooms"
        print("  No OPEN rooms exist initially")

        # Import the helper function
        from app.routers.entries import get_or_create_open_room

        # Call get_or_create_open_room
        room = get_or_create_open_room(session)

        assert room is not None, "Should return a room"
        assert room.status == "OPEN", "Room should have OPEN status"
        print(f"  Room created: {room.id}")
        print(f"  Status: {room.status}")
        print(f"  Scheduled at: {room.scheduled_at}")

        # Verify scheduled time is correct
        now = datetime.now(UTC)
        expected_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if now.hour >= 12:
            expected_time += timedelta(days=1)

        assert room.scheduled_at == expected_time, (
            f"Scheduled time should be {expected_time}, got {room.scheduled_at}"
        )
        print("  ✓ Scheduled time is correct")

        # Call again to verify it returns the same room
        room2 = get_or_create_open_room(session)
        assert room2.id == room.id, (
            "Should return same room when OPEN room already exists"
        )
        print("  ✓ Returns existing room on second call")

        print("  ✓ Test passed: API always returns next_room\n")


def test_no_duplicate_open_rooms():
    """Test that multiple batch runs don't create duplicate OPEN rooms."""
    print("Test: No duplicate OPEN rooms")
    print("-" * 60)

    with Session(engine) as session:
        # Clean up existing rooms
        statement = select(BattleRoom)
        rooms = session.exec(statement).all()
        for room in rooms:
            session.delete(room)
        session.commit()

        from scripts.run_batch import create_next_open_room

        # Run create_next_open_room multiple times
        create_next_open_room(session)
        create_next_open_room(session)
        create_next_open_room(session)

        # Verify only one OPEN room exists
        statement = select(BattleRoom).where(BattleRoom.status == "OPEN")
        open_rooms = list(session.exec(statement).all())

        assert len(open_rooms) == 1, (
            f"Should have exactly 1 OPEN room, got {len(open_rooms)}"
        )
        print(f"  Only 1 OPEN room exists after multiple calls: {open_rooms[0].id}")
        print("  ✓ Test passed: No duplicate OPEN rooms\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Testing OPEN Room Creation Fix")
    print("=" * 60)

    try:
        test_batch_creates_next_open_room()
        test_api_always_returns_next_room()
        test_no_duplicate_open_rooms()

        print("=" * 60)
        print("✓✓✓ All tests passed! ✓✓✓")
        print("=" * 60 + "\n")
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

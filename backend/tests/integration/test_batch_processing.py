#!/usr/bin/env python3
"""Integration test for batch processing.

This script sets up a test scenario and runs the batch script to verify
the complete flow works correctly.
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

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from sqlmodel import Session, select

from app.db import engine
from app.models.models import (
    BattleEntry,
    BattleResult,
    BattleRoom,
    MobileSuit,
    Vector3,
    Weapon,
)


def setup_test_data(session: Session) -> BattleRoom:
    """Create test data for batch processing."""
    print("Setting up test data...")

    # Create test mobile suits
    suit1 = MobileSuit(
        name="Test Gundam",
        user_id="test_user_1",
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

    suit2 = MobileSuit(
        name="Test Zaku",
        user_id="test_user_2",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        position=Vector3(x=500, y=0, z=0),
        weapons=[
            Weapon(
                id="zaku_mg",
                name="Zaku Machine Gun",
                power=100,
                range=400,
                accuracy=70,
            )
        ],
        side="PLAYER",
        tactics={"priority": "WEAKEST", "range": "RANGED"},
    )

    session.add(suit1)
    session.add(suit2)
    session.commit()
    session.refresh(suit1)
    session.refresh(suit2)

    print(f"  Created mobile suits: {suit1.name}, {suit2.name}")

    # Create a test room
    room = BattleRoom(
        status="OPEN",
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session.add(room)
    session.commit()
    session.refresh(room)

    print(f"  Created room: {room.id}")

    # Create entries
    entry1 = BattleEntry(
        user_id="test_user_1",
        room_id=room.id,
        mobile_suit_id=suit1.id,
        mobile_suit_snapshot=suit1.model_dump(),
        is_npc=False,
    )

    entry2 = BattleEntry(
        user_id="test_user_2",
        room_id=room.id,
        mobile_suit_id=suit2.id,
        mobile_suit_snapshot=suit2.model_dump(),
        is_npc=False,
    )

    session.add(entry1)
    session.add(entry2)
    session.commit()

    print(f"  Created {2} entries")
    print("Test data setup complete\n")

    return room


def verify_results(session: Session, room_id) -> bool:
    """Verify that batch processing completed successfully."""
    print("\nVerifying results...")

    # Check room status
    room = session.get(BattleRoom, room_id)
    if room.status != "COMPLETED":
        print(f"  ✗ Room status is {room.status}, expected COMPLETED")
        return False
    print("  ✓ Room status is COMPLETED")

    # Check entries
    entry_statement = select(BattleEntry).where(BattleEntry.room_id == room_id)
    entries = list(session.exec(entry_statement).all())

    if len(entries) < 2:
        print(f"  ✗ Expected at least 2 entries, got {len(entries)}")
        return False
    print(f"  ✓ Found {len(entries)} entries")

    # Check NPCs were created
    npc_entries = [e for e in entries if e.is_npc]
    print(f"  ✓ Found {len(npc_entries)} NPCs")

    # Check battle results
    result_statement = select(BattleResult).where(BattleResult.room_id == room_id)
    results = list(session.exec(result_statement).all())

    if not results:
        print("  ✗ No battle results found")
        return False
    print(f"  ✓ Found {len(results)} battle result(s)")

    # Check that results have logs
    for result in results:
        if not result.logs:
            print(f"  ✗ Battle result {result.id} has no logs")
            return False
    print("  ✓ All results have logs")

    print("\nVerification complete!")
    return True


def main():
    """Run the integration test."""
    print("=" * 60)
    print("Integration Test: Batch Processing")
    print("=" * 60 + "\n")

    try:
        with Session(engine) as session:
            # Setup test data
            room = setup_test_data(session)

            # Import and run batch processing
            print("Running batch script...")
            print("-" * 60)
            from scripts.run_batch import main as run_batch_main

            run_batch_main()
            print("-" * 60)

            # Verify results
            success = verify_results(session, room.id)

            if success:
                print("\n" + "=" * 60)
                print("✓✓✓ Integration test PASSED! ✓✓✓")
                print("=" * 60)
                return 0
            else:
                print("\n" + "=" * 60)
                print("✗✗✗ Integration test FAILED! ✗✗✗")
                print("=" * 60)
                return 1

    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

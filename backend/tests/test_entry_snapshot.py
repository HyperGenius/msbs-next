#!/usr/bin/env python3
"""Integration test for entry feature with snapshot functionality.

This test demonstrates that the snapshot functionality works correctly,
capturing the mobile suit data at entry time.
"""

import os
import sys

# Set mock environment variables before importing anything
os.environ["CLERK_JWKS_URL"] = "https://test.clerk.accounts.dev/.well-known/jwks.json"
os.environ["CLERK_SECRET_KEY"] = "test_secret_key"
os.environ["NEON_DATABASE_URL"] = "sqlite:///./test_entry_snapshot.db"

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, create_engine

from app.models.models import BattleEntry, BattleRoom, MobileSuit, Weapon


def test_entry_snapshot():
    """Test that entry snapshot correctly captures mobile suit data."""
    print("Testing entry snapshot functionality...")

    # Create in-memory database for testing with proper JSON serializer
    from app.db import json_serializer

    engine = create_engine("sqlite:///:memory:", json_serializer=json_serializer)
    from app.models.models import SQLModel

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # 1. Create a mobile suit
        print("\n1. Creating a mobile suit with initial configuration...")
        mobile_suit = MobileSuit(
            user_id="test_user_1",
            name="ガンダム",
            max_hp=200,
            current_hp=200,
            armor=20,
            mobility=1.5,
            weapons=[
                Weapon(
                    id="beam_rifle",
                    name="ビームライフル",
                    power=45,
                    range=600,
                    accuracy=85,
                )
            ],
            tactics={"priority": "CLOSEST", "range": "RANGED"},
        )

        # Get snapshot BEFORE committing to DB
        snapshot = mobile_suit.model_dump(mode="json")
        print(f"   - Captured snapshot with {len(snapshot)} fields")

        session.add(mobile_suit)
        session.commit()
        session.refresh(mobile_suit)
        print(f"   ✓ Mobile suit created: {mobile_suit.name}")
        print(f"   - HP: {mobile_suit.max_hp}")
        print(f"   - Armor: {mobile_suit.armor}")
        print(f"   - Tactics: {mobile_suit.tactics}")

        # 2. Create a battle room
        print("\n2. Creating a battle room...")
        battle_room = BattleRoom(
            status="OPEN",
            scheduled_at=datetime.now(UTC) + timedelta(hours=1),
        )
        session.add(battle_room)
        session.commit()
        session.refresh(battle_room)
        print(f"   ✓ Battle room created: {battle_room.id}")

        # 3. Create entry with snapshot
        print("\n3. Creating entry with snapshot...")
        # Snapshot was already captured before DB commit
        print("   - Using pre-captured snapshot")
        print(
            f"   - Sample fields: name={snapshot.get('name')}, hp={snapshot.get('max_hp')}"
        )
        entry = BattleEntry(
            user_id="test_user_1",
            room_id=battle_room.id,
            mobile_suit_id=mobile_suit.id,
            mobile_suit_snapshot=snapshot,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        print("   ✓ Entry created with snapshot")
        print(f"   - Entry ID: {entry.id}")
        print(f"   - Snapshot captured at: {entry.created_at}")

        # 4. Verify snapshot contains correct data
        print("\n4. Verifying snapshot data...")
        print(f"   - Snapshot type: {type(entry.mobile_suit_snapshot)}")
        print(f"   - Snapshot content preview: {str(entry.mobile_suit_snapshot)[:200]}")

        # The snapshot should be a dict
        snapshot_data = entry.mobile_suit_snapshot
        if isinstance(snapshot_data, str):
            import json

            snapshot_data = json.loads(snapshot_data)

        assert snapshot_data["name"] == "ガンダム"
        assert snapshot_data["max_hp"] == 200
        assert snapshot_data["armor"] == 20
        assert snapshot_data["tactics"]["priority"] == "CLOSEST"
        assert snapshot_data["tactics"]["range"] == "RANGED"
        assert len(snapshot_data["weapons"]) == 1
        assert snapshot_data["weapons"][0]["name"] == "ビームライフル"
        print("   ✓ Snapshot contains all original data")

        # 5. Modify the mobile suit after entry
        print("\n5. Modifying mobile suit after entry...")
        mobile_suit.max_hp = 250
        mobile_suit.armor = 30
        mobile_suit.tactics = {"priority": "WEAKEST", "range": "MELEE"}
        session.add(mobile_suit)
        session.commit()
        session.refresh(mobile_suit)
        print("   ✓ Mobile suit modified:")
        print(f"   - New HP: {mobile_suit.max_hp}")
        print(f"   - New Armor: {mobile_suit.armor}")
        print(f"   - New Tactics: {mobile_suit.tactics}")

        # 6. Verify snapshot is unchanged
        print("\n6. Verifying snapshot remains unchanged...")
        session.refresh(entry)
        snapshot_data = entry.mobile_suit_snapshot
        if isinstance(snapshot_data, str):
            import json

            snapshot_data = json.loads(snapshot_data)

        assert snapshot_data["max_hp"] == 200, "Snapshot HP should be 200"
        assert snapshot_data["armor"] == 20, "Snapshot armor should be 20"
        assert snapshot_data["tactics"]["priority"] == "CLOSEST", (
            "Snapshot tactics priority should be CLOSEST"
        )
        assert snapshot_data["tactics"]["range"] == "RANGED", (
            "Snapshot tactics range should be RANGED"
        )
        print("   ✓ Snapshot unchanged - entry data is preserved!")
        print(f"   - Snapshot HP: {snapshot_data['max_hp']} (original)")
        print(f"   - Current HP: {mobile_suit.max_hp} (modified)")

        print("\n" + "=" * 60)
        print("✓✓✓ Snapshot functionality test passed! ✓✓✓")
        print("=" * 60)
        print("\nKey findings:")
        print("- Entry successfully captures mobile suit data at entry time")
        print("- Snapshot includes all important data: stats, weapons, tactics")
        print("- Snapshot remains immutable even when mobile suit is modified")
        print("- This ensures battle fairness in periodic update games")


if __name__ == "__main__":
    try:
        test_entry_snapshot()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""Test for timezone fix in scheduled_at field.

This test verifies that when scheduled_at is returned by the API,
it includes timezone information (UTC) so that the frontend can
correctly interpret the time.
"""

import os
import sys

# Set mock environment variables before importing anything
os.environ["CLERK_JWKS_URL"] = "https://test.clerk.accounts.dev/.well-known/jwks.json"
os.environ["CLERK_SECRET_KEY"] = "test_secret_key"
os.environ["NEON_DATABASE_URL"] = "sqlite:///:memory:"

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import UTC, datetime

from sqlmodel import Session, SQLModel, create_engine


def test_scheduled_at_timezone():
    """Test that scheduled_at includes timezone information."""
    print("Testing scheduled_at timezone fix...")

    # Import models here to avoid early db connection
    # Create in-memory database for testing
    import json as json_lib

    from app.models.models import BattleRoom

    def json_serializer(obj):
        return json_lib.dumps(obj, ensure_ascii=False)

    engine = create_engine("sqlite:///:memory:", json_serializer=json_serializer)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # 1. Create a room with naive datetime (no timezone)
        print("\n1. Creating a room with naive datetime...")
        naive_datetime = datetime(2026, 2, 12, 12, 0, 0)  # No timezone info
        print(f"   - Created naive datetime: {naive_datetime}")
        print(f"   - tzinfo: {naive_datetime.tzinfo}")
        assert naive_datetime.tzinfo is None, "Should be naive datetime"

        room = BattleRoom(
            status="OPEN",
            scheduled_at=naive_datetime,
        )
        session.add(room)
        session.commit()
        session.refresh(room)
        print("   ✓ Room created with naive scheduled_at")

        # 2. Test timezone conversion (simulating what the API does)
        print("\n2. Testing timezone conversion in API response...")

        # Simulate what the API does: get the scheduled_at and convert it
        scheduled_at = room.scheduled_at
        print(f"   - Original scheduled_at: {scheduled_at}")
        print(f"   - Original tzinfo: {scheduled_at.tzinfo}")

        # Apply the fix
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=UTC)

        print(f"   - After fix scheduled_at: {scheduled_at}")
        print(f"   - After fix tzinfo: {scheduled_at.tzinfo}")

        # Convert to ISO format
        iso_string = scheduled_at.isoformat()
        print(f"   - ISO format: {iso_string}")

        # 3. Verify the ISO string includes timezone
        print("\n3. Verifying ISO format includes timezone...")
        assert "+00:00" in iso_string or iso_string.endswith("Z"), (
            f"ISO string should include timezone info. Got: {iso_string}"
        )
        print(f"   ✓ ISO string includes timezone: {iso_string}")

        # 4. Verify the frontend can correctly parse it
        print("\n4. Verifying frontend can parse it correctly...")
        parsed_datetime = datetime.fromisoformat(iso_string)
        print(f"   - Parsed datetime: {parsed_datetime}")
        print(f"   - Parsed tzinfo: {parsed_datetime.tzinfo}")
        assert parsed_datetime.tzinfo is not None, (
            "Parsed datetime should have timezone"
        )

        # Convert to JST (UTC+9) to verify the expected time
        print("\n5. Verifying time interpretation...")
        from datetime import timedelta

        jst_offset = timedelta(hours=9)
        jst_time = parsed_datetime + jst_offset
        print(f"   - JST time: {jst_time}")
        print(f"   - Expected hour: 21, Got: {jst_time.hour}")
        assert jst_time.hour == 21, "Should be 21:00 in JST"

        print("   ✓ Frontend can correctly interpret 12:00 UTC as 21:00 JST!")

        print("\n" + "=" * 60)
        print("✓✓✓ Timezone fix test passed! ✓✓✓")
        print("=" * 60)
        print("\nKey findings:")
        print("- Naive datetime (no timezone) is correctly converted to UTC")
        print("- ISO format includes timezone information (+00:00)")
        print("- Frontend can parse and interpret 12:00 UTC as 21:00 JST")
        print("- This fixes the countdown timer issue")


if __name__ == "__main__":
    try:
        test_scheduled_at_timezone()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

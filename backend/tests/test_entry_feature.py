#!/usr/bin/env python3
"""Backend API entry feature validation test.

This script validates that the entry feature API endpoints and models are correctly defined.
It doesn't require a database connection.
"""

import os
import sys

# Set mock environment variables before importing anything
os.environ["CLERK_JWKS_URL"] = "https://test.clerk.accounts.dev/.well-known/jwks.json"
os.environ["CLERK_SECRET_KEY"] = "test_secret_key"
os.environ["NEON_DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_entry_models():
    """Test that entry models are correctly defined."""
    print("Testing entry models...")
    from app.models.models import BattleEntry, BattleRoom

    # Check BattleRoom model
    assert hasattr(BattleRoom, "id")
    assert hasattr(BattleRoom, "status")
    assert hasattr(BattleRoom, "scheduled_at")
    assert hasattr(BattleRoom, "created_at")
    print("  ✓ BattleRoom model is correctly defined")

    # Check BattleEntry model
    assert hasattr(BattleEntry, "id")
    assert hasattr(BattleEntry, "user_id")
    assert hasattr(BattleEntry, "room_id")
    assert hasattr(BattleEntry, "mobile_suit_id")
    assert hasattr(BattleEntry, "mobile_suit_snapshot")
    assert hasattr(BattleEntry, "created_at")
    print("  ✓ BattleEntry model is correctly defined")

    print("✓ All entry models are correctly defined\n")


def test_entry_api_endpoints():
    """Test that entry API endpoints are correctly defined."""
    print("Testing entry API endpoints...")
    from main import app

    # Get all routes
    routes = [route.path for route in app.routes]

    # Check required entry endpoints
    required_endpoints = [
        "/api/entries",
        "/api/entries/status",
    ]

    for endpoint in required_endpoints:
        assert endpoint in routes, f"Endpoint {endpoint} not found"
        print(f"  ✓ {endpoint} is defined")

    print("✓ All entry API endpoints are correctly defined\n")


def test_entry_migration():
    """Test that entry migration file exists."""
    print("Testing entry migration...")
    migration_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "alembic",
        "versions",
        "4a1b2c3d4e5f_add_battle_room_and_entry_tables.py",
    )

    assert os.path.exists(migration_path), "Entry migration file not found"
    print("  ✓ Entry migration file exists")

    # Check migration content
    with open(migration_path) as f:
        content = f.read()
        assert "create_table" in content.lower()
        assert "battle_rooms" in content.lower()
        assert "battle_entries" in content.lower()
        assert "mobile_suit_snapshot" in content.lower()

    print("✓ Entry migration file is correctly defined\n")


def test_entry_router():
    """Test that entry router exists and is imported."""
    print("Testing entry router...")
    import app.routers.entries as entries_router

    # Check that required functions exist
    assert hasattr(entries_router, "create_entry")
    assert hasattr(entries_router, "get_entry_status")
    assert hasattr(entries_router, "cancel_entry")
    print("  ✓ Entry router functions are defined")

    # Check that router is configured
    assert hasattr(entries_router, "router")
    print("  ✓ Entry router is configured")

    print("✓ Entry router is correctly defined\n")


if __name__ == "__main__":
    try:
        test_entry_models()
        test_entry_api_endpoints()
        test_entry_migration()
        test_entry_router()

        print("=" * 60)
        print("✓✓✓ All entry feature tests passed! ✓✓✓")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

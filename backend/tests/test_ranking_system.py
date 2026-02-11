#!/usr/bin/env python3
"""Ranking system validation test.

This script validates that the ranking system endpoints and models are correctly defined.
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


def test_ranking_models():
    """Test that ranking models are correctly defined."""
    print("Testing ranking models...")
    from app.models.models import Leaderboard, Season

    # Check Season model
    assert hasattr(Season, "id")
    assert hasattr(Season, "name")
    assert hasattr(Season, "start_date")
    assert hasattr(Season, "end_date")
    assert hasattr(Season, "is_active")
    assert hasattr(Season, "created_at")
    print("  ✓ Season model is correctly defined")

    # Check Leaderboard model
    assert hasattr(Leaderboard, "id")
    assert hasattr(Leaderboard, "season_id")
    assert hasattr(Leaderboard, "user_id")
    assert hasattr(Leaderboard, "pilot_name")
    assert hasattr(Leaderboard, "wins")
    assert hasattr(Leaderboard, "losses")
    assert hasattr(Leaderboard, "kills")
    assert hasattr(Leaderboard, "credits_earned")
    assert hasattr(Leaderboard, "updated_at")
    print("  ✓ Leaderboard model is correctly defined")

    print("✓ All ranking models are correctly defined\n")


def test_ranking_service():
    """Test that ranking service is correctly defined."""
    print("Testing ranking service...")
    from app.services.ranking_service import RankingService

    # Check that service has required methods
    assert hasattr(RankingService, "__init__")
    assert hasattr(RankingService, "get_or_create_current_season")
    assert hasattr(RankingService, "calculate_ranking")
    assert hasattr(RankingService, "get_current_rankings")
    print("  ✓ RankingService has required methods")

    print("✓ Ranking service is correctly defined\n")


def test_ranking_api_endpoints():
    """Test that ranking API endpoints are correctly defined."""
    print("Testing ranking API endpoints...")
    from main import app

    # Get all routes
    routes = [route.path for route in app.routes]

    # Check required endpoints
    required_endpoints = [
        "/api/rankings/current",
        "/api/rankings/pilot/{user_id}/profile",
    ]

    for endpoint in required_endpoints:
        assert endpoint in routes, f"Endpoint {endpoint} not found"
        print(f"  ✓ {endpoint} is defined")

    print("✓ All ranking API endpoints are correctly defined\n")


def test_ranking_migration():
    """Test that ranking migration file exists."""
    print("Testing ranking migration...")
    migration_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "alembic",
        "versions",
        "c3d4e5f6g7h8_add_season_and_leaderboard_tables.py",
    )

    assert os.path.exists(migration_path), "Migration file not found"
    print("  ✓ Migration file exists")

    # Check migration content
    with open(migration_path) as f:
        content = f.read()
        assert "create_table" in content.lower()
        assert "seasons" in content.lower()
        assert "leaderboards" in content.lower()

    print("✓ Ranking migration file is correctly defined\n")


def test_batch_integration():
    """Test that run_batch.py integrates ranking updates."""
    print("Testing batch integration...")
    batch_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "run_batch.py")

    assert os.path.exists(batch_path), "Batch script not found"
    print("  ✓ Batch script exists")

    # Check batch content
    with open(batch_path) as f:
        content = f.read()
        assert "RankingService" in content
        assert "update_rankings" in content

    print("✓ Batch script integrates ranking updates\n")


def test_profile_security():
    """Test that profile endpoint doesn't expose sensitive data."""
    print("Testing profile security...")
    from app.routers.rankings import PlayerProfile

    # Check that PlayerProfile doesn't have sensitive fields
    sensitive_fields = ["credits", "email", "clerk_id"]

    profile_fields = PlayerProfile.model_fields.keys()

    for field in sensitive_fields:
        assert (
            field not in profile_fields
        ), f"Sensitive field {field} found in PlayerProfile"

    print("  ✓ No sensitive fields in PlayerProfile")

    # Check that it has expected public fields
    expected_fields = ["pilot_name", "level", "wins", "losses", "kills", "mobile_suit", "skills"]

    for field in expected_fields:
        assert (
            field in profile_fields
        ), f"Expected field {field} not found in PlayerProfile"

    print("  ✓ All expected public fields present")

    print("✓ Profile security check passed\n")


if __name__ == "__main__":
    try:
        test_ranking_models()
        test_ranking_service()
        test_ranking_api_endpoints()
        test_ranking_migration()
        test_batch_integration()
        test_profile_security()

        print("=" * 60)
        print("✓✓✓ All ranking system tests passed! ✓✓✓")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
Backend API structure validation test.

This script validates that all the new API endpoints and models are correctly defined.
It doesn't require a database connection.
"""

import sys
import os

# Set mock environment variables before importing anything
os.environ["CLERK_JWKS_URL"] = "https://test.clerk.accounts.dev/.well-known/jwks.json"
os.environ["CLERK_SECRET_KEY"] = "test_secret_key"
os.environ["NEON_DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_models():
    """Test that models are correctly defined."""
    print("Testing models...")
    from app.models.models import Mission, BattleResult, BattleLog
    
    # Check Mission model
    assert hasattr(Mission, "id")
    assert hasattr(Mission, "name")
    assert hasattr(Mission, "difficulty")
    assert hasattr(Mission, "description")
    assert hasattr(Mission, "enemy_config")
    print("  ✓ Mission model is correctly defined")
    
    # Check BattleResult model
    assert hasattr(BattleResult, "id")
    assert hasattr(BattleResult, "user_id")
    assert hasattr(BattleResult, "mission_id")
    assert hasattr(BattleResult, "win_loss")
    assert hasattr(BattleResult, "logs")
    assert hasattr(BattleResult, "created_at")
    print("  ✓ BattleResult model is correctly defined")
    
    print("✓ All models are correctly defined\n")

def test_api_endpoints():
    """Test that API endpoints are correctly defined."""
    print("Testing API endpoints...")
    from main import app
    
    # Get all routes
    routes = [route.path for route in app.routes]
    
    # Check required endpoints
    required_endpoints = [
        "/api/missions",
        "/api/battles",
        "/api/battles/{battle_id}",
        "/api/battle/simulate",
    ]
    
    for endpoint in required_endpoints:
        assert endpoint in routes, f"Endpoint {endpoint} not found"
        print(f"  ✓ {endpoint} is defined")
    
    print("✓ All API endpoints are correctly defined\n")

def test_migration():
    """Test that migration file exists."""
    print("Testing migration...")
    migration_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "alembic",
        "versions",
        "27a590afd0ec_add_mission_and_battle_result_tables.py"
    )
    
    assert os.path.exists(migration_path), "Migration file not found"
    print("  ✓ Migration file exists")
    
    # Check migration content
    with open(migration_path, "r") as f:
        content = f.read()
        assert "create_table" in content.lower()
        assert "missions" in content.lower()
        assert "battle_results" in content.lower()
    
    print("✓ Migration file is correctly defined\n")

def test_seed_script():
    """Test that seed script exists and is valid."""
    print("Testing seed script...")
    seed_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "scripts",
        "seed_missions.py"
    )
    
    assert os.path.exists(seed_path), "Seed script not found"
    print("  ✓ Seed script exists")
    
    # Check seed content
    with open(seed_path, "r") as f:
        content = f.read()
        assert "Mission 01" in content
        assert "Mission 02" in content
        assert "Mission 03" in content
        assert "ザク小隊" in content
    
    print("✓ Seed script is correctly defined\n")

if __name__ == "__main__":
    try:
        test_models()
        test_api_endpoints()
        test_migration()
        test_seed_script()
        
        print("=" * 60)
        print("✓✓✓ All backend tests passed! ✓✓✓")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

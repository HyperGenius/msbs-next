#!/usr/bin/env python3
"""Manual verification script for terrain and detection features."""

import os
import sys

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


def create_test_unit(
    name: str, pos: Vector3, side: str, terrain_adapt: dict
) -> MobileSuit:
    """Create a test mobile suit."""
    return MobileSuit(
        name=name,
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=2.0,
        sensor_range=500.0,
        terrain_adaptability=terrain_adapt,
        position=pos,
        weapons=[
            Weapon(
                id="test_weapon",
                name="Test Weapon",
                power=30,
                range=600,
                accuracy=85,
            )
        ],
        side=side,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )


def test_terrain_effects():
    """Test terrain adaptability effects."""
    print("\n" + "=" * 60)
    print("Testing Terrain Adaptability")
    print("=" * 60)

    # Space specialist
    player_space = create_test_unit(
        "Space Gundam",
        Vector3(x=0, y=0, z=0),
        "PLAYER",
        {"SPACE": "S", "GROUND": "D", "COLONY": "A", "UNDERWATER": "D"},
    )

    # Enemy far away
    enemy1 = create_test_unit(
        "Enemy 1",
        Vector3(x=1000, y=0, z=0),
        "ENEMY",
        {"SPACE": "A", "GROUND": "A", "COLONY": "A", "UNDERWATER": "C"},
    )

    # Test in SPACE (player has S grade)
    print("\n[Test 1] Space Specialist in SPACE environment")
    sim_space = BattleSimulator(player_space, [enemy1], environment="SPACE")
    modifier = sim_space._get_terrain_modifier(player_space)
    print(f"  Terrain Modifier: {modifier} (expected 1.2)")
    print(f"  Effective Mobility: {player_space.mobility * modifier}")

    # Test in GROUND (player has D grade)
    player_ground = create_test_unit(
        "Space Gundam",
        Vector3(x=0, y=0, z=0),
        "PLAYER",
        {"SPACE": "S", "GROUND": "D", "COLONY": "A", "UNDERWATER": "D"},
    )
    enemy2 = create_test_unit(
        "Enemy 2",
        Vector3(x=1000, y=0, z=0),
        "ENEMY",
        {"SPACE": "A", "GROUND": "A", "COLONY": "A", "UNDERWATER": "C"},
    )

    print("\n[Test 2] Space Specialist in GROUND environment")
    sim_ground = BattleSimulator(player_ground, [enemy2], environment="GROUND")
    modifier_ground = sim_ground._get_terrain_modifier(player_ground)
    print(f"  Terrain Modifier: {modifier_ground} (expected 0.4)")
    print(f"  Effective Mobility: {player_ground.mobility * modifier_ground}")

    print("\n✓ Terrain effects test completed")


def test_detection_mechanics():
    """Test detection mechanics."""
    print("\n" + "=" * 60)
    print("Testing Detection Mechanics")
    print("=" * 60)

    # Player with limited sensor range
    player = create_test_unit(
        "Gundam",
        Vector3(x=0, y=0, z=0),
        "PLAYER",
        {"SPACE": "A", "GROUND": "A", "COLONY": "A", "UNDERWATER": "C"},
    )
    player.sensor_range = 400.0

    # Enemy within range
    enemy_close = create_test_unit(
        "Close Enemy",
        Vector3(x=300, y=0, z=0),
        "ENEMY",
        {"SPACE": "A", "GROUND": "A", "COLONY": "A", "UNDERWATER": "C"},
    )

    # Enemy outside range
    enemy_far = create_test_unit(
        "Far Enemy",
        Vector3(x=800, y=0, z=0),
        "ENEMY",
        {"SPACE": "A", "GROUND": "A", "COLONY": "A", "UNDERWATER": "C"},
    )

    print("\n[Test 3] Detection range test")
    sim = BattleSimulator(player, [enemy_close, enemy_far], environment="SPACE")

    print(f"  Player sensor range: {player.sensor_range}m")
    print("  Close enemy distance: 300m")
    print("  Far enemy distance: 800m")

    # Run detection phase
    sim._detection_phase()

    print(
        f"\n  Detected enemies (PLAYER team): {len(sim.team_detected_units['PLAYER'])}"
    )
    print(
        f"  Close enemy detected: {enemy_close.id in sim.team_detected_units['PLAYER']}"
    )
    print(f"  Far enemy detected: {enemy_far.id in sim.team_detected_units['PLAYER']}")

    # Check detection logs
    detection_logs = [log for log in sim.logs if log.action_type == "DETECTION"]
    print(f"\n  Detection logs generated: {len(detection_logs)}")
    for log in detection_logs:
        print(f"    - {log.message}")

    print("\n✓ Detection mechanics test completed")


def test_full_battle_simulation():
    """Test a full battle with terrain and detection."""
    print("\n" + "=" * 60)
    print("Testing Full Battle Simulation")
    print("=" * 60)

    # Player in ground environment with poor ground adaptability
    player = create_test_unit(
        "Space Gundam",
        Vector3(x=0, y=0, z=0),
        "PLAYER",
        {"SPACE": "S", "GROUND": "D", "COLONY": "A", "UNDERWATER": "D"},
    )
    player.sensor_range = 300.0
    player.weapons[0].power = 50
    player.weapons[0].accuracy = 90

    # Enemy with good ground adaptability
    enemy = create_test_unit(
        "Ground Zaku",
        Vector3(x=600, y=0, z=0),
        "ENEMY",
        {"SPACE": "B", "GROUND": "S", "COLONY": "A", "UNDERWATER": "C"},
    )
    enemy.max_hp = 80
    enemy.current_hp = 80
    enemy.sensor_range = 300.0

    print("\n[Test 4] Battle in GROUND environment")
    print("  Player: Space Gundam (GROUND: D)")
    print("  Enemy: Ground Zaku (GROUND: S)")

    sim = BattleSimulator(player, [enemy], environment="GROUND")

    # Run simulation
    max_turns = 30
    while not sim.is_finished and sim.turn < max_turns:
        sim.process_turn()

    print(f"\n  Battle duration: {sim.turn} turns")
    print(f"  Player HP: {player.current_hp}/{player.max_hp}")
    print(f"  Enemy HP: {enemy.current_hp}/{enemy.max_hp}")

    # Check for detection logs
    detection_logs = [log for log in sim.logs if log.action_type == "DETECTION"]
    move_logs = [log for log in sim.logs if log.action_type == "MOVE"]

    print(f"\n  Detection events: {len(detection_logs)}")
    print(f"  Movement actions: {len(move_logs)}")

    # Show some sample logs
    print("\n  Sample logs:")
    for log in sim.logs[:5]:
        print(f"    Turn {log.turn}: {log.message}")

    print("\n✓ Full battle simulation test completed")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TERRAIN AND DETECTION VERIFICATION")
    print("=" * 60)

    try:
        test_terrain_effects()
        test_detection_mechanics()
        test_full_battle_simulation()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

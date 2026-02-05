"""Integration test for tactics system.

This test demonstrates the complete tactics functionality end-to-end.
"""

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


def test_tactics_integration() -> None:
    """Integration test demonstrating all tactics options working together."""
    # Create player with WEAKEST priority and RANGED behavior
    player = MobileSuit(
        name="Advanced Gundam",
        max_hp=200,
        current_hp=200,
        armor=15,
        mobility=2.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="long_range_cannon",
                name="Long Range Cannon",
                power=40,
                range=600,
                accuracy=80,
            )
        ],
        side="PLAYER",
        tactics={"priority": "WEAKEST", "range": "RANGED"},
    )

    # Create multiple enemies with varying HP
    enemies = [
        MobileSuit(
            name="Heavy Zaku",
            max_hp=100,
            current_hp=100,
            armor=10,
            mobility=1.0,
            position=Vector3(x=400, y=0, z=0),
            weapons=[
                Weapon(
                    id="heavy_mg",
                    name="Heavy MG",
                    power=20,
                    range=350,
                    accuracy=60,
                )
            ],
            side="ENEMY",
            tactics={"priority": "CLOSEST", "range": "MELEE"},
        ),
        MobileSuit(
            name="Damaged Gouf",
            max_hp=80,
            current_hp=30,  # Weakest enemy
            armor=5,
            mobility=1.5,
            position=Vector3(x=500, y=200, z=0),
            weapons=[
                Weapon(
                    id="heat_rod",
                    name="Heat Rod",
                    power=25,
                    range=200,
                    accuracy=70,
                )
            ],
            side="ENEMY",
            tactics={"priority": "CLOSEST", "range": "FLEE"},
        ),
        MobileSuit(
            name="Scout Zaku",
            max_hp=70,
            current_hp=70,
            armor=3,
            mobility=2.0,
            position=Vector3(x=300, y=-100, z=0),
            weapons=[
                Weapon(
                    id="light_mg",
                    name="Light MG",
                    power=15,
                    range=400,
                    accuracy=75,
                )
            ],
            side="ENEMY",
            tactics={"priority": "RANDOM", "range": "BALANCED"},
        ),
    ]

    sim = BattleSimulator(player, enemies)

    # Run simulation
    max_turns = 30
    turns_executed = 0
    while not sim.is_finished and turns_executed < max_turns:
        sim.process_turn()
        turns_executed += 1

    # Verify simulation completed
    assert turns_executed > 0
    assert len(sim.logs) > 0

    # Verify tactics were applied
    # Player should target weakest enemy first
    player_attack_logs = [
        log
        for log in sim.logs
        if log.actor_id == player.id and log.action_type == "ATTACK"
    ]

    if player_attack_logs:
        # At least one attack should have targeted the damaged Gouf
        damaged_gouf = enemies[1]
        targeted_weak = any(
            log.target_id == damaged_gouf.id for log in player_attack_logs
        )
        assert (
            targeted_weak
        ), "Player with WEAKEST priority should have targeted the damaged Gouf"

    # Check that various movement patterns were used
    flee_logs = [log for log in sim.logs if "後退中" in log.message]
    ranged_logs = [log for log in sim.logs if "距離を取る" in log.message]
    melee_logs = [log for log in sim.logs if "接近中" in log.message]

    # At least some tactical movement should have occurred
    total_tactical_moves = len(flee_logs) + len(ranged_logs) + len(melee_logs)
    assert total_tactical_moves > 0, "Tactical movements should have been executed"

    print(f"✓ Integration test passed!")
    print(f"  - Turns executed: {turns_executed}")
    print(f"  - Total logs: {len(sim.logs)}")
    print(f"  - Player attacks: {len(player_attack_logs)}")
    print(f"  - Flee movements: {len(flee_logs)}")
    print(f"  - Ranged movements: {len(ranged_logs)}")
    print(f"  - Melee movements: {len(melee_logs)}")


if __name__ == "__main__":
    test_tactics_integration()

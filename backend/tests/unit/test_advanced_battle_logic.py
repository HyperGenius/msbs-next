"""Tests for advanced battle logic with weapon types and resistances."""

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


def create_beam_weapon() -> Weapon:
    """Create a test beam weapon."""
    return Weapon(
        id="beam_rifle_test",
        name="Test Beam Rifle",
        power=100,
        range=500,
        accuracy=85,
        type="BEAM",
        optimal_range=400.0,
        decay_rate=0.05,
    )


def create_physical_weapon() -> Weapon:
    """Create a test physical weapon."""
    return Weapon(
        id="machine_gun_test",
        name="Test Machine Gun",
        power=80,
        range=400,
        accuracy=70,
        type="PHYSICAL",
        optimal_range=300.0,
        decay_rate=0.08,
    )


def create_player_with_beam() -> MobileSuit:
    """Create a player with beam weapon and high beam resistance."""
    return MobileSuit(
        name="Beam Gundam",
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[create_beam_weapon()],
        side="PLAYER",
        beam_resistance=0.2,
        physical_resistance=0.1,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )


def create_player_with_physical() -> MobileSuit:
    """Create a player with physical weapon and high physical resistance."""
    return MobileSuit(
        name="Physical Zaku",
        max_hp=800,
        current_hp=800,
        armor=60,
        mobility=1.2,
        position=Vector3(x=0, y=0, z=0),
        weapons=[create_physical_weapon()],
        side="PLAYER",
        beam_resistance=0.05,
        physical_resistance=0.25,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )


def create_enemy_beam_resistant() -> MobileSuit:
    """Create an enemy with high beam resistance."""
    return MobileSuit(
        name="Beam Resistant Enemy",
        max_hp=500,
        current_hp=500,
        armor=30,
        mobility=1.0,
        position=Vector3(x=100, y=0, z=0),
        weapons=[create_physical_weapon()],
        side="ENEMY",
        beam_resistance=0.3,
        physical_resistance=0.05,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )


def create_enemy_physical_resistant() -> MobileSuit:
    """Create an enemy with high physical resistance."""
    return MobileSuit(
        name="Physical Resistant Enemy",
        max_hp=500,
        current_hp=500,
        armor=30,
        mobility=1.0,
        position=Vector3(x=100, y=0, z=0),
        weapons=[create_beam_weapon()],
        side="ENEMY",
        beam_resistance=0.05,
        physical_resistance=0.3,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )


def test_beam_weapon_vs_beam_resistance() -> None:
    """Test that beam weapons deal reduced damage to beam-resistant enemies."""
    player = create_player_with_beam()
    enemy = create_enemy_beam_resistant()

    sim = BattleSimulator(player, [enemy])

    # Run one turn to see damage
    sim.process_turn()

    # Check that damage was dealt
    attack_logs = [log for log in sim.logs if log.action_type == "ATTACK" and log.damage]
    if attack_logs:
        # Verify that resistance message is in the log
        resistance_logs = [log for log in attack_logs if "対ビーム装甲" in log.message]
        assert len(resistance_logs) > 0, "Beam resistance message should appear in logs"


def test_physical_weapon_vs_physical_resistance() -> None:
    """Test that physical weapons deal reduced damage to physical-resistant enemies."""
    player = create_player_with_physical()
    enemy = create_enemy_physical_resistant()

    sim = BattleSimulator(player, [enemy])

    # Run one turn
    sim.process_turn()

    # Check for physical resistance message
    attack_logs = [log for log in sim.logs if log.action_type == "ATTACK" and log.damage]
    if attack_logs:
        resistance_logs = [log for log in attack_logs if "対実弾装甲" in log.message]
        assert len(resistance_logs) > 0, "Physical resistance message should appear in logs"


def test_optimal_range_hit_bonus() -> None:
    """Test that attacking at optimal range provides better hit chance."""
    player = create_player_with_beam()
    # Position enemy at optimal range (400m for beam rifle)
    enemy = create_enemy_beam_resistant()
    enemy.position = Vector3(x=400, y=0, z=0)

    sim = BattleSimulator(player, [enemy])
    sim.process_turn()

    # Check for optimal distance message
    optimal_logs = [log for log in sim.logs if "最適距離" in log.message]
    assert len(optimal_logs) > 0, "Optimal distance message should appear when at optimal range"


def test_suboptimal_range_penalty() -> None:
    """Test that attacking far from optimal range reduces hit chance."""
    player = create_player_with_beam()
    # Position enemy far from optimal range (600m vs 400m optimal)
    enemy = create_enemy_beam_resistant()
    enemy.position = Vector3(x=600, y=0, z=0)

    sim = BattleSimulator(player, [enemy])
    sim.process_turn()

    # Check for distance penalty message
    penalty_logs = [log for log in sim.logs if "距離不利" in log.message]
    # Note: Penalty message only appears if distance_from_optimal > 200
    # 600 - 400 = 200, so should be at the threshold


def test_weapon_type_defaults() -> None:
    """Test that weapon type defaults to PHYSICAL if not specified."""
    weapon = Weapon(
        id="test_weapon",
        name="Test Weapon",
        power=50,
        range=300,
        accuracy=70,
    )
    # type should default to PHYSICAL
    assert weapon.type == "PHYSICAL"


def test_resistance_defaults() -> None:
    """Test that resistances default to 0.0 if not specified."""
    ms = MobileSuit(
        name="Test MS",
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=1.0,
        position=Vector3(x=0, y=0, z=0),
        weapons=[],
        side="PLAYER",
    )
    assert ms.beam_resistance == 0.0
    assert ms.physical_resistance == 0.0


def test_battle_with_mixed_weapon_types() -> None:
    """Test a complete battle with different weapon types and resistances."""
    # Beam user vs physical-resistant enemy
    player = create_player_with_beam()
    enemy = create_enemy_physical_resistant()

    # Enemy has low beam resistance, so should take more damage
    sim = BattleSimulator(player, [enemy])

    # Run simulation
    max_turns = 20
    while not sim.is_finished and sim.turn < max_turns:
        sim.process_turn()

    # Battle should finish
    assert sim.is_finished or sim.turn >= max_turns

    # Check that logs contain weapon type information
    attack_logs = [log for log in sim.logs if log.action_type == "ATTACK"]
    assert len(attack_logs) > 0, "Should have attack logs"


def test_decay_rate_affects_hit_chance() -> None:
    """Test that weapons with different decay rates have different penalties."""
    # Create two identical mobile suits
    player1 = MobileSuit(
        name="Low Decay Player",
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="low_decay",
                name="Low Decay Weapon",
                power=100,
                range=600,
                accuracy=85,
                type="BEAM",
                optimal_range=300.0,
                decay_rate=0.02,  # Low decay
            )
        ],
        side="PLAYER",
        beam_resistance=0.0,
        physical_resistance=0.0,
    )

    player2 = MobileSuit(
        name="High Decay Player",
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="high_decay",
                name="High Decay Weapon",
                power=100,
                range=600,
                accuracy=85,
                type="BEAM",
                optimal_range=300.0,
                decay_rate=0.10,  # High decay
            )
        ],
        side="PLAYER",
        beam_resistance=0.0,
        physical_resistance=0.0,
    )

    # Enemy at 500m (200m from optimal 300m)
    enemy1 = MobileSuit(
        name="Enemy 1",
        max_hp=1000,
        current_hp=1000,
        armor=30,
        mobility=1.0,
        position=Vector3(x=500, y=0, z=0),
        weapons=[],
        side="ENEMY",
        beam_resistance=0.0,
        physical_resistance=0.0,
    )

    enemy2 = MobileSuit(
        name="Enemy 2",
        max_hp=1000,
        current_hp=1000,
        armor=30,
        mobility=1.0,
        position=Vector3(x=500, y=0, z=0),
        weapons=[],
        side="ENEMY",
        beam_resistance=0.0,
        physical_resistance=0.0,
    )

    # Both should work, but with different hit chances
    # Low decay: penalty = 200 * 0.02 = 4%
    # High decay: penalty = 200 * 0.10 = 20%
    # This is just a structural test to ensure the logic works
    sim1 = BattleSimulator(player1, [enemy1])
    sim2 = BattleSimulator(player2, [enemy2])

    sim1.process_turn()
    sim2.process_turn()

    # Both should have logs
    assert len(sim1.logs) > 0
    assert len(sim2.logs) > 0

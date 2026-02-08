"""Tests for terrain adaptability and detection system."""

from app.engine.simulation import BattleSimulator, TERRAIN_ADAPTABILITY_MODIFIERS
from app.models.models import MobileSuit, Vector3, Weapon


def create_test_player(terrain_adaptability: dict[str, str] | None = None) -> MobileSuit:
    """Create a test player mobile suit."""
    if terrain_adaptability is None:
        terrain_adaptability = {"SPACE": "A", "GROUND": "A", "COLONY": "A", "UNDERWATER": "C"}
    
    return MobileSuit(
        name="Test Gundam",
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=2.0,
        sensor_range=500.0,
        terrain_adaptability=terrain_adaptability,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="beam_rifle",
                name="Beam Rifle",
                power=30,
                range=500,
                accuracy=85,
            )
        ],
        side="PLAYER",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )


def create_test_enemy(
    name: str,
    position: Vector3,
    sensor_range: float = 400.0,
    terrain_adaptability: dict[str, str] | None = None,
) -> MobileSuit:
    """Create a test enemy mobile suit."""
    if terrain_adaptability is None:
        terrain_adaptability = {"SPACE": "A", "GROUND": "B", "COLONY": "A", "UNDERWATER": "D"}
    
    return MobileSuit(
        name=name,
        max_hp=80,
        current_hp=80,
        armor=5,
        mobility=1.2,
        sensor_range=sensor_range,
        terrain_adaptability=terrain_adaptability,
        position=position,
        weapons=[
            Weapon(
                id="zaku_mg",
                name="Zaku Machine Gun",
                power=15,
                range=400,
                accuracy=70,
            )
        ],
        side="ENEMY",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )


def test_terrain_adaptability_modifiers() -> None:
    """Test that terrain adaptability modifiers are correctly defined."""
    assert TERRAIN_ADAPTABILITY_MODIFIERS["S"] == 1.2
    assert TERRAIN_ADAPTABILITY_MODIFIERS["A"] == 1.0
    assert TERRAIN_ADAPTABILITY_MODIFIERS["B"] == 0.8
    assert TERRAIN_ADAPTABILITY_MODIFIERS["C"] == 0.6
    assert TERRAIN_ADAPTABILITY_MODIFIERS["D"] == 0.4


def test_terrain_modifier_calculation() -> None:
    """Test that terrain modifiers are correctly calculated."""
    # Space specialist in space
    player = create_test_player(terrain_adaptability={"SPACE": "S", "GROUND": "D", "COLONY": "A", "UNDERWATER": "D"})
    enemies = [create_test_enemy("Enemy", Vector3(x=2000, y=0, z=0))]
    
    sim = BattleSimulator(player, enemies, environment="SPACE")
    modifier = sim._get_terrain_modifier(player)
    assert modifier == 1.2  # S grade
    
    # Same unit in ground environment
    sim_ground = BattleSimulator(player, enemies, environment="GROUND")
    modifier_ground = sim_ground._get_terrain_modifier(player)
    assert modifier_ground == 0.4  # D grade


def test_terrain_affects_movement_distance() -> None:
    """Test that terrain adaptability affects movement distance."""
    # Create two identical units with different terrain adaptability
    player_space_specialist = create_test_player(
        terrain_adaptability={"SPACE": "S", "GROUND": "D", "COLONY": "A", "UNDERWATER": "D"}
    )
    player_ground_specialist = create_test_player(
        terrain_adaptability={"SPACE": "D", "GROUND": "S", "COLONY": "A", "UNDERWATER": "D"}
    )
    
    # Place enemy far away so units will move
    enemy_pos = Vector3(x=2000, y=0, z=0)
    enemies1 = [create_test_enemy("Enemy 1", enemy_pos)]
    enemies2 = [create_test_enemy("Enemy 2", enemy_pos)]
    
    # Simulate in SPACE
    sim_space = BattleSimulator(player_space_specialist, enemies1, environment="SPACE")
    sim_space.process_turn()
    
    # Space specialist should move further
    space_specialist_distance = player_space_specialist.position.x
    
    # Simulate in GROUND
    sim_ground = BattleSimulator(player_ground_specialist, enemies2, environment="GROUND")
    sim_ground.process_turn()
    
    # Ground specialist should move further in ground
    # (But since we're comparing space specialist in space vs ground specialist in ground,
    # both should have S grade and move similar distances)
    # Let's test the opposite: space specialist in ground
    player_space_in_ground = create_test_player(
        terrain_adaptability={"SPACE": "S", "GROUND": "D", "COLONY": "A", "UNDERWATER": "D"}
    )
    enemies3 = [create_test_enemy("Enemy 3", enemy_pos)]
    sim_ground2 = BattleSimulator(player_space_in_ground, enemies3, environment="GROUND")
    sim_ground2.process_turn()
    
    # Space specialist in ground should move less than ground specialist in ground
    space_in_ground_distance = player_space_in_ground.position.x
    ground_specialist_distance = player_ground_specialist.position.x
    
    # Ground specialist should have moved further
    assert ground_specialist_distance > space_in_ground_distance


def test_detection_phase_basic() -> None:
    """Test that detection phase correctly identifies enemies in range."""
    player = create_test_player()
    player.sensor_range = 600.0
    
    # Enemy within sensor range
    enemy_close = create_test_enemy("Close Enemy", Vector3(x=400, y=0, z=0))
    # Enemy outside sensor range
    enemy_far = create_test_enemy("Far Enemy", Vector3(x=800, y=0, z=0))
    
    sim = BattleSimulator(player, [enemy_close, enemy_far], environment="SPACE")
    
    # Before detection phase, no enemies detected
    assert len(sim.team_detected_units["PLAYER"]) == 0
    
    # Run detection phase
    sim._detection_phase()
    
    # Close enemy should be detected
    assert enemy_close.id in sim.team_detected_units["PLAYER"]
    # Far enemy should not be detected
    assert enemy_far.id not in sim.team_detected_units["PLAYER"]


def test_detection_logs_generated() -> None:
    """Test that detection logs are generated when enemies are discovered."""
    player = create_test_player()
    player.sensor_range = 600.0
    
    enemy = create_test_enemy("Enemy", Vector3(x=400, y=0, z=0))
    
    sim = BattleSimulator(player, [enemy], environment="SPACE")
    sim.turn = 1
    
    # Run detection phase
    sim._detection_phase()
    
    # Check that detection logs were created (both units detect each other)
    detection_logs = [log for log in sim.logs if log.action_type == "DETECTION"]
    assert len(detection_logs) >= 1  # At least one detection occurred
    assert any("発見" in log.message for log in detection_logs)


def test_detection_shared_among_team() -> None:
    """Test that detected enemies are shared among team members."""
    player = create_test_player()
    player.sensor_range = 600.0
    player.position = Vector3(x=0, y=0, z=0)
    
    # Create another player unit (ally)
    ally = create_test_player()
    ally.name = "Ally Gundam"
    ally.sensor_range = 300.0  # Shorter range
    ally.position = Vector3(x=0, y=500, z=0)  # Different position
    
    # Enemy is close to player but far from ally
    enemy = create_test_enemy("Enemy", Vector3(x=400, y=0, z=0))
    
    sim = BattleSimulator(player, [enemy], environment="SPACE")
    
    # Manually add ally to units (for this test)
    sim.units.append(ally)
    
    # Run detection phase
    sim._detection_phase()
    
    # Enemy should be in PLAYER team's detected units
    # (both player and ally are on PLAYER team)
    assert enemy.id in sim.team_detected_units["PLAYER"]


def test_target_selection_requires_detection() -> None:
    """Test that units can only target detected enemies."""
    player = create_test_player()
    player.sensor_range = 300.0  # Short range
    
    # Enemy outside sensor range
    enemy = create_test_enemy("Enemy", Vector3(x=500, y=0, z=0))
    
    sim = BattleSimulator(player, [enemy], environment="SPACE")
    
    # Before detection, target selection should return None
    target = sim._select_target(player)
    assert target is None
    
    # Run detection phase (enemy is out of range, so won't be detected)
    sim._detection_phase()
    target = sim._select_target(player)
    assert target is None
    
    # Manually add enemy to detected units
    sim.team_detected_units["PLAYER"].add(enemy.id)
    
    # Now target selection should work
    target = sim._select_target(player)
    assert target is not None
    assert target.id == enemy.id


def test_enemy_detection_of_player() -> None:
    """Test that enemies can also detect the player."""
    player = create_test_player()
    
    # Enemy with sensor range that can detect player
    enemy = create_test_enemy("Enemy", Vector3(x=300, y=0, z=0), sensor_range=400.0)
    
    sim = BattleSimulator(player, [enemy], environment="SPACE")
    
    # Before detection phase, enemy hasn't detected player
    assert len(sim.team_detected_units["ENEMY"]) == 0
    
    # Run detection phase
    sim._detection_phase()
    
    # Enemy should have detected player
    assert player.id in sim.team_detected_units["ENEMY"]


def test_detection_log_shows_distance() -> None:
    """Test that detection logs include distance information."""
    player = create_test_player()
    player.sensor_range = 600.0
    
    enemy = create_test_enemy("Enemy", Vector3(x=400, y=0, z=0))
    
    sim = BattleSimulator(player, [enemy], environment="SPACE")
    sim.turn = 1
    
    # Run detection phase
    sim._detection_phase()
    
    # Check detection log includes distance
    detection_logs = [log for log in sim.logs if log.action_type == "DETECTION"]
    assert len(detection_logs) >= 1
    # At least one log should mention distance
    assert any("400" in log.message or "距離" in log.message for log in detection_logs)


def test_full_battle_with_detection() -> None:
    """Test a complete battle with detection mechanics."""
    player = create_test_player()
    player.sensor_range = 300.0  # Shorter range so enemy starts undetected
    player.weapons[0].power = 50  # Strong weapon
    player.weapons[0].accuracy = 95
    
    # Enemy far away, will need to be detected first
    enemy = create_test_enemy("Enemy", Vector3(x=800, y=0, z=0), sensor_range=300.0)
    
    sim = BattleSimulator(player, [enemy], environment="SPACE")
    
    # Run simulation
    max_turns = 50
    while not sim.is_finished and sim.turn < max_turns:
        sim.process_turn()
    
    # Check that detection occurred at some point
    detection_logs = [log for log in sim.logs if log.action_type == "DETECTION"]
    assert len(detection_logs) > 0, "Detection should have occurred during the battle"
    
    # Battle should complete
    assert sim.turn < max_turns or sim.is_finished

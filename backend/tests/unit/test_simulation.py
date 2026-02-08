"""Tests for the battle simulation engine."""

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


def create_test_player() -> MobileSuit:
    """Create a test player mobile suit."""
    return MobileSuit(
        name="Test Gundam",
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=2.0,
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


def create_test_enemy(name: str, position: Vector3) -> MobileSuit:
    """Create a test enemy mobile suit."""
    return MobileSuit(
        name=name,
        max_hp=80,
        current_hp=80,
        armor=5,
        mobility=1.2,
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


def test_simulator_initialization() -> None:
    """Test that simulator initializes correctly."""
    player = create_test_player()
    enemies = [
        create_test_enemy("Enemy 1", Vector3(x=500, y=0, z=0)),
        create_test_enemy("Enemy 2", Vector3(x=500, y=200, z=0)),
    ]

    sim = BattleSimulator(player, enemies)

    assert sim.player == player
    assert len(sim.enemies) == 2
    assert len(sim.units) == 3
    assert sim.turn == 0
    assert not sim.is_finished


def test_process_turn_order() -> None:
    """Test that units act in mobility order."""
    player = create_test_player()
    player.mobility = 1.0  # Lower mobility
    enemies = [
        create_test_enemy("Fast Enemy", Vector3(x=500, y=0, z=0)),
    ]
    enemies[0].mobility = 2.0  # Higher mobility

    sim = BattleSimulator(player, enemies)
    sim.process_turn()

    # First log should be from the faster unit (enemy in this case)
    # They might move or attack depending on distance
    assert len(sim.logs) > 0
    assert sim.turn == 1


def test_player_vs_enemies_victory() -> None:
    """Test that battle ends when all enemies are defeated."""
    player = create_test_player()
    # Make player very strong
    player.weapons[0].power = 200
    player.weapons[0].accuracy = 100

    enemies = [
        create_test_enemy("Weak Enemy", Vector3(x=100, y=0, z=0)),
    ]

    sim = BattleSimulator(player, enemies)

    # Run simulation
    max_turns = 50
    while not sim.is_finished and sim.turn < max_turns:
        sim.process_turn()

    # Player should win
    assert player.current_hp > 0
    assert enemies[0].current_hp == 0
    assert sim.is_finished


def test_player_defeat() -> None:
    """Test that battle ends when player is defeated."""
    player = create_test_player()
    player.max_hp = 10
    player.current_hp = 10
    player.armor = 0

    enemies = [
        create_test_enemy("Strong Enemy", Vector3(x=100, y=0, z=0)),
    ]
    # Make enemy very strong
    enemies[0].weapons[0].power = 200
    enemies[0].weapons[0].accuracy = 100

    sim = BattleSimulator(player, enemies)

    # Run simulation
    max_turns = 50
    while not sim.is_finished and sim.turn < max_turns:
        sim.process_turn()

    # Player should lose
    assert player.current_hp == 0
    assert sim.is_finished


def test_multiple_enemies() -> None:
    """Test battle with multiple enemies."""
    player = create_test_player()
    enemies = [
        create_test_enemy("Enemy 1", Vector3(x=500, y=-200, z=0)),
        create_test_enemy("Enemy 2", Vector3(x=500, y=0, z=0)),
        create_test_enemy("Enemy 3", Vector3(x=500, y=200, z=0)),
    ]

    sim = BattleSimulator(player, enemies)

    # Run simulation
    max_turns = 50
    while not sim.is_finished and sim.turn < max_turns:
        sim.process_turn()

    # Battle should finish one way or another
    # Either player wins or loses
    alive_enemies = sum(1 for e in enemies if e.current_hp > 0)
    if player.current_hp > 0:
        assert alive_enemies == 0
    else:
        assert player.current_hp == 0


def test_logs_generated() -> None:
    """Test that battle logs are generated."""
    player = create_test_player()
    enemies = [
        create_test_enemy("Enemy 1", Vector3(x=500, y=0, z=0)),
    ]

    sim = BattleSimulator(player, enemies)

    # Run a few turns
    for _ in range(5):
        if not sim.is_finished:
            sim.process_turn()

    # Should have some logs
    assert len(sim.logs) > 0
    # All logs should have turn numbers
    for log in sim.logs:
        assert log.turn > 0
        assert log.message != ""


def test_tactics_weakest_priority() -> None:
    """Test that WEAKEST priority targets the lowest HP enemy."""
    player = create_test_player()
    player.tactics = {"priority": "WEAKEST", "range": "BALANCED"}

    # Create enemies with different HP levels
    enemies = [
        create_test_enemy("Strong Enemy", Vector3(x=300, y=0, z=0)),
        create_test_enemy("Weak Enemy", Vector3(x=500, y=0, z=0)),
        create_test_enemy("Medium Enemy", Vector3(x=400, y=0, z=0)),
    ]
    enemies[0].current_hp = 80  # Strong
    enemies[1].current_hp = 20  # Weak (should be targeted)
    enemies[2].current_hp = 50  # Medium

    sim = BattleSimulator(player, enemies)

    # Run detection phase so enemies are detected
    sim._detection_phase()

    # Get target selection
    target = sim._select_target(player)

    # Should target the weakest enemy
    assert target is not None
    assert target.name == "Weak Enemy"
    assert target.current_hp == 20


def test_tactics_ranged_behavior() -> None:
    """Test that RANGED tactics maintain distance from enemy."""
    player = create_test_player()
    player.tactics = {"priority": "CLOSEST", "range": "RANGED"}
    player.position = Vector3(x=0, y=0, z=0)

    enemies = [
        create_test_enemy("Close Enemy", Vector3(x=100, y=0, z=0)),
    ]

    sim = BattleSimulator(player, enemies)

    # Run one turn
    sim.process_turn()

    # Player should try to maintain distance (not rush forward)
    # Check that there's a movement log indicating distance maintenance
    move_logs = [
        log
        for log in sim.logs
        if log.action_type == "MOVE" and log.actor_id == player.id
    ]
    if move_logs:
        # Should contain message about maintaining distance or moving away
        assert any(
            "距離を取る" in log.message or "射程内" in log.message for log in move_logs
        )


def test_tactics_flee_behavior() -> None:
    """Test that FLEE tactics cause unit to retreat."""
    player = create_test_player()
    player.tactics = {"priority": "CLOSEST", "range": "FLEE"}
    player.position = Vector3(x=0, y=0, z=0)
    initial_distance = 500.0

    enemies = [
        create_test_enemy("Enemy", Vector3(x=initial_distance, y=0, z=0)),
    ]

    sim = BattleSimulator(player, enemies)

    # Run one turn
    sim.process_turn()

    # Player should be moving away from enemy
    move_logs = [
        log
        for log in sim.logs
        if log.action_type == "MOVE" and log.actor_id == player.id
    ]
    if move_logs:
        # Should contain message about retreating
        assert any("後退中" in log.message for log in move_logs)


def test_tactics_default_values() -> None:
    """Test that MobileSuit has default tactics values."""
    player = create_test_player()

    # Should have default tactics
    assert player.tactics is not None
    assert "priority" in player.tactics
    assert "range" in player.tactics
    assert player.tactics["priority"] in ["CLOSEST", "WEAKEST", "RANDOM"]
    assert player.tactics["range"] in ["MELEE", "RANGED", "BALANCED", "FLEE"]


def test_calculate_strategic_value() -> None:
    """Test strategic value calculation."""
    player = create_test_player()
    
    # Create enemies with different specs
    weak_enemy = create_test_enemy("Weak Zaku", Vector3(x=300, y=0, z=0))
    weak_enemy.max_hp = 50
    weak_enemy.weapons[0].power = 10
    
    strong_enemy = create_test_enemy("Strong Gundam", Vector3(x=500, y=0, z=0))
    strong_enemy.max_hp = 150
    strong_enemy.weapons[0].power = 40
    
    enemies = [weak_enemy, strong_enemy]
    sim = BattleSimulator(player, enemies)
    
    # Calculate strategic values
    weak_value = sim._calculate_strategic_value(weak_enemy)
    strong_value = sim._calculate_strategic_value(strong_enemy)
    
    # Strong enemy should have higher strategic value
    assert strong_value > weak_value
    assert weak_value > 0
    assert strong_value > 0


def test_calculate_threat_level() -> None:
    """Test threat level calculation."""
    player = create_test_player()
    player.current_hp = 100
    player.position = Vector3(x=0, y=0, z=0)
    
    # Create enemies at different distances
    close_enemy = create_test_enemy("Close Enemy", Vector3(x=100, y=0, z=0))
    close_enemy.weapons[0].power = 20
    
    far_enemy = create_test_enemy("Far Enemy", Vector3(x=500, y=0, z=0))
    far_enemy.weapons[0].power = 20
    
    enemies = [close_enemy, far_enemy]
    sim = BattleSimulator(player, enemies)
    
    # Calculate threat levels
    close_threat = sim._calculate_threat_level(player, close_enemy)
    far_threat = sim._calculate_threat_level(player, far_enemy)
    
    # Close enemy should have higher threat level
    assert close_threat > far_threat
    assert close_threat > 0
    assert far_threat > 0


def test_tactics_strongest_priority() -> None:
    """Test that STRONGEST priority targets the highest strategic value enemy."""
    player = create_test_player()
    player.tactics = {"priority": "STRONGEST", "range": "BALANCED"}
    player.position = Vector3(x=0, y=0, z=0)
    
    # Create enemies with different strategic values
    weak_enemy = create_test_enemy("Weak Zaku", Vector3(x=200, y=0, z=0))
    weak_enemy.max_hp = 50
    weak_enemy.weapons[0].power = 10
    
    strong_enemy = create_test_enemy("Strong Gundam", Vector3(x=400, y=0, z=0))
    strong_enemy.max_hp = 150
    strong_enemy.weapons[0].power = 40
    
    medium_enemy = create_test_enemy("Medium GM", Vector3(x=300, y=0, z=0))
    medium_enemy.max_hp = 100
    medium_enemy.weapons[0].power = 25
    
    enemies = [weak_enemy, strong_enemy, medium_enemy]
    sim = BattleSimulator(player, enemies)
    
    # Run detection phase so enemies are detected
    sim._detection_phase()
    
    # Get target selection
    target = sim._select_target(player)
    
    # Should target the strongest enemy (highest strategic value)
    assert target is not None
    assert target.name == "Strong Gundam"


def test_tactics_threat_priority() -> None:
    """Test that THREAT priority targets the highest threat enemy."""
    player = create_test_player()
    player.tactics = {"priority": "THREAT", "range": "BALANCED"}
    player.position = Vector3(x=0, y=0, z=0)
    player.current_hp = 50  # Lower HP to make threat more significant
    
    # Create enemies at different distances with different power
    close_weak = create_test_enemy("Close Weak", Vector3(x=100, y=0, z=0))
    close_weak.weapons[0].power = 15
    
    far_strong = create_test_enemy("Far Strong", Vector3(x=500, y=0, z=0))
    far_strong.weapons[0].power = 40
    
    close_strong = create_test_enemy("Close Strong", Vector3(x=150, y=0, z=0))
    close_strong.weapons[0].power = 30
    
    enemies = [close_weak, far_strong, close_strong]
    sim = BattleSimulator(player, enemies)
    
    # Run detection phase so enemies are detected
    sim._detection_phase()
    
    # Get target selection
    target = sim._select_target(player)
    
    # Should target Close Strong (highest threat: closer distance + higher power than Close Weak)
    assert target is not None
    assert target.name == "Close Strong"


def test_target_selection_with_multiple_tactics() -> None:
    """Test that different tactics produce different target selections."""
    # Setup: Same scenario with three different enemies
    def create_scenario():
        player = create_test_player()
        player.position = Vector3(x=0, y=0, z=0)
        player.current_hp = 100
        
        # Close weak enemy
        close_weak = create_test_enemy("Close Zaku", Vector3(x=150, y=0, z=0))
        close_weak.max_hp = 50
        close_weak.current_hp = 50
        close_weak.weapons[0].power = 10
        
        # Far strong enemy
        far_strong = create_test_enemy("Far Gundam", Vector3(x=450, y=0, z=0))
        far_strong.max_hp = 150
        far_strong.current_hp = 150
        far_strong.weapons[0].power = 40
        
        # Medium enemy, damaged
        medium_damaged = create_test_enemy("Damaged GM", Vector3(x=300, y=0, z=0))
        medium_damaged.max_hp = 100
        medium_damaged.current_hp = 30  # Low HP
        medium_damaged.weapons[0].power = 25
        
        return player, [close_weak, far_strong, medium_damaged]
    
    # Test CLOSEST
    player, enemies = create_scenario()
    player.tactics = {"priority": "CLOSEST", "range": "BALANCED"}
    sim = BattleSimulator(player, enemies)
    sim._detection_phase()
    target = sim._select_target(player)
    assert target is not None
    assert target.name == "Close Zaku"
    
    # Test WEAKEST
    player, enemies = create_scenario()
    player.tactics = {"priority": "WEAKEST", "range": "BALANCED"}
    sim = BattleSimulator(player, enemies)
    sim._detection_phase()
    target = sim._select_target(player)
    assert target is not None
    assert target.name == "Damaged GM"
    
    # Test STRONGEST
    player, enemies = create_scenario()
    player.tactics = {"priority": "STRONGEST", "range": "BALANCED"}
    sim = BattleSimulator(player, enemies)
    sim._detection_phase()
    target = sim._select_target(player)
    assert target is not None
    assert target.name == "Far Gundam"

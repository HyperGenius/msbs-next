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
        team_id="PLAYER_TEAM",
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
        team_id="ENEMY_TEAM",
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


# === team_id 関連のテスト ===


def test_same_team_id_no_attack() -> None:
    """同じteam_idの機体同士は攻撃しないこと."""
    player = create_test_player()
    player.team_id = "TEAM_A"

    # 敵も同じteam_idに設定
    ally = create_test_enemy("Ally Zaku", Vector3(x=100, y=0, z=0))
    ally.team_id = "TEAM_A"

    sim = BattleSimulator(player, [ally])
    sim._detection_phase()

    # プレイヤーのターゲット選択 → 同チームなので None
    target = sim._select_target(player)
    assert target is None


def test_different_team_id_attack() -> None:
    """異なるteam_idの機体同士は攻撃対象になること."""
    player = create_test_player()
    player.team_id = "TEAM_A"

    enemy = create_test_enemy("Enemy Zaku", Vector3(x=100, y=0, z=0))
    enemy.team_id = "TEAM_B"

    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    target = sim._select_target(player)
    assert target is not None
    assert target.name == "Enemy Zaku"


def test_mixed_side_same_team_no_attack() -> None:
    """sideが異なっても同じteam_idなら攻撃しないこと."""
    player = create_test_player()
    player.side = "PLAYER"
    player.team_id = "ALLIANCE"

    # sideはENEMYだがteam_idが同じ
    ally = create_test_enemy("NPC Ally", Vector3(x=100, y=0, z=0))
    ally.side = "ENEMY"
    ally.team_id = "ALLIANCE"

    sim = BattleSimulator(player, [ally])
    sim._detection_phase()

    # 同チームなので攻撃対象にならない
    target = sim._select_target(player)
    assert target is None


def test_solo_participants_auto_team_id() -> None:
    """team_id未設定のユニットにはユニットIDが自動付与されること."""
    player = MobileSuit(
        name="Solo Player",
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
        team_id=None,  # 明示的にNone
    )

    enemy = MobileSuit(
        name="Solo Enemy",
        max_hp=80,
        current_hp=80,
        armor=5,
        mobility=1.2,
        position=Vector3(x=100, y=0, z=0),
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
        team_id=None,  # 明示的にNone
    )

    BattleSimulator(player, [enemy])

    # team_idが自動的にユニットIDに設定される
    assert player.team_id == str(player.id)
    assert enemy.team_id == str(enemy.id)
    assert player.team_id != enemy.team_id


def test_battle_royale_three_solo_units() -> None:
    """3機のソロ参加者によるバトルロイヤルが成立すること."""
    unit_a = MobileSuit(
        name="Unit A",
        max_hp=100,
        current_hp=100,
        armor=5,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(id="rifle_a", name="Rifle A", power=50, range=500, accuracy=90)
        ],
        side="PLAYER",
        team_id=None,
    )

    unit_b = MobileSuit(
        name="Unit B",
        max_hp=100,
        current_hp=100,
        armor=5,
        mobility=1.5,
        position=Vector3(x=200, y=0, z=0),
        weapons=[
            Weapon(id="rifle_b", name="Rifle B", power=50, range=500, accuracy=90)
        ],
        side="ENEMY",
        team_id=None,
    )

    unit_c = MobileSuit(
        name="Unit C",
        max_hp=100,
        current_hp=100,
        armor=5,
        mobility=1.5,
        position=Vector3(x=100, y=200, z=0),
        weapons=[
            Weapon(id="rifle_c", name="Rifle C", power=50, range=500, accuracy=90)
        ],
        side="ENEMY",
        team_id=None,
    )

    sim = BattleSimulator(unit_a, [unit_b, unit_c])

    # 各ユニットのteam_idはそれぞれ異なるはず
    assert len({unit_a.team_id, unit_b.team_id, unit_c.team_id}) == 3

    # バトルを実行
    max_turns = 100
    while not sim.is_finished and sim.turn < max_turns:
        sim.process_turn()

    # 戦闘が正常に終了すること
    assert sim.is_finished
    # 生存者のteam_idは1種類以下
    alive_teams = {u.team_id for u in sim.units if u.current_hp > 0}
    assert len(alive_teams) <= 1


def test_team_battle_finishes_correctly() -> None:
    """2チーム対抗戦が正しく終了すること."""
    # チームA: 2機
    team_a_1 = MobileSuit(
        name="Team A Leader",
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=2.0,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="beam_rifle",
                name="Beam Rifle",
                power=200,
                range=500,
                accuracy=100,
            )
        ],
        side="PLAYER",
        team_id="TEAM_A",
    )

    team_a_2 = MobileSuit(
        name="Team A Sub",
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=2.0,
        position=Vector3(x=50, y=0, z=0),
        weapons=[
            Weapon(
                id="beam_rifle",
                name="Beam Rifle",
                power=200,
                range=500,
                accuracy=100,
            )
        ],
        side="PLAYER",
        team_id="TEAM_A",
    )

    # チームB: 1機 (弱い)
    team_b_1 = MobileSuit(
        name="Team B Unit",
        max_hp=50,
        current_hp=50,
        armor=0,
        mobility=1.0,
        position=Vector3(x=200, y=0, z=0),
        weapons=[
            Weapon(
                id="zaku_mg",
                name="Zaku MG",
                power=10,
                range=400,
                accuracy=60,
            )
        ],
        side="ENEMY",
        team_id="TEAM_B",
    )

    sim = BattleSimulator(team_a_1, [team_a_2, team_b_1])

    max_turns = 50
    while not sim.is_finished and sim.turn < max_turns:
        sim.process_turn()

    # 戦闘が終了すること
    assert sim.is_finished
    # チームAが生存しているはず (圧倒的火力差)
    alive_teams = {u.team_id for u in sim.units if u.current_hp > 0}
    assert "TEAM_A" in alive_teams
    assert "TEAM_B" not in alive_teams


def test_detection_shared_within_team() -> None:
    """同チーム内で索敵情報が共有されること."""
    # チームA: 2機 (1機は敵の近く)
    scout = MobileSuit(
        name="Scout",
        max_hp=100,
        current_hp=100,
        armor=5,
        mobility=1.0,
        sensor_range=500.0,
        position=Vector3(x=0, y=0, z=0),
        weapons=[Weapon(id="w1", name="Weapon", power=10, range=400, accuracy=70)],
        side="PLAYER",
        team_id="TEAM_A",
    )

    rear_guard = MobileSuit(
        name="Rear Guard",
        max_hp=100,
        current_hp=100,
        armor=5,
        mobility=1.0,
        sensor_range=100.0,  # 短い索敵範囲
        position=Vector3(x=-500, y=0, z=0),  # 遠くにいる
        weapons=[Weapon(id="w2", name="Weapon", power=10, range=400, accuracy=70)],
        side="PLAYER",
        team_id="TEAM_A",
    )

    enemy = MobileSuit(
        name="Enemy",
        max_hp=80,
        current_hp=80,
        armor=5,
        mobility=1.0,
        position=Vector3(x=300, y=0, z=0),  # Scoutの索敵範囲内
        weapons=[Weapon(id="w3", name="Weapon", power=10, range=400, accuracy=70)],
        side="ENEMY",
        team_id="TEAM_B",
    )

    sim = BattleSimulator(scout, [rear_guard, enemy])
    sim.turn = 1
    sim._detection_phase()

    # Scoutが敵を発見 → TEAM_Aの索敵情報に共有される
    assert enemy.id in sim.team_detected_units["TEAM_A"]

    # Rear GuardもTEAM_Aなので同じ索敵情報を使える
    target = sim._select_target(rear_guard)
    assert target is not None
    assert target.name == "Enemy"

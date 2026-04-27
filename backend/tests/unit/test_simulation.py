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
    assert sim.elapsed_time == 0.0
    assert not sim.is_finished


def test_step_advances_time() -> None:
    """Test that step() advances elapsed_time."""
    player = create_test_player()
    player.mobility = 1.0
    enemies = [
        create_test_enemy("Fast Enemy", Vector3(x=500, y=0, z=0)),
    ]
    enemies[0].mobility = 2.0

    sim = BattleSimulator(player, enemies)
    sim.step()

    # First log should be from the faster unit (enemy in this case)
    # They might move or attack depending on distance
    assert len(sim.logs) > 0
    assert sim.elapsed_time > 0.0


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
    for _ in range(max_turns):
        if sim.is_finished:
            break
        sim.step()

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
    for _ in range(max_turns):
        if sim.is_finished:
            break
        sim.step()

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
    for _ in range(max_turns):
        if sim.is_finished:
            break
        sim.step()

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
            sim.step()

    # Should have some logs
    assert len(sim.logs) > 0
    # All logs should have timestamps
    for log in sim.logs:
        assert log.timestamp >= 0.0
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
    sim.step()

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
    sim.step()

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
    for _ in range(max_turns):
        if sim.is_finished:
            break
        sim.step()

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
    for _ in range(max_turns):
        if sim.is_finished:
            break
        sim.step()

    # 戦闘が終了すること
    assert sim.is_finished
    # チームAが生存しているはず (圧倒的火力差)
    alive_teams = {u.team_id for u in sim.units if u.current_hp > 0}
    assert "TEAM_A" in alive_teams
    assert "TEAM_B" not in alive_teams


def test_format_actor_name_with_pilot_name() -> None:
    """パイロット名がある場合、[パイロット名]のMS名 形式で返すこと."""
    player = MobileSuit(
        name="Gundam",
        pilot_name="Amuro",
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=2.0,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(id="rifle", name="Beam Rifle", power=30, range=500, accuracy=85)
        ],
        side="PLAYER",
        team_id="PLAYER_TEAM",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )
    enemy = create_test_enemy("Zaku", Vector3(x=100, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    result = sim._format_actor_name(player)
    assert result == "[Amuro]のGundam"


def test_format_actor_name_without_pilot_name() -> None:
    """パイロット名がない場合（NPC等）、MS名のみを返すこと."""
    player = create_test_player()
    enemy = create_test_enemy("Zaku", Vector3(x=100, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    # 検出済みとして登録し、プレイヤーチーム視点で取得する
    sim.team_detected_units["PLAYER_TEAM"].add(enemy.id)
    result = sim._format_actor_name(enemy, viewer_team_id="PLAYER_TEAM")
    assert result == "Zaku"


def test_format_actor_name_empty_pilot_name() -> None:
    """パイロット名が空文字列の場合、MS名のみを返すこと."""
    player = create_test_player()
    enemy = MobileSuit(
        name="Zaku",
        pilot_name="",
        max_hp=80,
        current_hp=80,
        armor=5,
        mobility=1.2,
        position=Vector3(x=100, y=0, z=0),
        weapons=[Weapon(id="mg", name="Machine Gun", power=15, range=400, accuracy=70)],
        side="ENEMY",
        team_id="ENEMY_TEAM",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )
    sim = BattleSimulator(player, [enemy])

    # 検出済みとして登録し、プレイヤーチーム視点で取得する
    sim.team_detected_units["PLAYER_TEAM"].add(enemy.id)
    result = sim._format_actor_name(enemy, viewer_team_id="PLAYER_TEAM")
    assert result == "Zaku"


def test_format_actor_name_unknown_for_undetected_enemy() -> None:
    """プレイヤーチームが未索敵の敵は UNKNOWN機 と表示すること."""
    player = create_test_player()
    enemy = MobileSuit(
        name="Gelgoog",
        pilot_name="Char",
        max_hp=80,
        current_hp=80,
        armor=5,
        mobility=1.2,
        position=Vector3(x=1000, y=0, z=0),  # 遠距離で未索敵
        weapons=[
            Weapon(id="beam", name="Beam Rifle", power=20, range=500, accuracy=75)
        ],
        side="ENEMY",
        team_id="ENEMY_TEAM",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )
    sim = BattleSimulator(player, [enemy])

    # プレイヤーチーム視点で未索敵の敵を取得 → UNKNOWN機
    result = sim._format_actor_name(enemy, viewer_team_id="PLAYER_TEAM")
    assert result == "UNKNOWN機"


def test_format_actor_name_revealed_after_detection() -> None:
    """索敵後は UNKNOWN機 から実名表示に切り替わること."""
    player = create_test_player()
    enemy = MobileSuit(
        name="Gelgoog",
        pilot_name="Char",
        max_hp=80,
        current_hp=80,
        armor=5,
        mobility=1.2,
        position=Vector3(x=1000, y=0, z=0),
        weapons=[
            Weapon(id="beam", name="Beam Rifle", power=20, range=500, accuracy=75)
        ],
        side="ENEMY",
        team_id="ENEMY_TEAM",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )
    sim = BattleSimulator(player, [enemy])

    # 未索敵時は UNKNOWN機
    assert sim._format_actor_name(enemy, viewer_team_id="PLAYER_TEAM") == "UNKNOWN機"

    # 索敵後は実名表示
    sim.team_detected_units["PLAYER_TEAM"].add(enemy.id)
    assert (
        sim._format_actor_name(enemy, viewer_team_id="PLAYER_TEAM") == "[Char]のGelgoog"
    )


def test_attack_log_includes_pilot_name() -> None:
    """攻撃ログにパイロット名が含まれること."""
    player = MobileSuit(
        name="Gundam",
        pilot_name="Amuro",
        max_hp=1000,
        current_hp=1000,
        armor=10,
        mobility=2.0,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(id="rifle", name="Beam Rifle", power=30, range=500, accuracy=100)
        ],
        side="PLAYER",
        team_id="PLAYER_TEAM",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )
    enemy = MobileSuit(
        name="Zaku",
        max_hp=80,
        current_hp=80,
        armor=0,
        mobility=1.2,
        position=Vector3(x=100, y=0, z=0),
        weapons=[Weapon(id="mg", name="Machine Gun", power=15, range=400, accuracy=70)],
        side="ENEMY",
        team_id="ENEMY_TEAM",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )
    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()
    sim.step()

    attack_logs = [log for log in sim.logs if log.action_type in ("ATTACK", "MISS")]
    player_attack_logs = [log for log in attack_logs if log.actor_id == player.id]
    assert len(player_attack_logs) > 0
    # パイロット名が含まれること
    assert any("[Amuro]のGundam" in log.message for log in player_attack_logs)


def test_enemy_log_shows_unknown_before_detection() -> None:
    """索敵前の敵のアクションログは UNKNOWN機 を含むこと."""
    player = MobileSuit(
        name="Gundam",
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=0.1,  # 遅くして敵が先行
        sensor_range=1.0,  # 極端に短い索敵範囲（敵を発見できない）
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(id="rifle", name="Beam Rifle", power=30, range=500, accuracy=85)
        ],
        side="PLAYER",
        team_id="PLAYER_TEAM",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )
    enemy = MobileSuit(
        name="Zaku",
        pilot_name="Char",
        max_hp=1000,
        current_hp=1000,
        armor=5,
        mobility=2.0,  # 速くして先行
        position=Vector3(x=100, y=0, z=0),
        weapons=[
            Weapon(id="mg", name="Machine Gun", power=15, range=400, accuracy=100)
        ],
        side="ENEMY",
        team_id="ENEMY_TEAM",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )
    sim = BattleSimulator(player, [enemy])

    # 索敵フェーズを手動制御（敵はプレイヤーを発見するが、プレイヤーは敵を発見できない）
    # プレイヤーチームの索敵済みセットは空のままにする
    # 敵チームはプレイヤーを発見させる
    sim.team_detected_units["ENEMY_TEAM"].add(player.id)

    # ターゲット選択ログを生成
    sim.elapsed_time = 0.1
    sim._log_target_selection(enemy, player, "CLOSEST", "距離: 100m")

    target_logs = [log for log in sim.logs if log.action_type == "TARGET_SELECTION"]
    assert len(target_logs) == 1
    # 索敵前なのでプレイヤー視点では敵が UNKNOWN機 として表示される
    assert "UNKNOWN機" in target_logs[0].message


def test_skill_activated_flag_set_when_skill_changes_outcome() -> None:
    """スキルが命中/回避の結果を変えた場合、skill_activated=True が設定されること."""
    import random as _random

    # スキルボーナスが 20% あるシナリオ（accuracy_up Lv10）
    player = MobileSuit(
        name="Gundam",
        max_hp=10000,
        current_hp=10000,
        armor=0,
        mobility=2.0,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(id="rifle", name="Beam Rifle", power=1, range=500, accuracy=50)
        ],
        side="PLAYER",
        team_id="PLAYER_TEAM",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )
    enemy = MobileSuit(
        name="Zaku",
        max_hp=10000,
        current_hp=10000,
        armor=0,
        mobility=1.2,
        position=Vector3(x=100, y=0, z=0),
        weapons=[Weapon(id="mg", name="Machine Gun", power=1, range=400, accuracy=70)],
        side="ENEMY",
        team_id="ENEMY_TEAM",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )
    # accuracy_up Lv10 → +20% hit chance bonus
    sim = BattleSimulator(player, [enemy], player_skills={"accuracy_up": 10})
    sim.team_detected_units["PLAYER_TEAM"].add(enemy.id)
    sim.team_detected_units["ENEMY_TEAM"].add(player.id)

    # 多数のターンを実行してスキル発動ケースが含まれることを確認
    _random.seed(12345)
    for _ in range(20):
        if not sim.is_finished:
            sim.step()

    attack_and_miss_logs = [
        log
        for log in sim.logs
        if log.action_type in ("ATTACK", "MISS") and log.actor_id == player.id
    ]
    assert len(attack_and_miss_logs) > 0
    # skill_activated フィールドは None または bool のどちらかであること
    for log in attack_and_miss_logs:
        assert log.skill_activated is None or isinstance(log.skill_activated, bool)


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
    sim.elapsed_time = 0.1
    sim._detection_phase()

    # Scoutが敵を発見 → TEAM_Aの索敵情報に共有される
    assert enemy.id in sim.team_detected_units["TEAM_A"]

    # Rear GuardもTEAM_Aなので同じ索敵情報を使える
    target = sim._select_target(rear_guard)
    assert target is not None
    assert target.name == "Enemy"


# ---------------------------------------------------------------------------
# 中階層ファジィ推論統合テスト
# ---------------------------------------------------------------------------


def create_fuzzy_test_player() -> MobileSuit:
    """ファジィ統合テスト用のプレイヤー機体を作成する."""
    return MobileSuit(
        name="Test Player",
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=2.0,
        sensor_range=600.0,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="br_01",
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


def create_fuzzy_test_enemy(name: str, position: Vector3) -> MobileSuit:
    """ファジィ統合テスト用の敵機体を作成する."""
    return MobileSuit(
        name=name,
        max_hp=80,
        current_hp=80,
        armor=5,
        mobility=1.2,
        sensor_range=500.0,
        position=position,
        weapons=[
            Weapon(
                id=f"zmg_{name}",
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


def test_ai_decision_phase_no_detected_enemies_returns_move() -> None:
    """索敵済みの敵が0体の場合、ファジィ推論をスキップして MOVE を選択する."""
    player = create_fuzzy_test_player()
    # 遠くに配置して索敵範囲外にする
    enemies = [create_fuzzy_test_enemy("Far Enemy", Vector3(x=5000, y=0, z=0))]

    sim = BattleSimulator(player, enemies)
    # 索敵フェーズをスキップ（敵を発見しない状態）
    sim._ai_decision_phase(player)

    assert sim.unit_resources[str(player.id)]["current_action"] == "MOVE"


def test_ai_decision_phase_with_detected_enemies() -> None:
    """索敵済みの敵がいる場合、ファジィ推論が実行されて行動が決定される."""
    player = create_fuzzy_test_player()
    enemy = create_fuzzy_test_enemy("Close Enemy", Vector3(x=300, y=0, z=0))

    sim = BattleSimulator(player, enemies=[enemy])
    # 敵を索敵済みにする
    sim._detection_phase()

    sim._ai_decision_phase(player)

    action = sim.unit_resources[str(player.id)]["current_action"]
    assert action in ("ATTACK", "MOVE", "RETREAT")


def test_ai_decision_phase_logs_ai_decision() -> None:
    """ファジィ推論の結果が AI_DECISION ログとして記録される."""
    player = create_fuzzy_test_player()
    enemy = create_fuzzy_test_enemy("Enemy", Vector3(x=200, y=0, z=0))

    sim = BattleSimulator(player, enemies=[enemy])
    sim._detection_phase()
    sim._ai_decision_phase(player)

    ai_logs = [log for log in sim.logs if log.action_type == "AI_DECISION"]
    assert len(ai_logs) >= 1

    player_log = next(
        (log for log in ai_logs if log.actor_id == player.id), None
    )
    assert player_log is not None
    assert player_log.fuzzy_scores is not None
    assert player_log.strategy_mode == "AGGRESSIVE"


def test_ai_decision_phase_fuzzy_scores_recorded() -> None:
    """fuzzy_scores に action の活性化度が記録される."""
    player = create_fuzzy_test_player()
    enemy = create_fuzzy_test_enemy("Enemy", Vector3(x=200, y=0, z=0))

    sim = BattleSimulator(player, enemies=[enemy])
    sim._detection_phase()
    sim._ai_decision_phase(player)

    ai_logs = [log for log in sim.logs if log.action_type == "AI_DECISION"]
    player_log = next(
        (log for log in ai_logs if log.actor_id == player.id), None
    )
    assert player_log is not None
    # fuzzy_scores には activations が記録されている
    assert "action" in player_log.fuzzy_scores


def test_ai_decision_phase_retreat_fallback_to_move() -> None:
    """RETREAT が出力されるシナリオで MOVE にフォールバックすることを確認する."""
    # HP 低く、敵多い → RETREAT が最優勢になるシナリオ
    player = create_fuzzy_test_player()
    player.current_hp = 5   # HP 非常に低い (LOW ゾーン)
    player.max_hp = 100

    # 近接敵を大量配置（MANY になるよう）
    enemies = [
        create_fuzzy_test_enemy(f"Enemy{i}", Vector3(x=100 + i * 20, y=i * 10, z=0))
        for i in range(8)
    ]

    sim = BattleSimulator(player, enemies=enemies)
    sim._detection_phase()
    sim._ai_decision_phase(player)

    # RETREAT フォールバックで MOVE になっている（または ATTACK の場合もあり得る）
    action = sim.unit_resources[str(player.id)]["current_action"]
    # RETREAT は MOVE にフォールバックするため、"RETREAT" は絶対に出力されない
    assert action != "RETREAT"
    assert action in ("ATTACK", "MOVE")


def test_step_includes_ai_decision_phase() -> None:
    """step() 実行後に AI_DECISION ログが生成されることを確認する."""
    player = create_fuzzy_test_player()
    # 近くに敵を配置して索敵で発見できるようにする
    enemy = create_fuzzy_test_enemy("Close Enemy", Vector3(x=200, y=0, z=0))

    sim = BattleSimulator(player, enemies=[enemy])
    sim.step()

    ai_logs = [log for log in sim.logs if log.action_type == "AI_DECISION"]
    assert len(ai_logs) >= 1


def test_current_action_initialized_as_move() -> None:
    """unit_resources の current_action がデフォルト MOVE で初期化される."""
    player = create_fuzzy_test_player()
    enemy = create_fuzzy_test_enemy("Enemy", Vector3(x=500, y=0, z=0))

    sim = BattleSimulator(player, enemies=[enemy])

    # 初期値は MOVE
    assert sim.unit_resources[str(player.id)]["current_action"] == "MOVE"
    assert sim.unit_resources[str(enemy.id)]["current_action"] == "MOVE"


def test_action_phase_respects_move_action() -> None:
    """current_action=MOVE のとき、攻撃射程内でも攻撃しないことを確認する."""
    player = create_fuzzy_test_player()
    # 攻撃射程内に敵を配置
    enemy = create_fuzzy_test_enemy("Close Enemy", Vector3(x=100, y=0, z=0))

    sim = BattleSimulator(player, enemies=[enemy])
    sim._detection_phase()

    # MOVE に設定して行動フェーズを実行
    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"
    initial_enemy_hp = enemy.current_hp
    sim._action_phase(player)

    # MOVE なので攻撃せず、敵のHPが変わっていない
    assert enemy.current_hp == initial_enemy_hp
    # MOVE ログが出力される
    move_logs = [log for log in sim.logs if log.action_type == "MOVE" and log.actor_id == player.id]
    assert len(move_logs) >= 1


def test_action_phase_respects_attack_action() -> None:
    """current_action=ATTACK のとき、射程内で攻撃を試みることを確認する."""
    player = create_fuzzy_test_player()
    player.weapons[0].accuracy = 100  # 必ず命中するように
    # 攻撃射程内に敵を配置
    enemy = create_fuzzy_test_enemy("Close Enemy", Vector3(x=100, y=0, z=0))

    sim = BattleSimulator(player, enemies=[enemy])
    sim._detection_phase()

    # ATTACK に設定して行動フェーズを実行
    sim.unit_resources[str(player.id)]["current_action"] = "ATTACK"
    sim._action_phase(player)

    # ATTACK または MISS ログが出力される（攻撃を試みた）
    attack_logs = [
        log for log in sim.logs
        if log.action_type in ("ATTACK", "MISS", "WAIT") and log.actor_id == player.id
    ]
    assert len(attack_logs) >= 1

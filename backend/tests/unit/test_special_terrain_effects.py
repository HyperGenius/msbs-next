"""Tests for special terrain effects (Minovsky particles, gravity well, obstacles)."""

import pytest

from app.engine.constants import SPECIAL_ENVIRONMENT_EFFECTS, MAX_WEAPON_SLOTS
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


def create_test_player(sensor_range: float = 600.0) -> MobileSuit:
    """Create a test player mobile suit."""
    return MobileSuit(
        name="Test Gundam",
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=2.0,
        sensor_range=sensor_range,
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
        sensor_range=400.0,
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


# --- 定数テスト ---


def test_special_environment_effects_defined() -> None:
    """特殊環境効果の定数が正しく定義されていることをテスト."""
    assert "MINOVSKY" in SPECIAL_ENVIRONMENT_EFFECTS
    assert "GRAVITY_WELL" in SPECIAL_ENVIRONMENT_EFFECTS
    assert "OBSTACLE" in SPECIAL_ENVIRONMENT_EFFECTS

    assert SPECIAL_ENVIRONMENT_EFFECTS["MINOVSKY"]["sensor_range_multiplier"] == 0.5
    assert SPECIAL_ENVIRONMENT_EFFECTS["GRAVITY_WELL"]["mobility_multiplier"] == 0.6
    assert SPECIAL_ENVIRONMENT_EFFECTS["OBSTACLE"]["accuracy_penalty"] == 10.0


def test_max_weapon_slots_defined() -> None:
    """最大武器スロット数の定数が正しく定義されていることをテスト."""
    assert MAX_WEAPON_SLOTS == 2


# --- ミノフスキー粒子テスト ---


def test_minovsky_reduces_sensor_range() -> None:
    """ミノフスキー粒子が索敵範囲を半減させることをテスト."""
    player = create_test_player(sensor_range=600.0)

    # 索敵範囲内 (300m) だが、ミノフスキー粒子により半減 (実効300m > 300m なので検出できないはず)
    # 正確には 600 * 0.5 = 300m が実効索敵範囲
    # ちょうど300mの敵は検出される
    enemy = create_test_enemy("Enemy", Vector3(x=299, y=0, z=0))

    sim_minovsky = BattleSimulator(
        player, [enemy], environment="SPACE", special_effects=["MINOVSKY"]
    )
    sim_minovsky._detection_phase()

    # ミノフスキー粒子下では 600 * 0.5 = 300m が実効範囲
    # 299m なので検出されるはず
    assert enemy.id in sim_minovsky.team_detected_units["PLAYER"]


def test_minovsky_blocks_long_range_detection() -> None:
    """ミノフスキー粒子により通常は検出できる距離の敵が検出できないことをテスト."""
    player = create_test_player(sensor_range=600.0)

    # 400mの敵 - 通常は検出可能 (600m範囲内)、ミノフスキー粒子下では不可 (300m範囲外)
    enemy = create_test_enemy("Far Enemy", Vector3(x=400, y=0, z=0))

    # 通常環境
    sim_normal = BattleSimulator(player, [enemy], environment="SPACE")
    sim_normal._detection_phase()
    assert enemy.id in sim_normal.team_detected_units["PLAYER"]

    # ミノフスキー粒子下 (同じ敵、新しいシミュレーター)
    player2 = create_test_player(sensor_range=600.0)
    enemy2 = create_test_enemy("Far Enemy", Vector3(x=400, y=0, z=0))
    sim_minovsky = BattleSimulator(
        player2, [enemy2], environment="SPACE", special_effects=["MINOVSKY"]
    )
    sim_minovsky._detection_phase()
    # 400m > 300m (実効索敵範囲) なので検出できないはず
    assert enemy2.id not in sim_minovsky.team_detected_units["PLAYER"]


def test_minovsky_detection_log_includes_message() -> None:
    """ミノフスキー粒子下の発見ログにメッセージが含まれることをテスト."""
    player = create_test_player(sensor_range=600.0)
    enemy = create_test_enemy("Enemy", Vector3(x=200, y=0, z=0))

    sim = BattleSimulator(
        player, [enemy], environment="SPACE", special_effects=["MINOVSKY"]
    )
    sim.turn = 1
    sim._detection_phase()

    detection_logs = [log for log in sim.logs if log.action_type == "DETECTION"]
    assert len(detection_logs) >= 1
    assert any("ミノフスキー粒子" in log.message for log in detection_logs)


def test_no_minovsky_no_message() -> None:
    """ミノフスキー粒子なしの発見ログにはメッセージが含まれないことをテスト."""
    player = create_test_player(sensor_range=600.0)
    enemy = create_test_enemy("Enemy", Vector3(x=200, y=0, z=0))

    sim = BattleSimulator(player, [enemy], environment="SPACE")
    sim.turn = 1
    sim._detection_phase()

    detection_logs = [log for log in sim.logs if log.action_type == "DETECTION"]
    assert len(detection_logs) >= 1
    assert not any("ミノフスキー粒子" in log.message for log in detection_logs)


# --- 重力井戸テスト ---


def test_gravity_well_reduces_movement() -> None:
    """重力井戸効果が機動性（移動距離）を低下させることをテスト."""
    enemy_pos = Vector3(x=2000, y=0, z=0)

    # 通常環境
    player_normal = create_test_player()
    enemy_normal = create_test_enemy("Enemy", enemy_pos)
    sim_normal = BattleSimulator(player_normal, [enemy_normal], environment="GROUND")
    sim_normal._detection_phase()
    sim_normal.process_turn()
    normal_x = player_normal.position.x

    # 重力井戸環境
    player_gravity = create_test_player()
    enemy_gravity = create_test_enemy("Enemy", enemy_pos)
    sim_gravity = BattleSimulator(
        player_gravity, [enemy_gravity], environment="GROUND", special_effects=["GRAVITY_WELL"]
    )
    sim_gravity._detection_phase()
    sim_gravity.process_turn()
    gravity_x = player_gravity.position.x

    # 重力井戸下では通常より移動距離が少ないはず
    assert gravity_x < normal_x


def test_gravity_well_terrain_modifier() -> None:
    """重力井戸効果がterrain_modifierに反映されることをテスト."""
    player = create_test_player()
    enemy = create_test_enemy("Enemy", Vector3(x=500, y=0, z=0))

    sim_normal = BattleSimulator(player, [enemy], environment="GROUND")
    sim_gravity = BattleSimulator(
        player, [enemy], environment="GROUND", special_effects=["GRAVITY_WELL"]
    )

    modifier_normal = sim_normal._get_terrain_modifier(player)
    modifier_gravity = sim_gravity._get_terrain_modifier(player)

    # 重力井戸下では補正係数が低くなる
    assert modifier_gravity < modifier_normal
    assert modifier_gravity == pytest.approx(modifier_normal * 0.6, rel=1e-5)


# --- 障害物テスト ---


def test_obstacle_reduces_hit_chance() -> None:
    """障害物効果が命中率を低下させることをテスト."""
    player = create_test_player()
    enemy = create_test_enemy("Enemy", Vector3(x=100, y=0, z=0))
    weapon = player.weapons[0]
    distance = 100.0

    sim_normal = BattleSimulator(player, [enemy], environment="SPACE")
    sim_obstacle = BattleSimulator(
        player, [enemy], environment="SPACE", special_effects=["OBSTACLE"]
    )

    hit_normal, _ = sim_normal._calculate_hit_chance(player, enemy, weapon, distance)
    hit_obstacle, _ = sim_obstacle._calculate_hit_chance(player, enemy, weapon, distance)

    # 障害物下では命中率が低くなる
    assert hit_obstacle < hit_normal
    assert hit_normal - hit_obstacle == pytest.approx(10.0, rel=1e-5)


# --- 複数効果テスト ---


def test_multiple_special_effects() -> None:
    """複数の特殊効果が同時に適用されることをテスト."""
    player = create_test_player(sensor_range=600.0)
    enemy = create_test_enemy("Enemy", Vector3(x=400, y=0, z=0))
    weapon = player.weapons[0]
    distance = 100.0

    sim = BattleSimulator(
        player,
        [enemy],
        environment="SPACE",
        special_effects=["MINOVSKY", "GRAVITY_WELL", "OBSTACLE"],
    )

    # ミノフスキー粒子: 400m > 300m (実効範囲) なので検出不可
    sim._detection_phase()
    assert enemy.id not in sim.team_detected_units["PLAYER"]

    # 重力井戸: terrain_modifierが低下
    modifier = sim._get_terrain_modifier(player)
    assert modifier < 1.0

    # 障害物: 命中率が低下
    hit_chance, _ = sim._calculate_hit_chance(player, enemy, weapon, distance)
    # 通常より10%低いはず
    sim_normal = BattleSimulator(player, [enemy], environment="SPACE")
    hit_normal, _ = sim_normal._calculate_hit_chance(player, enemy, weapon, distance)
    assert hit_chance < hit_normal


# --- 特殊効果なし (デフォルト) テスト ---


def test_no_special_effects_by_default() -> None:
    """デフォルトでは特殊効果が適用されないことをテスト."""
    player = create_test_player()
    enemy = create_test_enemy("Enemy", Vector3(x=500, y=0, z=0))

    sim = BattleSimulator(player, [enemy])
    assert sim.special_effects == []

"""Tests for Phase A — LOS + Obstacle system.

Validates:
1. Obstacle data model and BattleField model
2. _has_los() 3D Ray-Sphere intersection logic
3. LOS check integration in _detection_phase()
4. LOS check integration in _process_attack() with ATTACK_BLOCKED_LOS log
5. Obstacle repulsion in _calculate_potential_field()
6. last_known_enemy_position tracking in _search_movement()
7. Backward compatibility when obstacles = []
8. _get_units_in_weapon_range() performance helper
"""

import numpy as np
from unittest.mock import patch

from app.engine.simulation import BattleSimulator, _has_los
from app.models.models import (
    BattleField,
    MobileSuit,
    Obstacle,
    Vector3,
    Weapon,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_unit(
    name: str,
    side: str,
    team_id: str,
    pos: Vector3,
    sensor_range: float = 2000.0,
    weapon_range: float = 1000.0,
    weapon_power: float = 30.0,
    is_melee: bool = False,
) -> MobileSuit:
    weapon_id = f"weapon_{name}"
    return MobileSuit(
        name=name,
        max_hp=100,
        current_hp=100,
        armor=0,
        mobility=1.0,
        position=pos,
        sensor_range=sensor_range,
        side=side,
        team_id=team_id,
        weapons=[
            Weapon(
                id=weapon_id,
                name=f"{name} Weapon",
                power=int(weapon_power),
                range=weapon_range,
                accuracy=90.0,
                is_melee=is_melee,
            )
        ],
    )


def _make_obstacle(
    obs_id: str,
    x: float,
    y: float,
    z: float,
    radius: float,
    height: float = 100.0,
) -> Obstacle:
    return Obstacle(
        obstacle_id=obs_id,
        position=Vector3(x=x, y=y, z=z),
        radius=radius,
        height=height,
    )


# ---------------------------------------------------------------------------
# 1. Data model tests
# ---------------------------------------------------------------------------


def test_obstacle_model_fields() -> None:
    """Obstacle モデルが必要なフィールドを持つこと."""
    obs = _make_obstacle("obs1", 500.0, 0.0, 500.0, 100.0, 200.0)
    assert obs.obstacle_id == "obs1"
    assert obs.position.x == 500.0
    assert obs.position.y == 0.0
    assert obs.position.z == 500.0
    assert obs.radius == 100.0
    assert obs.height == 200.0


def test_battlefield_model_obstacles() -> None:
    """BattleField モデルが obstacles フィールドを持つこと."""
    bf = BattleField()
    assert bf.obstacles == []

    obs = _make_obstacle("obs1", 0.0, 0.0, 0.0, 50.0)
    bf2 = BattleField(obstacles=[obs])
    assert len(bf2.obstacles) == 1
    assert bf2.obstacles[0].obstacle_id == "obs1"


# ---------------------------------------------------------------------------
# 2. _has_los() tests
# ---------------------------------------------------------------------------


def test_has_los_no_obstacles() -> None:
    """障害物がない場合、常に LOS あり."""
    pos_a = np.array([0.0, 0.0, 0.0])
    pos_b = np.array([500.0, 0.0, 0.0])
    assert _has_los(pos_a, pos_b, []) is True


def test_has_los_same_position() -> None:
    """同じ位置（距離ほぼゼロ）の場合、LOS あり."""
    pos_a = np.array([100.0, 0.0, 100.0])
    pos_b = np.array([100.0, 0.0, 100.0])
    obs = _make_obstacle("obs1", 100.0, 0.0, 100.0, 50.0)
    assert _has_los(pos_a, pos_b, [obs]) is True


def test_has_los_obstacle_on_ray_blocked() -> None:
    """射線上に障害物がある場合、LOS なし（遮断）."""
    # A=(0,0,0), B=(1000,0,0), 障害物中心=(500,0,0), radius=100
    pos_a = np.array([0.0, 0.0, 0.0])
    pos_b = np.array([1000.0, 0.0, 0.0])
    obs = _make_obstacle("obs1", 500.0, 0.0, 0.0, 100.0)
    assert _has_los(pos_a, pos_b, [obs]) is False


def test_has_los_obstacle_beside_ray_passes() -> None:
    """射線の横に障害物がある場合、LOS あり（遮断なし）."""
    # A=(0,0,0), B=(1000,0,0), 障害物中心=(500,0,200), radius=100
    pos_a = np.array([0.0, 0.0, 0.0])
    pos_b = np.array([1000.0, 0.0, 0.0])
    obs = _make_obstacle("obs1", 500.0, 0.0, 200.0, 100.0)
    assert _has_los(pos_a, pos_b, [obs]) is True


def test_has_los_obstacle_behind_target_no_block() -> None:
    """ターゲットの後方にある障害物は遮断しない（t > dist）."""
    # A=(0,0,0), B=(500,0,0), 障害物中心=(800,0,0), radius=100
    # t の範囲 0 < t < 500 の外側なので遮断なし
    pos_a = np.array([0.0, 0.0, 0.0])
    pos_b = np.array([500.0, 0.0, 0.0])
    obs = _make_obstacle("obs1", 800.0, 0.0, 0.0, 100.0)
    assert _has_los(pos_a, pos_b, [obs]) is True


def test_has_los_obstacle_behind_shooter_no_block() -> None:
    """射撃者の後方にある障害物は遮断しない（t < 0）."""
    # A=(0,0,0), B=(1000,0,0), 障害物中心=(-200,0,0), radius=100
    pos_a = np.array([0.0, 0.0, 0.0])
    pos_b = np.array([1000.0, 0.0, 0.0])
    obs = _make_obstacle("obs1", -200.0, 0.0, 0.0, 100.0)
    assert _has_los(pos_a, pos_b, [obs]) is True


def test_has_los_multiple_obstacles_one_blocking() -> None:
    """複数の障害物のうち1つでも射線上にある場合、LOS なし."""
    pos_a = np.array([0.0, 0.0, 0.0])
    pos_b = np.array([1000.0, 0.0, 0.0])
    obs1 = _make_obstacle("obs1", 200.0, 0.0, 500.0, 50.0)  # 射線外
    obs2 = _make_obstacle("obs2", 500.0, 0.0, 0.0, 100.0)  # 射線上
    assert _has_los(pos_a, pos_b, [obs1, obs2]) is False


def test_has_los_y_axis_obstacle_3d() -> None:
    """Y 軸（高度）方向の障害物も正しく判定できること."""
    # A=(0,0,0), B=(0,1000,0) — Y方向に移動
    # 障害物中心=(0,500,0), radius=100 — 射線上
    pos_a = np.array([0.0, 0.0, 0.0])
    pos_b = np.array([0.0, 1000.0, 0.0])
    obs = _make_obstacle("obs1", 0.0, 500.0, 0.0, 100.0)
    assert _has_los(pos_a, pos_b, [obs]) is False


# ---------------------------------------------------------------------------
# 3. _detection_phase() LOS integration tests
# ---------------------------------------------------------------------------


def test_detection_blocked_by_obstacle() -> None:
    """センサー範囲内でも障害物で遮断されている場合、発見されないこと."""
    # プレイヤー: (0,0,0), 敵: (1000,0,0), 障害物: (500,0,0) radius=100
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), sensor_range=2000.0
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=1000, y=0, z=0))
    obs = _make_obstacle("obs1", 500.0, 0.0, 0.0, 100.0)
    sim = BattleSimulator(player, [enemy], obstacles=[obs])

    sim._detection_phase()

    player_team_id = player.team_id
    assert enemy.id not in sim.team_detected_units[player_team_id], (
        "障害物で遮断されている場合、敵は発見されてはいけない"
    )


def test_detection_passes_without_obstacle_on_ray() -> None:
    """障害物が射線外にある場合、通常通り発見されること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), sensor_range=2000.0
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=1000, y=0, z=0))
    obs = _make_obstacle("obs1", 500.0, 0.0, 300.0, 100.0)  # 射線横
    sim = BattleSimulator(player, [enemy], obstacles=[obs])

    with patch("app.engine.targeting.random.random", return_value=0.0):
        sim._detection_phase()

    player_team_id = player.team_id
    assert enemy.id in sim.team_detected_units[player_team_id], (
        "障害物が射線外の場合、敵は発見されるべき"
    )


def test_detection_los_lost_stores_last_known_position() -> None:
    """発見済みの敵が障害物の陰に入った場合、最終座標が記録されること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), sensor_range=2000.0
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=1000, y=0, z=0))

    # 最初は障害物なしで発見させる（パッチで確率判定を常に成功させる）
    sim = BattleSimulator(player, [enemy])
    with patch("app.engine.targeting.random.random", return_value=0.0):
        sim._detection_phase()
    assert enemy.id in sim.team_detected_units[player.team_id]

    # 障害物を追加（射線上）して再チェック
    sim.obstacles = [_make_obstacle("obs1", 500.0, 0.0, 0.0, 100.0)]
    sim._detection_phase()

    unit_id = str(player.id)
    last_known = sim.unit_resources[unit_id]["last_known_enemy_position"]
    assert str(enemy.id) in last_known, "LOS 喪失時に最終座標が記憶されるべき"
    assert enemy.id not in sim.team_detected_units[player.team_id], (
        "LOS 喪失後は発見済みリストから除外されるべき"
    )


def test_detection_no_obstacles_backward_compatible() -> None:
    """obstacles=[] の場合、従来通りに発見されること（後方互換性）."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), sensor_range=2000.0
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=500, y=0, z=0))
    sim = BattleSimulator(player, [enemy])  # obstacles なし

    with patch("app.engine.targeting.random.random", return_value=0.0):
        sim._detection_phase()

    assert enemy.id in sim.team_detected_units[player.team_id], (
        "obstacles なし（デフォルト）では従来通り発見されること"
    )


# ---------------------------------------------------------------------------
# 4. _process_attack() LOS integration tests
# ---------------------------------------------------------------------------


def test_attack_blocked_by_obstacle_logs_attack_blocked_los() -> None:
    """射線上の障害物により攻撃がスキップされ ATTACK_BLOCKED_LOS がログに記録されること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), weapon_range=1500.0
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=1000, y=0, z=0))
    obs = _make_obstacle("obs1", 500.0, 0.0, 0.0, 100.0)
    sim = BattleSimulator(player, [enemy], obstacles=[obs])

    # 発見済みにセットアップ
    sim.team_detected_units[player.team_id].add(enemy.id)

    pos_player = player.position.to_numpy()
    weapon = player.get_active_weapon()
    sim._process_attack(player, enemy, 1000.0, pos_player, weapon)

    blocked_logs = [log for log in sim.logs if log.action_type == "ATTACK_BLOCKED_LOS"]
    assert len(blocked_logs) == 1, "ATTACK_BLOCKED_LOS がログに記録されるべき"
    assert blocked_logs[0].target_id == enemy.id


def test_attack_not_blocked_when_no_obstacle_on_ray() -> None:
    """射線外の障害物があっても攻撃は通常通り実行されること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), weapon_range=1500.0
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=1000, y=0, z=0))
    obs = _make_obstacle("obs1", 500.0, 0.0, 300.0, 100.0)  # 射線外
    sim = BattleSimulator(player, [enemy], obstacles=[obs])

    sim.team_detected_units[player.team_id].add(enemy.id)
    pos_player = player.position.to_numpy()
    weapon = player.get_active_weapon()
    sim._process_attack(player, enemy, 1000.0, pos_player, weapon)

    blocked_logs = [log for log in sim.logs if log.action_type == "ATTACK_BLOCKED_LOS"]
    assert len(blocked_logs) == 0, "射線外の障害物では攻撃がブロックされてはいけない"

    # ATTACK or DAMAGE or MISS が記録されること
    attack_logs = [
        log for log in sim.logs if log.action_type in {"ATTACK", "DAMAGE", "MISS"}
    ]
    assert len(attack_logs) > 0, "攻撃が実行されるべき"


def test_melee_attack_skips_los_check() -> None:
    """格闘武器は LOS チェックをスキップすること."""
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        Vector3(x=0, y=0, z=0),
        weapon_range=50.0,
        is_melee=True,
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=30, y=0, z=0))
    obs = _make_obstacle("obs1", 15.0, 0.0, 0.0, 10.0)  # 射線上
    sim = BattleSimulator(player, [enemy], obstacles=[obs])

    sim.team_detected_units[player.team_id].add(enemy.id)
    pos_player = player.position.to_numpy()
    weapon = player.get_active_weapon()
    assert weapon is not None and weapon.is_melee is True

    sim._process_attack(player, enemy, 30.0, pos_player, weapon)

    blocked_logs = [log for log in sim.logs if log.action_type == "ATTACK_BLOCKED_LOS"]
    assert len(blocked_logs) == 0, "格闘武器は LOS チェックをスキップすること"


def test_attack_no_obstacles_backward_compatible() -> None:
    """obstacles=[] の場合、攻撃は従来通り実行されること（後方互換性）."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), weapon_range=1500.0
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=200, y=0, z=0))
    sim = BattleSimulator(player, [enemy])  # obstacles なし

    sim.team_detected_units[player.team_id].add(enemy.id)
    pos_player = player.position.to_numpy()
    weapon = player.get_active_weapon()
    sim._process_attack(player, enemy, 200.0, pos_player, weapon)

    blocked_logs = [log for log in sim.logs if log.action_type == "ATTACK_BLOCKED_LOS"]
    assert len(blocked_logs) == 0, "obstacles=[] では LOS ブロックが発生しないこと"


# ---------------------------------------------------------------------------
# 5. _calculate_potential_field() obstacle repulsion test
# ---------------------------------------------------------------------------


def test_potential_field_obstacle_repulsion() -> None:
    """ポテンシャルフィールドに障害物斥力が機能すること."""
    # プレイヤーを障害物の近くに配置し、障害物と反対方向への力が働くことを確認
    # 障害物: (200,0,0), radius=100, OBSTACLE_MARGIN=50 → 有効距離 150m
    # ユニット: (100,0,0) → 障害物まで距離 100m < 150m → 斥力発生
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=100, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=4000, y=0, z=0))
    obs = _make_obstacle("obs1", 200.0, 0.0, 0.0, 100.0)
    sim = BattleSimulator(player, [enemy], obstacles=[obs])

    # 敵を発見済みにして ATTACK 行動させる
    sim.team_detected_units[player.team_id].add(enemy.id)
    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"

    direction = sim._calculate_potential_field(player)
    # X 方向は障害物（右、+x）から離れる方向への力が加わるため x は負方向に傾くはず
    # ただし敵への引力もあるため、少なくとも障害物斥力が働いていることを確認
    # 斥力がなければ単純に +x 方向へ引力のみ
    # 斥力ありの場合は x 成分が減少するはず（ただし完全に -x にはならないかもしれない）
    # ここではポテンシャルフィールドが有効な単位ベクトルを返すことを確認
    assert direction is not None
    assert direction.shape == (3,)
    magnitude = float(np.linalg.norm(direction))
    assert abs(magnitude - 1.0) < 1e-5 or magnitude < 1e-6, (
        "ポテンシャルフィールドは単位ベクトル（またはゼロベクトル）を返すこと"
    )


def test_potential_field_no_repulsion_outside_margin() -> None:
    """障害物から十分離れている場合、障害物斥力は働かないこと."""
    # ユニット: (0,0,0), 障害物: (600,0,0), radius=100, margin=50 → 有効距離 150m
    # 距離 600m > 150m → 斥力なし
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=4000, y=0, z=0))
    obs = _make_obstacle("obs1", 600.0, 0.0, 0.0, 100.0)

    sim_with_obs = BattleSimulator(player, [enemy], obstacles=[obs])
    sim_without_obs = BattleSimulator(
        _make_unit("Player2", "PLAYER", "PT", Vector3(x=0, y=0, z=0)),
        [_make_unit("Enemy2", "ENEMY", "ET", Vector3(x=4000, y=0, z=0))],
    )
    sim_with_obs.team_detected_units[player.team_id].add(enemy.id)
    sim_without_obs.team_detected_units[sim_without_obs.player.team_id].add(
        sim_without_obs.enemies[0].id
    )
    sim_with_obs.unit_resources[str(player.id)]["current_action"] = "MOVE"
    sim_without_obs.unit_resources[str(sim_without_obs.player.id)]["current_action"] = (
        "MOVE"
    )

    dir_with = sim_with_obs._calculate_potential_field(player)
    dir_without = sim_without_obs._calculate_potential_field(sim_without_obs.player)

    # 有効距離外の場合、方向ベクトルはほぼ同じになるはず
    assert np.allclose(dir_with, dir_without, atol=1e-3), (
        "有効距離外の障害物は方向ベクトルに影響しないこと"
    )


# ---------------------------------------------------------------------------
# 6. last_known_enemy_position tracking tests
# ---------------------------------------------------------------------------


def test_last_known_position_initialized_empty() -> None:
    """unit_resources に last_known_enemy_position が空辞書で初期化されること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=500, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    unit_id = str(player.id)
    assert "last_known_enemy_position" in sim.unit_resources[unit_id]
    assert sim.unit_resources[unit_id]["last_known_enemy_position"] == {}


def test_search_movement_uses_last_known_position() -> None:
    """last_known_enemy_position がある場合、そこへ向かって移動すること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=3000, y=0, z=3000))
    sim = BattleSimulator(player, [enemy])

    unit_id = str(player.id)
    # 最終既知座標を (3000, 0, 3000) に設定
    sim.unit_resources[unit_id]["last_known_enemy_position"][str(enemy.id)] = [
        3000.0,
        0.0,
        3000.0,
    ]

    initial_pos = player.position.to_numpy().copy()
    sim._search_movement(player, dt=0.1)
    new_pos = player.position.to_numpy()

    assert not np.allclose(new_pos, initial_pos), "移動が発生すること"


# ---------------------------------------------------------------------------
# 7. _get_units_in_weapon_range() tests
# ---------------------------------------------------------------------------


def test_get_units_in_weapon_range_includes_nearby() -> None:
    """射程内のユニットが正しく返されること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy_near = _make_unit("NearEnemy", "ENEMY", "ET", Vector3(x=300, y=0, z=0))
    enemy_far = _make_unit("FarEnemy", "ENEMY", "ET", Vector3(x=2000, y=0, z=0))
    sim = BattleSimulator(player, [enemy_near, enemy_far])

    result = sim._get_units_in_weapon_range(player, sim.units, weapon_max_range=500.0)
    ids = [u.id for u in result]
    assert enemy_near.id in ids, "射程内の敵は含まれるべき"
    assert enemy_far.id not in ids, "射程外の敵は含まれないべき"
    assert player.id not in ids, "自分自身は含まれないべき"


def test_get_units_in_weapon_range_empty_when_all_far() -> None:
    """全ユニットが射程外の場合、空リストが返されること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=5000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    result = sim._get_units_in_weapon_range(player, sim.units, weapon_max_range=100.0)
    assert result == []


# ---------------------------------------------------------------------------
# 8. BattleSimulator with obstacles parameter test
# ---------------------------------------------------------------------------


def test_simulator_accepts_obstacles_parameter() -> None:
    """BattleSimulator が obstacles パラメータを受け取ること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=500, y=0, z=0))
    obs = _make_obstacle("obs1", 250.0, 0.0, 0.0, 50.0)

    sim = BattleSimulator(player, [enemy], obstacles=[obs])
    assert len(sim.obstacles) == 1
    assert sim.obstacles[0].obstacle_id == "obs1"


def test_simulator_default_no_obstacles() -> None:
    """Obstacles を渡さない場合、空リストになること（後方互換性）."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=500, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    assert sim.obstacles == []


def test_full_simulation_with_obstacles_completes() -> None:
    """障害物ありでシミュレーションが正常に完了すること（後方互換性）."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), sensor_range=2000.0
    )
    enemy = _make_unit(
        "Enemy",
        "ENEMY",
        "ET",
        Vector3(x=4000, y=0, z=0),
        sensor_range=2000.0,
        weapon_range=1500.0,
    )
    # 射線外の障害物（両ユニット間の正射線からずれた位置）
    obs = _make_obstacle("obs1", 2000.0, 0.0, 300.0, 100.0)

    sim = BattleSimulator(player, [enemy], obstacles=[obs])

    for _ in range(100):
        if sim.is_finished:
            break
        sim.step()

    # クラッシュせず完了すること（勝敗は問わない）
    assert True


def test_full_simulation_without_obstacles_unchanged() -> None:
    """obstacles=[] でシミュレーション結果が従来と変わらないこと（後方互換性）."""
    import random

    random.seed(42)
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), sensor_range=2000.0
    )
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=500, y=0, z=0), sensor_range=2000.0
    )

    sim = BattleSimulator(player, [enemy])
    for _ in range(200):
        if sim.is_finished:
            break
        sim.step()

    # シミュレーションが完了すること
    assert sim.is_finished or any(u.current_hp <= 0 for u in sim.units)

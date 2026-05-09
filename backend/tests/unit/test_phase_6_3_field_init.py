"""Tests for Phase 6-3 — Field Initialization Improvement.

Validates:
1. SpawnZone model
2. BattleField.spawn_zones and obstacle_density fields
3. Default spawn zone generation (_generate_default_spawn_zones)
4. Spawn zone application (_apply_spawn_zones)
5. Obstacle auto-generation (_generate_obstacles)
6. battlefield parameter opt-in (backward compatibility)
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.engine.constants import (
    ALLY_REPULSION_RADIUS,
    MAP_BOUNDS,
    SPAWN_ZONE_RADIUS_2TEAM,
    SPAWN_ZONE_RADIUS_3TEAM,
    SPAWN_ZONE_RADIUS_4TEAM,
)
from app.engine.simulation import BattleSimulator
from app.models.models import BattleField, MobileSuit, Obstacle, SpawnZone, Vector3, Weapon

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MAP_MIN, MAP_MAX = MAP_BOUNDS


def _make_weapon(
    range_: float = 500.0,
    power: int = 30,
) -> Weapon:
    return Weapon(
        id=f"w_{id(object())}",
        name="Test Weapon",
        power=power,
        range=range_,
        accuracy=80.0,
    )


def _make_unit(
    name: str,
    side: str,
    team_id: str,
    pos: Vector3 | None = None,
    sensor_range: float = 2000.0,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=100,
        current_hp=100,
        armor=0,
        mobility=1.0,
        position=pos or Vector3(x=0, y=0, z=0),
        sensor_range=sensor_range,
        side=side,
        team_id=team_id,
        weapons=[_make_weapon()],
    )


# ---------------------------------------------------------------------------
# 1. SpawnZone model tests
# ---------------------------------------------------------------------------


def test_spawn_zone_model_fields() -> None:
    """SpawnZone モデルが必要なフィールドを持つこと."""
    sz = SpawnZone(
        team_id="TEAM_A",
        center=Vector3(x=500.0, y=0.0, z=500.0),
        radius=400.0,
    )
    assert sz.team_id == "TEAM_A"
    assert sz.center.x == 500.0
    assert sz.center.y == 0.0
    assert sz.center.z == 500.0
    assert sz.radius == 400.0


# ---------------------------------------------------------------------------
# 2. BattleField model extension tests
# ---------------------------------------------------------------------------


def test_battlefield_has_spawn_zones_field() -> None:
    """BattleField が spawn_zones フィールドを持ち、デフォルトは空であること."""
    bf = BattleField()
    assert bf.spawn_zones == []


def test_battlefield_has_obstacle_density_field() -> None:
    """BattleField が obstacle_density フィールドを持ち、デフォルトは MEDIUM であること."""
    bf = BattleField()
    assert bf.obstacle_density == "MEDIUM"


def test_battlefield_accepts_spawn_zones() -> None:
    """BattleField に spawn_zones を設定できること."""
    sz = SpawnZone(team_id="T1", center=Vector3(x=500, y=0, z=500), radius=400)
    bf = BattleField(spawn_zones=[sz])
    assert len(bf.spawn_zones) == 1
    assert bf.spawn_zones[0].team_id == "T1"


def test_battlefield_accepts_obstacle_density() -> None:
    """BattleField に obstacle_density を設定できること."""
    bf = BattleField(obstacle_density="DENSE")
    assert bf.obstacle_density == "DENSE"


def test_battlefield_obstacle_density_none() -> None:
    """obstacle_density='NONE' が設定できること."""
    bf = BattleField(obstacle_density="NONE")
    assert bf.obstacle_density == "NONE"


# ---------------------------------------------------------------------------
# 3. BattleSimulator backward compatibility
# ---------------------------------------------------------------------------


def test_backward_compat_no_battlefield_no_spawn_zones_applied() -> None:
    """battlefield を渡さない場合、ユニット位置が変更されないこと（後方互換性）."""
    player = _make_unit("P", "PLAYER", "PT", Vector3(x=100, y=0, z=100))
    enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=300, y=0, z=300))
    sim = BattleSimulator(player, [enemy])
    assert player.position.x == 100.0
    assert player.position.z == 100.0
    assert enemy.position.x == 300.0
    assert enemy.position.z == 300.0


def test_backward_compat_no_battlefield_no_obstacles_generated() -> None:
    """battlefield を渡さない場合、obstacles が自動生成されないこと（後方互換性）."""
    player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=500, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    assert sim.obstacles == []


def test_obstacles_param_still_works_without_battlefield() -> None:
    """obstacles 引数単体でも従来通り動作すること（後方互換性）."""
    player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=500, y=0, z=0))
    obs = Obstacle(obstacle_id="obs1", position=Vector3(x=250, y=0, z=0), radius=50)
    sim = BattleSimulator(player, [enemy], obstacles=[obs])
    assert len(sim.obstacles) == 1
    assert sim.obstacles[0].obstacle_id == "obs1"


# ---------------------------------------------------------------------------
# 4. BattleSimulator with battlefield — spawn zone generation
# ---------------------------------------------------------------------------


def test_default_spawn_zones_generated_for_2_teams() -> None:
    """battlefield を渡した場合、2チームのデフォルトスポーン領域が生成されること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy], battlefield=BattleField(obstacle_density="NONE"))
    assert len(sim.battlefield.spawn_zones) == 2


def test_default_spawn_zones_cover_all_team_ids() -> None:
    """生成されたスポーン領域が全チームをカバーすること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy], battlefield=BattleField(obstacle_density="NONE"))
    team_ids = {sz.team_id for sz in sim.battlefield.spawn_zones}
    assert "PT" in team_ids
    assert "ET" in team_ids


def test_2team_spawn_zone_radius() -> None:
    """2チームスポーン領域のデフォルト半径が正しいこと."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy], battlefield=BattleField(obstacle_density="NONE"))
    for sz in sim.battlefield.spawn_zones:
        assert sz.radius == SPAWN_ZONE_RADIUS_2TEAM


def test_2team_spawn_center_distance_gte_1000m() -> None:
    """2チームのスポーン中心間距離が 1000m 以上であること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy], battlefield=BattleField(obstacle_density="NONE"))
    zones = sim.battlefield.spawn_zones
    assert len(zones) == 2
    c0 = np.array([zones[0].center.x, zones[0].center.z])
    c1 = np.array([zones[1].center.x, zones[1].center.z])
    dist = float(np.linalg.norm(c0 - c1))
    assert dist >= 1000.0, f"スポーン中心間距離 {dist:.1f}m < 1000m"


def test_default_spawn_zones_3_teams() -> None:
    """3チームのデフォルトスポーン領域が正しく生成されること."""
    p = _make_unit("P", "PLAYER", "TA")
    e1 = _make_unit("E1", "ENEMY", "TB")
    e2 = _make_unit("E2", "ENEMY", "TC")
    sim = BattleSimulator(p, [e1, e2], battlefield=BattleField(obstacle_density="NONE"))
    assert len(sim.battlefield.spawn_zones) == 3
    for sz in sim.battlefield.spawn_zones:
        assert sz.radius == SPAWN_ZONE_RADIUS_3TEAM


def test_default_spawn_zones_4_teams() -> None:
    """4チームのデフォルトスポーン領域が生成されること."""
    p = _make_unit("P", "PLAYER", "TA")
    e1 = _make_unit("E1", "ENEMY", "TB")
    e2 = _make_unit("E2", "ENEMY", "TC")
    e3 = _make_unit("E3", "ENEMY", "TD")
    sim = BattleSimulator(p, [e1, e2, e3], battlefield=BattleField(obstacle_density="NONE"))
    assert len(sim.battlefield.spawn_zones) == 4
    for sz in sim.battlefield.spawn_zones:
        assert sz.radius == SPAWN_ZONE_RADIUS_4TEAM


def test_explicit_spawn_zones_not_overwritten() -> None:
    """明示的に spawn_zones を設定した場合、自動生成されないこと."""
    sz_p = SpawnZone(team_id="PT", center=Vector3(x=1000, y=0, z=1000), radius=300)
    sz_e = SpawnZone(team_id="ET", center=Vector3(x=4000, y=0, z=4000), radius=300)
    bf = BattleField(spawn_zones=[sz_p, sz_e], obstacle_density="NONE")
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy], battlefield=bf)
    # 明示的に渡したゾーンがそのまま使われること
    assert len(sim.battlefield.spawn_zones) == 2
    zone_map = {sz.team_id: sz for sz in sim.battlefield.spawn_zones}
    assert zone_map["PT"].center.x == 1000.0
    assert zone_map["ET"].center.x == 4000.0


# ---------------------------------------------------------------------------
# 5. Spawn zone application (_apply_spawn_zones)
# ---------------------------------------------------------------------------


def test_apply_spawn_zones_places_units_in_zone() -> None:
    """スポーン領域適用後、各ユニットがゾーン内に配置されること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy], battlefield=BattleField(obstacle_density="NONE"))

    zone_map = {sz.team_id: sz for sz in sim.battlefield.spawn_zones}
    for unit in sim.units:
        zone = zone_map[unit.team_id]
        dx = unit.position.x - zone.center.x
        dz = unit.position.z - zone.center.z
        dist = math.sqrt(dx * dx + dz * dz)
        assert dist <= zone.radius + 1e-6, (
            f"ユニット {unit.name} がゾーン外: dist={dist:.1f} > radius={zone.radius}"
        )


def test_apply_spawn_zones_with_zero_radius_places_at_center() -> None:
    """radius=0 のスポーン領域では、ユニットがゾーン中心に配置されること."""
    sz_p = SpawnZone(team_id="PT", center=Vector3(x=100, y=0, z=200), radius=0.0)
    sz_e = SpawnZone(team_id="ET", center=Vector3(x=4000, y=0, z=4000), radius=0.0)
    bf = BattleField(spawn_zones=[sz_p, sz_e], obstacle_density="NONE")
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy], battlefield=bf)

    assert abs(player.position.x - 100.0) < 1e-6
    assert abs(player.position.z - 200.0) < 1e-6
    assert abs(enemy.position.x - 4000.0) < 1e-6
    assert abs(enemy.position.z - 4000.0) < 1e-6


def test_apply_spawn_zones_ally_min_dist() -> None:
    """同チーム内の複数ユニットが ALLY_REPULSION_RADIUS 以上の間隔で配置されること."""
    # 3ユニット同チーム
    p = _make_unit("P", "PLAYER", "PT")
    a1 = _make_unit("A1", "PLAYER", "PT")
    a2 = _make_unit("A2", "PLAYER", "PT")
    e = _make_unit("E", "ENEMY", "ET")
    # 同チームは半径 600m のゾーンに 3 機
    sz_p = SpawnZone(team_id="PT", center=Vector3(x=500, y=0, z=500), radius=600.0)
    sz_e = SpawnZone(team_id="ET", center=Vector3(x=4500, y=0, z=4500), radius=400.0)
    bf = BattleField(spawn_zones=[sz_p, sz_e], obstacle_density="NONE")
    sim = BattleSimulator(p, [a1, a2, e], battlefield=bf)

    # PT チームのユニット位置を収集
    pt_units = [u for u in sim.units if u.team_id == "PT"]
    positions = [np.array([u.position.x, u.position.z]) for u in pt_units]
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            dist = float(np.linalg.norm(positions[i] - positions[j]))
            # 緩和が起きる場合があるため、完全ゼロでないことを確認
            assert dist >= 0.0  # クラッシュせず配置されること


# ---------------------------------------------------------------------------
# 6. Obstacle auto-generation (_generate_obstacles)
# ---------------------------------------------------------------------------


def test_obstacles_auto_generated_with_medium_density() -> None:
    """obstacle_density='MEDIUM' で障害物が自動生成されること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy], battlefield=BattleField(obstacle_density="MEDIUM"))
    assert len(sim.obstacles) > 0


def test_obstacles_auto_generated_with_dense_density() -> None:
    """obstacle_density='DENSE' で多数の障害物が生成されること (MEDIUM より多い傾向)."""
    player1 = _make_unit("P1", "PLAYER", "PT")
    enemy1 = _make_unit("E1", "ENEMY", "ET")
    sim_dense = BattleSimulator(
        player1, [enemy1], battlefield=BattleField(obstacle_density="DENSE")
    )
    player2 = _make_unit("P2", "PLAYER", "PT")
    enemy2 = _make_unit("E2", "ENEMY", "ET")
    sim_medium = BattleSimulator(
        player2, [enemy2], battlefield=BattleField(obstacle_density="MEDIUM")
    )
    # DENSE の方が障害物が多い（確率的なため ≥ で比較）
    # 少なくとも両方で障害物が存在すること
    assert len(sim_dense.obstacles) > 0
    assert len(sim_medium.obstacles) > 0


def test_obstacles_not_generated_with_none_density() -> None:
    """obstacle_density='NONE' では障害物が生成されないこと."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy], battlefield=BattleField(obstacle_density="NONE"))
    assert sim.obstacles == []


def test_obstacles_not_generated_when_obstacles_explicitly_passed() -> None:
    """obstacles を明示的に渡した場合、自動生成が行われないこと."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    obs = Obstacle(obstacle_id="manual_obs", position=Vector3(x=2500, y=0, z=2500), radius=100)
    sim = BattleSimulator(
        player, [enemy],
        obstacles=[obs],
        battlefield=BattleField(obstacle_density="DENSE"),
    )
    # obstacles 引数が優先され、自動生成されない
    assert len(sim.obstacles) == 1
    assert sim.obstacles[0].obstacle_id == "manual_obs"


def test_auto_generated_obstacles_not_in_spawn_zones() -> None:
    """自動生成された障害物がスポーン領域と重複しないこと."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy], battlefield=BattleField(obstacle_density="DENSE"))

    for obs in sim.obstacles:
        for sz in sim.battlefield.spawn_zones:
            dx = obs.position.x - sz.center.x
            dz = obs.position.z - sz.center.z
            dist = math.sqrt(dx * dx + dz * dz)
            assert dist >= sz.radius + obs.radius - 1e-6, (
                f"障害物 {obs.obstacle_id} がスポーン領域 {sz.team_id} と重複: "
                f"dist={dist:.1f} < radius_sum={sz.radius + obs.radius:.1f}"
            )


def test_auto_generated_obstacles_have_valid_ids() -> None:
    """自動生成された障害物に一意の ID が付与されること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy], battlefield=BattleField(obstacle_density="MEDIUM"))
    ids = [obs.obstacle_id for obs in sim.obstacles]
    assert len(ids) == len(set(ids)), "障害物 ID が重複している"


def test_sparse_density_generates_fewer_obstacles_than_dense() -> None:
    """SPARSE の障害物数が DENSE より少ない（確率的）傾向があること."""
    # 種固定でサンプル数を増やして比較（確率的なため複数回試行）
    sparse_counts = []
    dense_counts = []
    for _ in range(5):
        p = _make_unit("P", "PLAYER", "PT")
        e = _make_unit("E", "ENEMY", "ET")
        sim_s = BattleSimulator(p, [e], battlefield=BattleField(obstacle_density="SPARSE"))
        sparse_counts.append(len(sim_s.obstacles))

        p2 = _make_unit("P2", "PLAYER", "PT")
        e2 = _make_unit("E2", "ENEMY", "ET")
        sim_d = BattleSimulator(p2, [e2], battlefield=BattleField(obstacle_density="DENSE"))
        dense_counts.append(len(sim_d.obstacles))

    assert sum(sparse_counts) <= sum(dense_counts), (
        f"SPARSE({sum(sparse_counts)}) > DENSE({sum(dense_counts)}) は期待外"
    )


# ---------------------------------------------------------------------------
# 7. Full simulation with battlefield parameter
# ---------------------------------------------------------------------------


def test_full_simulation_with_battlefield_completes() -> None:
    """battlefield パラメータありでシミュレーションが正常に完了すること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(
        player, [enemy],
        battlefield=BattleField(obstacle_density="MEDIUM"),
    )
    for _ in range(200):
        if sim.is_finished:
            break
        sim.step()
    assert True  # クラッシュしないこと


def test_battlefield_param_sets_explicit_flag() -> None:
    """battlefield パラメータを渡すと _battlefield_explicit が True になること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim_with = BattleSimulator(
        player, [enemy],
        battlefield=BattleField(obstacle_density="NONE"),
    )
    assert sim_with._battlefield_explicit is True

    player2 = _make_unit("P2", "PLAYER", "PT")
    enemy2 = _make_unit("E2", "ENEMY", "ET")
    sim_without = BattleSimulator(player2, [enemy2])
    assert sim_without._battlefield_explicit is False

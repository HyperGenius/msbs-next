"""スポーン時の索敵回避 + 初速付与のテスト.

Validates:
1. デフォルトスポーン領域が、参加ユニットの最大 sensor_range に対して十分な
   間隔（縁と縁の距離が sensor_range + 安全マージン以上）を持つこと
   （2 / 3 / 4 / 5 チームの各配置で）
2. 明示的に spawn_zones を渡した場合はフィールド拡張が行われないこと（後方互換性）
3. スポーン直後の各ユニットに、スポーン領域中心からフィールド中心へ向かう
   初速が付与されること
"""

from __future__ import annotations

import itertools
import math

import numpy as np

from app.engine.constants import (
    SPAWN_DETECTION_SAFETY_MARGIN,
    SPAWN_INITIAL_SPEED_RATIO,
)
from app.engine.simulation import BattleSimulator
from app.models.models import BattleField, MobileSuit, SpawnZone, Vector3, Weapon

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_weapon(range_: float = 500.0, power: int = 30) -> Weapon:
    return Weapon(
        id=f"w_{id(object())}",
        name="Test Weapon",
        power=power,
        range=range_,
        accuracy=80.0,
    )


def _make_unit(
    name: str,
    team_id: str,
    sensor_range: float = 900.0,
    max_speed: float = 80.0,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=100,
        current_hp=100,
        armor=0,
        mobility=1.0,
        position=Vector3(x=0, y=0, z=0),
        sensor_range=sensor_range,
        max_speed=max_speed,
        side="PLAYER",
        team_id=team_id,
        weapons=[_make_weapon()],
    )


def _min_edge_to_edge_distance(zones: list[SpawnZone]) -> float:
    """異なるチームの spawn_zones ペアのうち、最小の縁と縁の距離を返す."""
    best = math.inf
    for a, b in itertools.combinations(zones, 2):
        center_dist = math.sqrt(
            (a.center.x - b.center.x) ** 2 + (a.center.z - b.center.z) ** 2
        )
        edge_dist = center_dist - a.radius - b.radius
        best = min(best, edge_dist)
    return best


# ---------------------------------------------------------------------------
# 1. 索敵回避: 縁と縁の距離が sensor_range + マージン 以上であること
# ---------------------------------------------------------------------------


def test_2team_spawn_zones_guarantee_detection_safety() -> None:
    """2チームのスポーン領域が索敵範囲+マージン以上離れていること."""
    player = _make_unit("P", "PT", sensor_range=900.0)
    enemy = _make_unit("E", "ET", sensor_range=900.0)
    sim = BattleSimulator(
        player, [enemy], battlefield=BattleField(obstacle_density="NONE")
    )
    zones = sim.battlefield.spawn_zones
    assert len(zones) == 2
    edge_dist = _min_edge_to_edge_distance(zones)
    assert edge_dist >= 900.0 + SPAWN_DETECTION_SAFETY_MARGIN - 1e-6


def test_3team_spawn_zones_guarantee_detection_safety() -> None:
    """3チームのスポーン領域が索敵範囲+マージン以上離れていること."""
    p = _make_unit("P", "TA", sensor_range=900.0)
    e1 = _make_unit("E1", "TB", sensor_range=900.0)
    e2 = _make_unit("E2", "TC", sensor_range=900.0)
    sim = BattleSimulator(p, [e1, e2], battlefield=BattleField(obstacle_density="NONE"))
    zones = sim.battlefield.spawn_zones
    assert len(zones) == 3
    edge_dist = _min_edge_to_edge_distance(zones)
    assert edge_dist >= 900.0 + SPAWN_DETECTION_SAFETY_MARGIN - 1e-6


def test_4team_spawn_zones_guarantee_detection_safety() -> None:
    """4チームのスポーン領域が索敵範囲+マージン以上離れていること."""
    p = _make_unit("P", "TA", sensor_range=900.0)
    e1 = _make_unit("E1", "TB", sensor_range=900.0)
    e2 = _make_unit("E2", "TC", sensor_range=900.0)
    e3 = _make_unit("E3", "TD", sensor_range=900.0)
    sim = BattleSimulator(
        p, [e1, e2, e3], battlefield=BattleField(obstacle_density="NONE")
    )
    zones = sim.battlefield.spawn_zones
    assert len(zones) == 4
    edge_dist = _min_edge_to_edge_distance(zones)
    assert edge_dist >= 900.0 + SPAWN_DETECTION_SAFETY_MARGIN - 1e-6


def test_5team_circular_spawn_zones_guarantee_detection_safety() -> None:
    """5チーム以上（円周配置）のスポーン領域が索敵範囲+マージン以上離れていること."""
    p = _make_unit("P", "TA", sensor_range=900.0)
    enemies = [_make_unit(f"E{i}", f"T{i}", sensor_range=900.0) for i in range(4)]
    sim = BattleSimulator(p, enemies, battlefield=BattleField(obstacle_density="NONE"))
    zones = sim.battlefield.spawn_zones
    assert len(zones) == 5
    edge_dist = _min_edge_to_edge_distance(zones)
    assert edge_dist >= 900.0 + SPAWN_DETECTION_SAFETY_MARGIN - 1e-6


def test_field_expands_when_min_field_size_too_small_for_sensor_range() -> None:
    """少数ユニット戦闘 (MIN_FIELD_SIZE クランプ対象) でも索敵回避が保証されること."""
    player = _make_unit("P", "PT", sensor_range=900.0)
    enemy = _make_unit("E", "ET", sensor_range=900.0)
    sim = BattleSimulator(
        player, [enemy], battlefield=BattleField(obstacle_density="NONE")
    )
    # MIN_FIELD_SIZE=2000 では 900m 索敵範囲を安全に回避できないため拡張されること
    assert sim.map_bounds[1] > 2000.0


def test_explicit_spawn_zones_bypass_field_expansion() -> None:
    """明示的な spawn_zones を渡した場合、索敵回避のためのフィールド拡張は行われないこと."""
    sz_p = SpawnZone(team_id="PT", center=Vector3(x=200, y=0, z=200), radius=100)
    sz_e = SpawnZone(team_id="ET", center=Vector3(x=400, y=0, z=400), radius=100)
    bf = BattleField(spawn_zones=[sz_p, sz_e], obstacle_density="NONE")
    player = _make_unit("P", "PT", sensor_range=900.0)
    enemy = _make_unit("E", "ET", sensor_range=900.0)
    sim = BattleSimulator(player, [enemy], battlefield=bf)
    # 明示的に渡した狭いゾーンがそのまま使われ、フィールドも拡張されない
    zone_map = {sz.team_id: sz for sz in sim.battlefield.spawn_zones}
    assert zone_map["PT"].center.x == 200.0
    assert zone_map["ET"].center.x == 400.0


# ---------------------------------------------------------------------------
# 2. スポーン時初速の付与
# ---------------------------------------------------------------------------


def test_units_receive_nonzero_initial_velocity_on_spawn() -> None:
    """スポーン直後のユニットが max_speed × SPAWN_INITIAL_SPEED_RATIO の初速を持つこと."""
    player = _make_unit("P", "PT", max_speed=100.0)
    enemy = _make_unit("E", "ET", max_speed=100.0)
    sim = BattleSimulator(
        player, [enemy], battlefield=BattleField(obstacle_density="NONE")
    )
    for unit in sim.units:
        speed = float(unit.velocity.to_numpy() @ unit.velocity.to_numpy()) ** 0.5
        assert speed > 0.0
        assert abs(speed - unit.max_speed * SPAWN_INITIAL_SPEED_RATIO) < 1e-6


def test_initial_velocity_points_toward_field_center() -> None:
    """初速の向きがスポーン領域中心からフィールド中心へ向かう方向であること."""
    player = _make_unit("P", "PT", max_speed=100.0)
    enemy = _make_unit("E", "ET", max_speed=100.0)
    sim = BattleSimulator(
        player, [enemy], battlefield=BattleField(obstacle_density="NONE")
    )
    map_min, map_max = sim.map_bounds
    field_center = np.array([(map_min + map_max) / 2.0, 0.0, (map_min + map_max) / 2.0])

    for unit in sim.units:
        pos = unit.position.to_numpy()
        vel = unit.velocity.to_numpy()
        to_center = field_center - pos
        # 初速ベクトルは「フィールド中心方向」と同じ向き（内積が正）であること
        assert float(np.dot(vel, to_center)) > 0.0


def test_unit_resources_velocity_vec_matches_unit_velocity_on_spawn() -> None:
    """unit_resources の velocity_vec (実シミュレーション用) も初速と一致すること."""
    player = _make_unit("P", "PT", max_speed=100.0)
    enemy = _make_unit("E", "ET", max_speed=100.0)
    sim = BattleSimulator(
        player, [enemy], battlefield=BattleField(obstacle_density="NONE")
    )
    for unit in sim.units:
        resources = sim.unit_resources[str(unit.id)]
        np.testing.assert_allclose(
            resources["velocity_vec"], unit.velocity.to_numpy(), atol=1e-6
        )


def test_no_initial_velocity_without_battlefield() -> None:
    """Battlefield を渡さない場合（後方互換性）は初速も付与されないこと."""
    player = _make_unit("P", "PT")
    enemy = _make_unit("E", "ET")
    sim = BattleSimulator(player, [enemy])
    for unit in sim.units:
        speed = float(np.linalg.norm(unit.velocity.to_numpy()))
        assert speed == 0.0

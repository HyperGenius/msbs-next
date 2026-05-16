"""Tests for Phase 6-5 — Field Scaling (dynamic MAP_BOUNDS per unit count).

Validates:
1. constants: AREA_PER_UNIT, MIN_FIELD_SIZE, MAX_FIELD_SIZE が定義されていること
2. BattleSimulator.map_bounds が総ユニット数から動的計算されること
3. グローバル定数 MAP_BOUNDS が書き換えられないこと
4. 最小・最大フィールドサイズがクランプされること
5. _generate_default_spawn_zones() が self.map_bounds を使用すること
6. _generate_obstacles() が self.map_bounds を使用すること
"""

from __future__ import annotations

import math

from app.engine.constants import (
    AREA_PER_UNIT,
    MAP_BOUNDS,
    MAX_FIELD_SIZE,
    MIN_FIELD_SIZE,
)
from app.engine.simulation import BattleSimulator
from app.models.models import BattleField, MobileSuit, Vector3, Weapon


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


def _make_unit(name: str, side: str, team_id: str) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=100,
        current_hp=100,
        armor=0,
        mobility=1.0,
        position=Vector3(x=0, y=0, z=0),
        sensor_range=2000.0,
        side=side,
        team_id=team_id,
        weapons=[_make_weapon()],
    )


# ---------------------------------------------------------------------------
# 1. 定数定義テスト
# ---------------------------------------------------------------------------


def test_area_per_unit_defined() -> None:
    """AREA_PER_UNIT が constants.py に定義されていること."""
    assert AREA_PER_UNIT == 250_000.0


def test_min_field_size_defined() -> None:
    """MIN_FIELD_SIZE が constants.py に定義されていること."""
    assert MIN_FIELD_SIZE == 2000.0


def test_max_field_size_defined() -> None:
    """MAX_FIELD_SIZE が constants.py に定義されていること."""
    assert MAX_FIELD_SIZE == 8000.0


# ---------------------------------------------------------------------------
# 2. BattleSimulator.map_bounds 動的計算テスト
# ---------------------------------------------------------------------------


def test_map_bounds_attribute_exists() -> None:
    """BattleSimulator が map_bounds インスタンス属性を持つこと."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy])
    assert hasattr(sim, "map_bounds")


def test_map_bounds_is_tuple_of_two_floats() -> None:
    """map_bounds が (float, float) のタプルであること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy])
    assert isinstance(sim.map_bounds, tuple)
    assert len(sim.map_bounds) == 2
    assert isinstance(sim.map_bounds[0], float)
    assert isinstance(sim.map_bounds[1], float)


def test_map_bounds_starts_at_zero() -> None:
    """map_bounds の下限は常に 0.0 であること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy])
    assert sim.map_bounds[0] == 0.0


def test_map_bounds_2_units_equals_min_field_size() -> None:
    """2ユニット (sqrt(2 * 250000) ≈ 707) は MIN_FIELD_SIZE にクランプされること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy])
    # sqrt(2 * 250000) = 707 < MIN_FIELD_SIZE=2000 → クランプ
    assert sim.map_bounds == (0.0, MIN_FIELD_SIZE)


def test_map_bounds_scales_with_unit_count() -> None:
    """ユニット数が増えるにつれてフィールドが大きくなること."""
    # 2ユニット: sqrt(2 * 250000) ≈ 707 → MIN_FIELD_SIZE=2000 にクランプ
    player_small = _make_unit("P", "PLAYER", "PT")
    enemy_small = _make_unit("E", "ENEMY", "ET")
    sim_small = BattleSimulator(player_small, [enemy_small])

    # 20ユニット: sqrt(20 * 250000) ≈ 2236 > MIN_FIELD_SIZE → クランプなし
    player_large = _make_unit("P2", "PLAYER", "PT")
    enemies_large = [_make_unit(f"E{i}", "ENEMY", "ET") for i in range(19)]
    sim_large = BattleSimulator(player_large, enemies_large)

    assert sim_large.map_bounds[1] > sim_small.map_bounds[1]


def test_map_bounds_formula_10_units() -> None:
    """10ユニット時のフィールドサイズが sqrt(10 * AREA_PER_UNIT) になること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemies = [_make_unit(f"E{i}", "ENEMY", "ET") for i in range(9)]
    sim = BattleSimulator(player, enemies)

    expected = math.sqrt(10 * AREA_PER_UNIT)
    expected = max(MIN_FIELD_SIZE, min(MAX_FIELD_SIZE, expected))
    assert abs(sim.map_bounds[1] - expected) < 1e-6


def test_map_bounds_formula_20_units() -> None:
    """20ユニット時のフィールドサイズが sqrt(20 * AREA_PER_UNIT) になること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemies = [_make_unit(f"E{i}", "ENEMY", "ET") for i in range(19)]
    sim = BattleSimulator(player, enemies)

    expected = math.sqrt(20 * AREA_PER_UNIT)
    expected = max(MIN_FIELD_SIZE, min(MAX_FIELD_SIZE, expected))
    assert abs(sim.map_bounds[1] - expected) < 1e-6


# ---------------------------------------------------------------------------
# 3. グローバル定数 MAP_BOUNDS が書き換えられないこと
# ---------------------------------------------------------------------------


def test_global_map_bounds_not_modified() -> None:
    """BattleSimulator 生成後もグローバル定数 MAP_BOUNDS が変更されていないこと."""
    original = MAP_BOUNDS
    player = _make_unit("P", "PLAYER", "PT")
    enemies = [_make_unit(f"E{i}", "ENEMY", "ET") for i in range(9)]
    BattleSimulator(player, enemies)
    assert MAP_BOUNDS == original, "グローバル定数 MAP_BOUNDS が書き換えられてはならない"


# ---------------------------------------------------------------------------
# 4. MIN_FIELD_SIZE / MAX_FIELD_SIZE クランプテスト
# ---------------------------------------------------------------------------


def test_map_bounds_min_clamp_for_small_unit_count() -> None:
    """少ユニット数 (2) では MIN_FIELD_SIZE にクランプされること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemy = _make_unit("E", "ENEMY", "ET")
    sim = BattleSimulator(player, [enemy])
    assert sim.map_bounds[1] >= MIN_FIELD_SIZE


def test_map_bounds_max_clamp_for_large_unit_count() -> None:
    """大ユニット数では MAX_FIELD_SIZE を超えないこと."""
    # sqrt(300 * 250000) = sqrt(75_000_000) ≈ 8660 > MAX_FIELD_SIZE=8000
    player = _make_unit("P", "PLAYER", "PT")
    enemies = [_make_unit(f"E{i}", "ENEMY", "ET") for i in range(299)]
    sim = BattleSimulator(player, enemies)
    assert sim.map_bounds[1] <= MAX_FIELD_SIZE


def test_map_bounds_at_max_boundary() -> None:
    """MAX_FIELD_SIZE を超える計算値が MAX_FIELD_SIZE に丸められること."""
    player = _make_unit("P", "PLAYER", "PT")
    # sqrt(N * 250000) > 8000  → N > 256
    enemies = [_make_unit(f"E{i}", "ENEMY", "ET") for i in range(299)]
    sim = BattleSimulator(player, enemies)
    assert sim.map_bounds == (0.0, MAX_FIELD_SIZE)


# ---------------------------------------------------------------------------
# 5. _generate_default_spawn_zones が動的 map_bounds を使用すること
# ---------------------------------------------------------------------------


def test_spawn_zones_use_dynamic_map_bounds() -> None:
    """スポーン領域の中心座標が動的 map_bounds 内に収まること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemies = [_make_unit(f"E{i}", "ENEMY", "ET") for i in range(9)]
    sim = BattleSimulator(player, enemies, battlefield=BattleField(obstacle_density="NONE"))

    map_min, map_max = sim.map_bounds
    for sz in sim.battlefield.spawn_zones:
        assert map_min <= sz.center.x <= map_max, (
            f"スポーン中心 x={sz.center.x} が map_bounds {sim.map_bounds} 外"
        )
        assert map_min <= sz.center.z <= map_max, (
            f"スポーン中心 z={sz.center.z} が map_bounds {sim.map_bounds} 外"
        )


def test_spawn_zones_2team_differ_by_unit_count() -> None:
    """ユニット数が異なると 2 チームのスポーン中心間距離が変わること."""
    # 小規模 (2 units) → map_bounds = (0, 2000) (MIN_FIELD_SIZE クランプ)
    p_small = _make_unit("P", "PLAYER", "PT")
    e_small = _make_unit("E", "ENEMY", "ET")
    sim_small = BattleSimulator(p_small, [e_small], battlefield=BattleField(obstacle_density="NONE"))

    # 大規模 (20 units, 2 teams) → sqrt(20 * 250000) ≈ 2236 > MIN_FIELD_SIZE
    p_large = _make_unit("P2", "PLAYER", "PT")
    enemies_large = [_make_unit(f"E{i}", "ENEMY", "ET") for i in range(19)]
    sim_large = BattleSimulator(p_large, enemies_large, battlefield=BattleField(obstacle_density="NONE"))

    def _center_dist(sim: BattleSimulator) -> float:
        zones = {sz.team_id: sz for sz in sim.battlefield.spawn_zones}
        teams = sorted(zones.keys())
        if len(teams) < 2:
            return 0.0
        c1 = zones[teams[0]].center
        c2 = zones[teams[1]].center
        return math.sqrt((c1.x - c2.x) ** 2 + (c1.z - c2.z) ** 2)

    dist_small = _center_dist(sim_small)
    dist_large = _center_dist(sim_large)
    assert dist_large > dist_small, (
        f"大規模戦闘のスポーン間距離 ({dist_large:.1f}m) が"
        f"小規模 ({dist_small:.1f}m) より大きいこと"
    )


# ---------------------------------------------------------------------------
# 6. _generate_obstacles が動的 map_bounds を使用すること
# ---------------------------------------------------------------------------


def test_obstacles_within_dynamic_map_bounds() -> None:
    """自動生成された障害物の位置が動的 map_bounds 内に収まること."""
    player = _make_unit("P", "PLAYER", "PT")
    enemies = [_make_unit(f"E{i}", "ENEMY", "ET") for i in range(9)]
    sim = BattleSimulator(
        player, enemies, battlefield=BattleField(obstacle_density="MEDIUM")
    )

    map_min, map_max = sim.map_bounds
    for obs in sim.obstacles:
        assert map_min <= obs.position.x <= map_max, (
            f"障害物 x={obs.position.x} が map_bounds {sim.map_bounds} 外"
        )
        assert map_min <= obs.position.z <= map_max, (
            f"障害物 z={obs.position.z} が map_bounds {sim.map_bounds} 外"
        )

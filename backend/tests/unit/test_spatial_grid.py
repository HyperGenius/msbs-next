"""Tests for UnitSpatialGrid (Issue #446) / PointSpatialGrid (Issue #447).

近傍探索（グリッド分割）の境界条件を単体で検証する:
- セル境界上・負座標での分類
- 3x3x3近傍セルの範囲内/範囲外の判定
- 極小セルサイズの下限クランプ
- 空グリッドの挙動
"""

import numpy as np

from app.engine.spatial_grid import _MIN_CELL_SIZE, PointSpatialGrid, UnitSpatialGrid
from app.models.models import MobileSuit, Vector3, Weapon


def _make_unit(name: str, x: float, y: float, z: float) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=100,
        current_hp=100,
        armor=0,
        mobility=1.0,
        position=Vector3(x=x, y=y, z=z),
        side="PLAYER",
        team_id="T",
        weapons=[Weapon(id=f"w_{name}", name="w", power=10, range=100, accuracy=80)],
    )


def _neighbor_names(grid: UnitSpatialGrid, pos: tuple[float, float, float]) -> set[str]:
    return {u.name for u in grid.neighbors(np.array(pos))}


def test_neighbors_returns_units_in_same_cell() -> None:
    """同一セル内のユニットは近傍探索で取得できること."""
    a = _make_unit("a", 10.0, 0.0, 10.0)
    b = _make_unit("b", 20.0, 0.0, 20.0)
    grid = UnitSpatialGrid([a, b], cell_size=500.0)

    names = _neighbor_names(grid, (0.0, 0.0, 0.0))
    assert names == {"a", "b"}


def test_neighbors_returns_units_in_adjacent_cell() -> None:
    """セル幅 = 探索半径のとき、隣接セルのユニットも取得できること."""
    # cell_size=500 → 基準点(0,0,0)のセルは(0,0,0)。隣接セル(1,0,0)内の点(600,0,0)も
    # 3x3x3近傍に含まれるはず
    near = _make_unit("near", 600.0, 0.0, 0.0)
    grid = UnitSpatialGrid([near], cell_size=500.0)

    names = _neighbor_names(grid, (0.0, 0.0, 0.0))
    assert names == {"near"}


def test_neighbors_excludes_units_two_cells_away() -> None:
    """2セル以上離れたユニットは近傍探索の対象外であること."""
    far = _make_unit(
        "far", 1600.0, 0.0, 0.0
    )  # cell (3,0,0): 基準セル(0,0,0)から2セル以上離れる
    grid = UnitSpatialGrid([far], cell_size=500.0)

    names = _neighbor_names(grid, (0.0, 0.0, 0.0))
    assert names == set()


def test_neighbors_handles_negative_coordinates() -> None:
    """負座標のユニットも正しくセル分類・近傍探索できること."""
    unit = _make_unit("neg", -600.0, 0.0, -600.0)
    grid = UnitSpatialGrid([unit], cell_size=500.0)

    names = _neighbor_names(grid, (-1000.0, 0.0, -1000.0))
    assert names == {"neg"}

    # 十分離れた正座標からは見えない
    names_far = _neighbor_names(grid, (2000.0, 0.0, 2000.0))
    assert names_far == set()


def test_neighbors_handles_cell_boundary_exactly() -> None:
    """セル境界ちょうどの座標でも一貫した分類がされること（境界は隣接セル側に属する）."""
    # cell_size=500 のとき x=500.0 はセル(1,*,*)に属する（int(500.0 // 500.0) == 1）
    boundary_unit = _make_unit("boundary", 500.0, 0.0, 0.0)
    grid = UnitSpatialGrid([boundary_unit], cell_size=500.0)

    # 基準セル(0,0,0)から見て隣接セル(1,0,0)なので3x3x3近傍に含まれる
    names = _neighbor_names(grid, (0.0, 0.0, 0.0))
    assert names == {"boundary"}


def test_min_cell_size_clamp() -> None:
    """cell_size が下限(_MIN_CELL_SIZE)未満でも下限にクランプされ縮退しないこと."""
    a = _make_unit("a", 0.0, 0.0, 0.0)
    b = _make_unit("b", 10.0, 0.0, 10.0)
    grid = UnitSpatialGrid([a, b], cell_size=0.0)

    assert grid.cell_size == _MIN_CELL_SIZE
    names = _neighbor_names(grid, (0.0, 0.0, 0.0))
    assert names == {"a", "b"}


def test_neighbors_empty_grid_returns_nothing() -> None:
    """空のユニット群から構築した場合、近傍探索は常に空集合を返すこと."""
    grid = UnitSpatialGrid([], cell_size=500.0)
    assert _neighbor_names(grid, (0.0, 0.0, 0.0)) == set()


# ---------------------------------------------------------------------------
# PointSpatialGrid (Issue #447)
# ---------------------------------------------------------------------------


def _neighbor_coords(
    grid: PointSpatialGrid, pos: tuple[float, float, float]
) -> set[tuple[float, float, float]]:
    return {
        (float(p[0]), float(p[1]), float(p[2])) for p in grid.neighbors(np.array(pos))
    }


def test_point_grid_empty_returns_nothing() -> None:
    """挿入前の空グリッドは近傍探索で常に空集合を返すこと."""
    grid = PointSpatialGrid(cell_size=150.0)
    assert _neighbor_coords(grid, (0.0, 0.0, 0.0)) == set()


def test_point_grid_returns_inserted_point_in_same_cell() -> None:
    """挿入した点が同一セル内であれば近傍探索で取得できること."""
    grid = PointSpatialGrid(cell_size=150.0)
    grid.insert(np.array([10.0, 0.0, 10.0]))

    assert _neighbor_coords(grid, (0.0, 0.0, 0.0)) == {(10.0, 0.0, 10.0)}


def test_point_grid_returns_points_in_adjacent_cell() -> None:
    """セル幅 = 探索半径のとき、隣接セルの点も取得できること."""
    grid = PointSpatialGrid(cell_size=150.0)
    grid.insert(np.array([200.0, 0.0, 0.0]))  # 隣接セル(1,0,0)

    assert _neighbor_coords(grid, (0.0, 0.0, 0.0)) == {(200.0, 0.0, 0.0)}


def test_point_grid_excludes_points_two_cells_away() -> None:
    """2セル以上離れた点は近傍探索の対象外であること."""
    grid = PointSpatialGrid(cell_size=150.0)
    grid.insert(np.array([500.0, 0.0, 0.0]))  # cell(3,0,0): 2セル以上離れる

    assert _neighbor_coords(grid, (0.0, 0.0, 0.0)) == set()


def test_point_grid_incremental_insert_accumulates() -> None:
    """insert() を繰り返した点が全て近傍探索で取得できること（逐次追加の確認）."""
    grid = PointSpatialGrid(cell_size=150.0)
    points = [np.array([float(i) * 10.0, 0.0, 0.0]) for i in range(5)]
    for p in points:
        grid.insert(p)

    assert _neighbor_coords(grid, (0.0, 0.0, 0.0)) == {
        (float(i) * 10.0, 0.0, 0.0) for i in range(5)
    }

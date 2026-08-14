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
# UnitSpatialGrid.nearest() (Issue #450)
# ---------------------------------------------------------------------------


def test_nearest_finds_unit_in_same_cell() -> None:
    """同一セル内の候補が最近傍として返ること."""
    near = _make_unit("near", 10.0, 0.0, 10.0)
    grid = UnitSpatialGrid([near], cell_size=150.0)

    result = grid.nearest(np.array([0.0, 0.0, 0.0]), lambda u: True)
    assert result is not None
    assert result.name == "near"


def test_nearest_returns_none_on_empty_grid() -> None:
    """空グリッドでは None を返すこと."""
    grid = UnitSpatialGrid([], cell_size=150.0)
    assert grid.nearest(np.array([0.0, 0.0, 0.0]), lambda u: True) is None


def test_nearest_returns_none_when_predicate_never_matches() -> None:
    """述語を満たす候補が一つも存在しない場合は None を返すこと（無限ループしないこと）."""
    a = _make_unit("a", 10.0, 0.0, 10.0)
    b = _make_unit("b", 2000.0, 0.0, 2000.0)
    grid = UnitSpatialGrid([a, b], cell_size=150.0)

    result = grid.nearest(np.array([0.0, 0.0, 0.0]), lambda u: False)
    assert result is None


def test_nearest_expands_beyond_neighbor_cells_when_candidate_is_far() -> None:
    """近傍セル（3x3x3）に候補がいなくても、遠方セルの真の最近傍を捕捉すること.

    `neighbors()`（固定3x3x3走査）では取りこぼす配置を意図的に作り、
    `nearest()` の環状探索が正しく候補を見つけられることを確認する。
    """
    # cell_size=150 のとき、原点から2000m離れた位置は3x3x3近傍の範囲外
    far_only_candidate = _make_unit("far", 2000.0, 0.0, 0.0)
    grid = UnitSpatialGrid([far_only_candidate], cell_size=150.0)

    # neighbors() では見つからないことを確認（前提条件）
    assert _neighbor_names(grid, (0.0, 0.0, 0.0)) == set()

    result = grid.nearest(np.array([0.0, 0.0, 0.0]), lambda u: True)
    assert result is not None
    assert result.name == "far"


def test_nearest_picks_true_global_closest_not_first_populated_cell() -> None:
    """最初に見つかったセルの候補ではなく、真にグローバルな最近傍を選ぶこと.

    近傍セルに1体だけ候補がいるが、その少し外側のセルにさらに近い候補が
    いる配置を作り、後者が正しく選ばれることを確認する
    （単純な「最初に見つかったセルで打ち切り」実装だと誤って前者を返す）。
    """
    # 隣接セル(1,0,0)内、距離200m
    near_cell_candidate = _make_unit("near_cell", 200.0, 0.0, 0.0)
    # 隣接セルより遠いセルにいるが、直線距離としては近い候補（斜め方向）
    # cell_size=150 のとき、(140, 0, 140) は距離約198mでセル(0,0,0)からは
    # 隣接セル(0,0,0)自身に含まれるため、代わりにより明確な配置を使う。
    closer_diagonal = _make_unit("closer", 60.0, 0.0, 60.0)  # 距離 ≒84.9m
    grid = UnitSpatialGrid([near_cell_candidate, closer_diagonal], cell_size=150.0)

    result = grid.nearest(np.array([0.0, 0.0, 0.0]), lambda u: True)
    assert result is not None
    assert result.name == "closer"


def test_nearest_respects_predicate_filter() -> None:
    """述語に一致しない候補は除外されること（例: 敵チーム限定）."""
    ally = _make_unit("ally", 10.0, 0.0, 10.0)
    enemy = _make_unit("enemy", 500.0, 0.0, 0.0)
    grid = UnitSpatialGrid([ally, enemy], cell_size=150.0)

    result = grid.nearest(np.array([0.0, 0.0, 0.0]), lambda u: u.name == "enemy")
    assert result is not None
    assert result.name == "enemy"


def test_nearest_matches_brute_force_over_random_layout() -> None:
    """ランダム配置において、nearest() の結果がO(N)総当たりの最近傍と一致すること."""
    rng = np.random.RandomState(12345)  # noqa: NPY002 テスト再現性のため固定シード
    units = [
        _make_unit(f"u{i}", *rng.uniform(-2000.0, 2000.0, size=3).tolist())
        for i in range(60)
    ]
    grid = UnitSpatialGrid(units, cell_size=150.0)

    for _ in range(20):
        query = rng.uniform(-2000.0, 2000.0, size=3)
        expected = min(
            units, key=lambda u: float(np.linalg.norm(u.position.to_numpy() - query))
        )
        result = grid.nearest(query, lambda u: True)
        assert result is not None
        expected_dist = float(np.linalg.norm(expected.position.to_numpy() - query))
        result_dist = float(np.linalg.norm(result.position.to_numpy() - query))
        # 同一距離の候補が複数存在しうるため、距離の一致で判定する
        assert abs(result_dist - expected_dist) < 1e-6


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

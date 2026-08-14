# backend/app/engine/spatial_grid.py
"""ユニット位置のグリッド分割による近傍探索用の補助構造体（Issue #446）.

索敵・ターゲット選定処理の全ユニット総当たり（O(N^2)）を解消するため、
ユニット位置を一定サイズのセルに分類し、近傍セルのみを走査することで
判定対象を近接ユニットに絞り込む。
"""

from collections import defaultdict
from collections.abc import Iterable, Iterator

import numpy as np

from app.models.models import MobileSuit

# セル座標 (cx, cy, cz)
CellKey = tuple[int, int, int]

# セルサイズの下限（索敵範囲が極端に小さい/ゼロの場合の縮退防止）
_MIN_CELL_SIZE = 100.0

_NEIGHBOR_OFFSETS: tuple[tuple[int, int, int], ...] = tuple(
    (dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
)


class UnitSpatialGrid:
    """位置ベースのグリッド分割インデックス（セル座標→ユニットリスト）.

    セルサイズを近傍探索で使う最大距離以上に設定すれば、あるユニットの
    セルと隣接26セル（3x3x3）の走査だけで、そのユニットからセルサイズ
    以内にいる可能性のある全ユニットを漏れなく捕捉できる
    （セル幅 >= 探索半径なら、2セル以上離れたセル間の最短距離はセル幅
    以上になるため、3x3x3の範囲外は距離的に候補になり得ない）。
    """

    def __init__(self, units: Iterable[MobileSuit], cell_size: float) -> None:
        """ユニット群をセル座標に分類してグリッドを構築する."""
        self.cell_size = max(float(cell_size), _MIN_CELL_SIZE)
        self._cells: dict[CellKey, list[MobileSuit]] = defaultdict(list)
        for unit in units:
            self._cells[self._cell_key_for_unit(unit)].append(unit)

    def _cell_key_for_unit(self, unit: MobileSuit) -> CellKey:
        pos = unit.position
        return self._cell_key(pos.x, pos.y, pos.z)

    def _cell_key(self, x: float, y: float, z: float) -> CellKey:
        return (
            int(x // self.cell_size),
            int(y // self.cell_size),
            int(z // self.cell_size),
        )

    def neighbors(self, pos: np.ndarray) -> Iterator[MobileSuit]:
        """指定座標を含むセルと近傍26セル（3x3x3）内の全ユニットを返す."""
        cx, cy, cz = self._cell_key(float(pos[0]), float(pos[1]), float(pos[2]))
        for dx, dy, dz in _NEIGHBOR_OFFSETS:
            cell = self._cells.get((cx + dx, cy + dy, cz + dz))
            if cell:
                yield from cell

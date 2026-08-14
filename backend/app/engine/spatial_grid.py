# backend/app/engine/spatial_grid.py
"""ユニット位置のグリッド分割による近傍探索用の補助構造体（Issue #446）.

索敵・ターゲット選定処理の全ユニット総当たり（O(N^2)）を解消するため、
ユニット位置を一定サイズのセルに分類し、近傍セルのみを走査することで
判定対象を近接ユニットに絞り込む。
"""

from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator

import numpy as np

from app.models.models import MobileSuit

# セル座標 (cx, cy, cz)
CellKey = tuple[int, int, int]

# セルサイズの下限（索敵範囲が極端に小さい/ゼロの場合の縮退防止）
_MIN_CELL_SIZE = 100.0

_NEIGHBOR_OFFSETS: tuple[tuple[int, int, int], ...] = tuple(
    (dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
)


def _shell_offsets(radius: int) -> Iterator[tuple[int, int, int]]:
    """チェビシェフ距離がちょうど `radius` のセルオフセットを列挙する（殻走査）.

    `UnitSpatialGrid.nearest()` の環状探索が「半径 radius の立方体全体を毎回
    O(radius^3) で走査してから殻だけに絞り込む」実装だと、探索半径が伸びる
    ケース（近傍に候補がおらず遠方まで探す必要がある場合）で無駄な走査コストが
    急増する。本関数は殻の外周セルだけを直接 O(radius^2) で生成することで
    この無駄を避ける。
    """
    if radius == 0:
        yield (0, 0, 0)
        return
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if abs(dx) == radius or abs(dy) == radius:
                # x/y 側で既に殻の境界に達しているので z は全範囲が殻に含まれる
                for dz in range(-radius, radius + 1):
                    yield (dx, dy, dz)
            else:
                # x/y だけでは境界に達しないので z が ±radius のときのみ殻
                yield (dx, dy, -radius)
                yield (dx, dy, radius)


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
        # nearest() の環状探索を打ち切るための探索範囲上限を求めるためのセル座標範囲
        self._min_cell = (0, 0, 0)
        self._max_cell = (0, 0, 0)
        for unit in units:
            key = self._cell_key_for_unit(unit)
            self._cells[key].append(unit)
        if self._cells:
            keys = self._cells.keys()
            self._min_cell = tuple(min(k[i] for k in keys) for i in range(3))  # type: ignore[assignment]
            self._max_cell = tuple(max(k[i] for k in keys) for i in range(3))  # type: ignore[assignment]

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

    def nearest(
        self, pos: np.ndarray, predicate: Callable[[MobileSuit], bool]
    ) -> MobileSuit | None:
        """述語を満たすユニットのうち、真にグローバルな最近傍を環状探索で求める（Issue #450）.

        `neighbors()` の固定 3x3x3 走査と異なり、近傍セルに述語を満たす候補が
        いない場合は探索半径（セル単位）を1段ずつ外側へ広げていく。ある半径
        `r` までの走査を終えた時点で見つかっている最小距離が `r * cell_size`
        以下であれば、まだ走査していないセルにそれより近い候補が存在し得ない
        （2セル以上離れたセル間の最短距離はセル幅以上、という `UnitSpatialGrid`
        の前提を一般化した性質）ため、その時点で打ち切って良い。これにより、
        単純な近傍セル限定探索では取りこぼしうる「たまたま近傍セルに候補がいない
        場合の真の最近傍」を漏れなく捕捉できる。

        Args:
            pos: 探索基準座標
            predicate: 候補ユニットを絞り込む述語（生存判定・敵味方判定など）

        Returns:
            述語を満たす最近傍ユニット。該当ユニットが存在しない場合は None。
        """
        if not self._cells:
            return None

        cx, cy, cz = self._cell_key(float(pos[0]), float(pos[1]), float(pos[2]))
        max_radius = max(
            abs(cx - self._min_cell[0]),
            abs(cx - self._max_cell[0]),
            abs(cy - self._min_cell[1]),
            abs(cy - self._max_cell[1]),
            abs(cz - self._min_cell[2]),
            abs(cz - self._max_cell[2]),
        )

        best: MobileSuit | None = None
        best_dist = float("inf")
        radius = 0
        while True:
            for dx, dy, dz in _shell_offsets(radius):
                cell = self._cells.get((cx + dx, cy + dy, cz + dz))
                if not cell:
                    continue
                for candidate in cell:
                    if not predicate(candidate):
                        continue
                    dist = float(np.linalg.norm(candidate.position.to_numpy() - pos))
                    if dist < best_dist:
                        best_dist = dist
                        best = candidate

            if best is not None and best_dist <= radius * self.cell_size:
                return best
            if radius >= max_radius:
                return best
            radius += 1


class PointSpatialGrid:
    """逐次追加される座標点（np.ndarray）向けの軽量グリッド分割インデックス（Issue #447）.

    `UnitSpatialGrid` は「全ユニットが揃った状態で一括構築し、以降は読み取り専用」
    という索敵フェーズの用途に合わせた設計だが、スポーン位置サンプリングでは
    ユニットを1体ずつ配置しながら「既配置点のうち一定距離以内に別の点がないか」を
    その都度判定する必要がある。本クラスは `insert()` による逐次追加をサポートし、
    セルサイズを判定に使う最大距離（呼び出し側が判定に使う可能性のある最大の
    min_dist）以上に固定することで、`UnitSpatialGrid` と同じ理屈（セル幅 >= 探索半径
    なら3x3x3近傍セルの走査だけで漏れなく候補を捕捉できる）を維持する。
    """

    # セルサイズの下限（cell_size に0以下が渡された場合のゼロ除算・縮退防止）
    _MIN_CELL_SIZE: float = 1e-6

    def __init__(self, cell_size: float) -> None:
        """セルサイズ（判定に使う可能性のある最大距離以上）を指定してグリッドを構築する."""
        self.cell_size = max(float(cell_size), self._MIN_CELL_SIZE)
        self._cells: dict[CellKey, list[np.ndarray]] = defaultdict(list)

    def _cell_key(self, x: float, y: float, z: float) -> CellKey:
        return (
            int(x // self.cell_size),
            int(y // self.cell_size),
            int(z // self.cell_size),
        )

    def insert(self, pos: np.ndarray) -> None:
        """座標点をグリッドに追加する."""
        self._cells[self._cell_key(float(pos[0]), float(pos[1]), float(pos[2]))].append(
            pos
        )

    def neighbors(self, pos: np.ndarray) -> Iterator[np.ndarray]:
        """指定座標を含むセルと近傍26セル（3x3x3）内の全登録点を返す."""
        cx, cy, cz = self._cell_key(float(pos[0]), float(pos[1]), float(pos[2]))
        for dx, dy, dz in _NEIGHBOR_OFFSETS:
            cell = self._cells.get((cx + dx, cy + dy, cz + dz))
            if cell:
                yield from cell

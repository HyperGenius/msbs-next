# backend/app/engine/rng.py
"""エンジンが使う numpy の乱数生成器.

`np.random.default_rng()` は `np.random.seed()` で固定できない。
エンジンは生成器を `new_numpy_rng()` で作り、結果を再現したい呼び出し元は
`seed_numpy_rngs()` でシードを固定する。固定しなければ毎回シードなしで作る（本番）。
"""

import numpy as np

_seed_sequence: np.random.SeedSequence | None = None


def new_numpy_rng() -> np.random.Generator:
    """乱数生成器（`np.random.Generator`）を作る.

    シードを固定していれば、作るたびに固定したシードから派生した別の系列を返す。
    """
    if _seed_sequence is None:
        return np.random.default_rng()
    return np.random.default_rng(_seed_sequence.spawn(1)[0])


def seed_numpy_rngs(seed: int | None) -> None:
    """以降に作る生成器のシードを固定する。None で固定をやめる."""
    global _seed_sequence
    _seed_sequence = None if seed is None else np.random.SeedSequence(seed)

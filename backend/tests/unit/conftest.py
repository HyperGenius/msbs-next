"""tests/unit 配下の乱数状態をテスト間で分離するための conftest.

`app.engine.*` の戦闘計算ロジックはグローバルな `random` モジュールに依存している。
一部のテスト（例: `test_simulation.py` の `random.seed(12345)` 呼び出し）が
明示的にシードを固定すると、そのテスト以降に実行される全テストが同じ乱数列を
引き継いでしまい、モンテカルロ的な確率アサーションの結果がテストの実行順序に
依存して変化していた（Issue #385）。

各テストの直前に `random.seed()` （引数なし = OS エントロピーで再初期化）を
呼び出すことで、あるテストの乱数消費・明示的なシード固定が後続のテストに
影響しないようにし、スイート全体実行時と単体実行時で結果が変わらないようにする。
"""

import random

import pytest


@pytest.fixture(autouse=True)
def _isolate_random_state() -> None:
    """テストごとに `random` モジュールの状態を独立させる."""
    random.seed()

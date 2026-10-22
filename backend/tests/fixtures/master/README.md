# テスト用マスターデータ

テスト専用の固定データです。**本番の値とは一致させません。**

マスターデータの正本は DB（`master_*` テーブル）です。
本番の値を変えるときは、管理画面か `scripts/maintenance/` のスクリプトで DB を直します。
このディレクトリの JSON を直しても、本番には反映されません。

## 使っている箇所

| 箇所 | 用途 |
|---|---|
| `tests/conftest.py` | 全テストの前に、インメモリ DB へ投入する |
| `tests/unit/test_engagement_bench.py` ほか | DB を使わない計測ツール（`engagement_bench.py`）に渡す |
| `scripts/verify/verify_ace_pilots.py` | 既定の投入元 |
| `scripts/seed/seed_master_data.py --data-dir tests/fixtures/master` | 本番に繋げない環境の初期投入 |

## 変更するとき

テストの期待値はこのデータに依存します。
本番の値に合わせて書き換えると、無関係なテストが落ちることがあります。
テストに新しい機体・武器が必要なら、追加してください。

本番の値でデータが必要なときは、`scripts/maintenance/export_master_data.py` で書き出します。
書き出したデータは Git に入れません。

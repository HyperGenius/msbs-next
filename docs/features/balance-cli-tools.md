# バランス調整CLIツール (Phase 5-3)

バトルエンジンのファジィルールや戦略モードのバランス調整を効率化するための CLI ツール群です。
`backend/scripts/run_simulation.py` のサブコマンドとして実装されています。

## サブコマンド一覧

| サブコマンド | 概要 |
|---|---|
| `run` | 単一シミュレーションを実行して結果 JSON を出力する（従来機能） |
| `bench` | 複数回シミュレーションを実行してサマリーを集計する |
| `compare` | 2つの戦略モードを A/B テストで比較する |
| `report` | 既存のシミュレーション結果 JSON からレポートを生成する |

---

## `run` サブコマンド（従来機能）

単一シミュレーションを実行して結果を JSON に出力します。

```bash
# ミッション 1 を実行（出力先は自動生成）
python scripts/run_simulation.py run --mission-id 1

# 出力先を指定
python scripts/run_simulation.py run --mission-id 2 --output results/mission2.json

# 戦略モードを指定
python scripts/run_simulation.py run --mission-id 1 --strategy AGGRESSIVE

# ファジィルール JSON のホットリロードを有効化 (Phase 5-2 連携)
python scripts/run_simulation.py run --mission-id 1 --hot-reload

# 後方互換: サブコマンドなしでも動作する
python scripts/run_simulation.py --mission-id 1
```

### オプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--mission-id` | 必須 | ミッション ID |
| `--output` | 自動生成 | 出力先 JSON ファイルパス |
| `--steps` | `5000` | 最大ステップ数 |
| `--strategy` | `None` | プレイヤーの戦略モード |
| `--hot-reload` | `False` | ファジィルールのホットリロード |

---

## `bench` サブコマンド

指定したミッション・戦略で N 回シミュレーションを実行し、統計サマリーを出力します。

```bash
# ミッション 1 を 20 回実行してサマリーを集計
python scripts/run_simulation.py bench --mission-id 1 --rounds 20

# 戦略モードを指定
python scripts/run_simulation.py bench --mission-id 1 --strategy DEFENSIVE --rounds 10

# JSON フォーマットで出力
python scripts/run_simulation.py bench --mission-id 1 --rounds 10 --format json

# ファイルに保存
python scripts/run_simulation.py bench --mission-id 1 --rounds 20 --output results/bench.txt
```

### オプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--mission-id` | 必須 | ミッション ID |
| `--rounds` | `10` | 実行回数 |
| `--strategy` | `AGGRESSIVE` | 全チームに適用する初期戦略モード |
| `--output` | stdout | 出力先ファイルパス |
| `--format` | `text` | 出力フォーマット (`text` / `json`) |
| `--steps` | `5000` | 最大ステップ数 |
| `--hot-reload` | `False` | ファジィルールのホットリロード |

### 出力例

```
=== Bench Summary: mission_id=1, strategy=AGGRESSIVE, rounds=20 ===

勝敗分布:
  PLAYER_TEAM 勝利: 12 回 (60.0%)
  ENEMY_TEAM 勝利:  6 回 (30.0%)
  引き分け   :  2 回 (10.0%)

平均戦闘時間: 38.4s (最短 22.1s / 最長 67.3s)

行動分布（全ユニット平均）:
  ATTACK      : 54.2%
  MOVE        : 28.1%
  USE_SKILL   :  8.4%
  RETREAT     :  9.3%

引き分け検出: 2 件（最大ステップ到達）
```

### 異常検出

以下の条件に該当する場合は⚠️警告が表示されます。

| 条件 | 閾値 | 警告内容 |
|---|---|---|
| 引き分け率が高い | `> 20%` | 戦闘が長期化しすぎている可能性 |
| 一方の勝率が高い | `> 80%` | バランスが偏っている可能性 |
| 平均戦闘時間が長い | `> 200s` | ステップ数が多すぎる可能性 |

閾値は `backend/app/engine/constants.py` の `BALANCE_WARN_*` 定数で変更できます。

---

## `compare` サブコマンド

2つの戦略モードを対戦させ、勝率・行動分布の差異を比較します。
プレイヤーチームに `--strategy-a`、敵チームに `--strategy-b` を適用します。

```bash
# AGGRESSIVE vs DEFENSIVE を 20 回対戦
python scripts/run_simulation.py compare \
  --mission-id 1 \
  --strategy-a AGGRESSIVE \
  --strategy-b DEFENSIVE \
  --rounds 20

# JSON 出力
python scripts/run_simulation.py compare \
  --mission-id 1 --strategy-a SNIPER --strategy-b ASSAULT --rounds 10 --format json
```

### オプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--mission-id` | 必須 | ミッション ID |
| `--rounds` | `10` | 実行回数 |
| `--strategy-a` | `AGGRESSIVE` | プレイヤーチームの戦略モード |
| `--strategy-b` | `DEFENSIVE` | 敵チームの戦略モード |
| `--output` | stdout | 出力先ファイルパス |
| `--format` | `text` | 出力フォーマット (`text` / `json`) |
| `--steps` | `5000` | 最大ステップ数 |
| `--hot-reload` | `False` | ファジィルールのホットリロード |

### 出力例

```
=== Compare: AGGRESSIVE vs DEFENSIVE, rounds=20 ===

             AGGRESSIVE  DEFENSIVE
勝利回数             12          7
勝率             60.0%      35.0%
引き分け                         1

平均生存ユニット数       1.8        2.3
平均残HP率            0.32       0.51
平均行動: ATTACK    61.2%      38.4%
平均行動: RETREAT    4.1%      14.2%

判定: AGGRESSIVE が優勢（勝率差 +25.0%）⚠️ バランス要調整
```

---

## `report` サブコマンド

既存のシミュレーション結果 JSON（`run` コマンドで出力したファイル）を読み込み、ログを分析してレポートを生成します。

```bash
# 単一ファイル
python scripts/run_simulation.py report --input data/sim_results/result.json

# ワイルドカードで複数ファイルを一括処理
python scripts/run_simulation.py report --input "data/sim_results/result_*.json"

# JSON フォーマットで出力
python scripts/run_simulation.py report \
  --input "data/sim_results/*.json" --format json --output analysis.json
```

### オプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--input` | 必須 | 入力 JSON ファイルパス（ワイルドカード対応、複数可） |
| `--output` | stdout | 出力先ファイルパス |
| `--format` | `text` | 出力フォーマット (`text` / `json`) |

### 出力項目

- 勝敗集計（WIN / LOSE / DRAW の回数・割合）
- 行動分布（ATTACK / MOVE / USE_SKILL / RETREAT / DAMAGE / DESTROYED / MISS の回数・割合）
- 戦略遷移ログ（`STRATEGY_CHANGED` イベントの一覧・回数）
- 武器選択ログ（武器名ごとの使用回数・割合）
- ファジィスコア分布（サンプルがある場合）

---

## 実装ファイル構成

```
backend/scripts/
  run_simulation.py  # エントリーポイント（サブコマンドを振り分け）
  sim_bench.py       # bench サブコマンドの実処理（BenchRunner / SimulationSummary）
  sim_compare.py     # compare サブコマンドの実処理（CompareRunner / ComparisonSummary）
  sim_report.py      # report サブコマンドの実処理（ReportGenerator / Report）

backend/app/engine/
  constants.py       # BALANCE_WARN_DRAW_RATE / BALANCE_WARN_WIN_RATE / BALANCE_WARN_AVG_DURATION

backend/tests/unit/
  test_sim_bench.py  # bench / compare / report のユニットテスト
```

## 警告しきい値の変更

`backend/app/engine/constants.py` の以下の定数を編集することで閾値を変更できます。

```python
# バランス調整CLIツール 警告しきい値 (Phase 5-3) — チューニング可能
BALANCE_WARN_DRAW_RATE: float = 0.20     # 引き分け率がこれを超えると警告
BALANCE_WARN_WIN_RATE: float = 0.80      # 勝率がこれを超えると警告（一方的優位）
BALANCE_WARN_AVG_DURATION: float = 200.0 # 平均戦闘時間（秒）がこれを超えると警告
```

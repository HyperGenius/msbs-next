# バランス調整CLIツール (Phase 5-3)

バトルエンジンのファジィルールや戦略モードのバランス調整を効率化するための CLI ツール群です。
`backend/scripts/run_simulation.py` のサブコマンドとして実装されています。

## ローカルバトルシミュレータ（`local_sim`）との関係

`backend/scripts/simulation/local_sim` の `report` / `compare`（[local-battle-simulator.md](local-battle-simulator.md#report--compare-世代の集計と比較)）と、
本ドキュメントの `run_simulation.py` の `bench` / `compare` / `report` は、別のツールとして残す（Issue #613 で決定）。

| | `run_simulation.py`（ミッション戦） | `local_sim`（ルーム戦） |
|---|---|---|
| 機体 | DB の先頭の機体と、ミッションの `enemy_config` から組み立てた敵 | 本番の参加機体・NPC・エース（`fetch` のロスター） |
| 戦闘処理 | `BattleSimulator` を直接回す | 本番バッチと同じ `app/services/battle_execution.py` |
| DB | 実行のたびに `NEON_DATABASE_URL` を読む | `fetch` の1回だけ（Read Only）。`run` 以降は接続しない |
| 比べるもの | 同じ戦闘の中で、2つの戦略モード（A/B テスト） | エンジン・ファジィルールの変更前後（2つの世代） |
| 再現性 | シードを固定しない | シードで同じログを再現する |

* エンジン・ファジィルールの変更が本番の機体構成でどう効くかは、`local_sim` で確かめる。`run_simulation.py` は戦略モードの A/B を手早く比べる用途に残す
* 集計は共有する。行動分布・戦略遷移・武器の使用回数は `sim_report.ReportGenerator.add_result()`、警告は `sim_bench.balance_warnings()`（同じ `BALANCE_WARN_*`）
* `local_sim` は引き分けが無い（勝敗は判定する機体のチームが生き残ったか）。最大ステップ数での打ち切りを、bench の引き分け（最大ステップ到達）と同じ閾値で警告する
* 新しい集計項目は `local_sim` の `analysis.py` に足す。`run_simulation.py` 側には足さない

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
  sim_bench.py       # bench サブコマンドの実処理（BenchRunner / SimulationSummary / balance_warnings）
  sim_compare.py     # compare サブコマンドの実処理（CompareRunner / ComparisonSummary）
  sim_report.py      # report サブコマンドの実処理（ReportGenerator / Report）
  local_sim/analysis.py  # local_sim の report / compare。ReportGenerator と balance_warnings を使う

backend/app/engine/
  constants.py       # BALANCE_WARN_DRAW_RATE / BALANCE_WARN_WIN_RATE / BALANCE_WARN_AVG_DURATION

backend/tests/unit/
  test_sim_bench.py  # bench / compare / report のユニットテスト
  test_local_sim_analysis.py  # local_sim の report / compare のユニットテスト
```

## 警告しきい値の変更

`backend/app/engine/constants.py` の以下の定数を編集することで閾値を変更できます。

```python
# バランス調整CLIツール 警告しきい値 (Phase 5-3) — チューニング可能
BALANCE_WARN_DRAW_RATE: float = 0.20     # 引き分け率がこれを超えると警告
BALANCE_WARN_WIN_RATE: float = 0.80      # 勝率がこれを超えると警告（一方的優位）
BALANCE_WARN_AVG_DURATION: float = 200.0 # 平均戦闘時間（秒）がこれを超えると警告
```

---

## 直近バトル結果の取得・検証（`fetch_recent_battles.py`）

上記の各ツールがオフラインでのシミュレーション実行を対象とするのに対し、
`backend/scripts/verify/fetch_recent_battles.py` は**実際にDBへ保存された `battle_results` を直近から取得**して
コンソール表示・JSON出力する検証用スクリプトです（Issue #419）。

```bash
cd backend
source .venv/bin/activate

# 直近20件を取得（デフォルト）
python scripts/verify/fetch_recent_battles.py

# 件数・ユーザーを絞り込み
python scripts/verify/fetch_recent_battles.py --limit 50
python scripts/verify/fetch_recent_battles.py --user-id user_xxxx

# ターンごとの生ログ（battle_logs.logs）も含めて出力
python scripts/verify/fetch_recent_battles.py --with-logs
```

出力JSONは `backend/scripts/verify/output/` 配下にタイムスタンプ付きで生成されます。
このディレクトリは `.gitignore` 対象のため、取得したバトルデータがリポジトリにコミットされることはありません。

`NEON_DATABASE_URL`（共有のリモートDB）に接続する読み取り専用の参照ツールです。書き込みは行いません。

---

## 地形適正・環境効果のバランス確認（`terrain_balance_bench.py`）

`backend/scripts/simulation/terrain_balance_bench.py` は、環境タイプの効果と地形適正の影響を 1対1 のモンテカルロで確認するスクリプトです（Issue #576）。
DB を使わず、`backend/data/master/mobile_suits.json`・`environments.json` から戦闘を組み立てます。

```bash
cd backend
# 1 組 100 試行（既定）。並列数は既定で CPU コア数
python scripts/simulation/terrain_balance_bench.py

# 試行回数・並列数・シードを指定する
python scripts/simulation/terrain_balance_bench.py --rounds 60 --workers 8 --seed 576

# 同一機体のランク差だけを見る
python scripts/simulation/terrain_balance_bench.py --skip-masters
```

条件は「森林・ミノフスキー 0.6」と「宇宙・ミノフスキー 0.3」（スクリプト内の `_CONDITIONS`）。条件ごとに次の表を Markdown で出力します。

| 表 | 内容 |
|---|---|
| 同一機体のランク差 | ザク II の性能で地形適正ランク（S / A / C）だけを変えて総当たり |
| 特化機と汎用機 | 地形適正が A 以外の機体（ゲルググ・ドム・グフ）と汎用機（ザク II・ジム）の組 |

* 最大ステップは定期バトルと同じ 3000。決着しないときは残り HP の割合が高い方を勝ちとします
* 試行ごとに PLAYER 側を入れ替え、スポーン位置の偏りを消します
* 1 戦に数秒かかります。`--rounds 60` で 30〜60 分程度です

結果は [battle-engine-feature.md 30.9節](battle-engine-feature.md#309-バランス確認) に残しています。

---

## 交戦距離・膠着の計測（`engagement_bench.py`）

`backend/scripts/simulation/engagement_bench.py` は、1対1 の戦闘で「どの距離で戦っているか」「格闘の空振りが続いていないか」を数値で確認するスクリプトです（Issue #595、Epic #594）。
DB を使わず、`backend/data/master/mobile_suits.json`・`weapons.json` から機体と武器を組み立てます。バトルエンジンの挙動は変えません。

```bash
cd backend
# 全シナリオ × 戦略 4 種 × tactics.range の組を各 10 試行（既定）。8 コアで約 2 分
python scripts/simulation/engagement_bench.py run --output results/engagement_before.json

# シナリオ・戦略・試行回数を絞る
python scripts/simulation/engagement_bench.py run \
  --scenarios melee_duel --strategies AGGRESSIVE,ASSAULT --rounds 20

# 両機の tactics.range を指定する（既定はシナリオごとの組）
python scripts/simulation/engagement_bench.py run --ranges BALANCED,RANGED

# 両機のパイロット能力を指定する（書かない能力は 0。Issue #601）
python scripts/simulation/engagement_bench.py run --ranges BALANCED,MELEE --pilot mel=20

# 2 つの結果 JSON を比べる（変更前 → 変更後）
python scripts/simulation/engagement_bench.py diff \
  results/engagement_before.json results/engagement_after.json
```

### `run` のオプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--rounds` | `10` | 1 条件あたりの試行回数 |
| `--seed` | `595` | 1 試行目のシード。i 試行目は `seed + i` |
| `--workers` | CPU コア数 | 並列プロセス数。結果は並列数によらず同じ |
| `--max-steps` | `5000` | 最大ステップ数（0.1 秒刻み。5000 で 500 秒） |
| `--scenarios` | 全シナリオ | カンマ区切りのシナリオキー |
| `--strategies` | `AGGRESSIVE,DEFENSIVE,SNIPER,ASSAULT` | 両機に設定する戦略モード |
| `--ranges` | シナリオごとの組 | 両機に同じ `tactics.range` を設定する |
| `--pilot` | `sht=1,mel=1,intel=1,ref=1,tou=1,luk=1` | 両機のパイロット能力（`PilotStats` のフィールド名）。書かない能力は 0。`--pilot ""` で全能力 0 |
| `--output` | なし | 結果 JSON の保存先 |

### シナリオ

| キー | 内容 | 開始距離 | 既定の `tactics.range`（A×B） |
|---|---|---|---|
| `melee_duel` | ガンダム［ビームサーベル＋ビームライフル］ vs グフ［ヒートロッド＋ザクマシンガン］ | 300m | BALANCED×BALANCED、MELEE×MELEE |
| `melee_only_duel` | ガンダム［ビームサーベル］ vs グフ［ヒートロッド］。射撃に逃げられないため、鍔迫り合いの頻度の上限を見る（Issue #600） | 300m | BALANCED×BALANCED、MELEE×MELEE |
| `ranged_gundam_zaku` | ガンダム［ビームライフル］ vs ザクII［ザクマシンガン］ | 1000m | BALANCED×BALANCED、RANGED×RANGED |
| `ranged_gelgoog_gundam` | ゲルググ［ビームライフル］ vs ガンダム［ビームライフル］ | 1000m | BALANCED×BALANCED、RANGED×RANGED |
| `melee_vs_ranged` | グフ［ヒートロッド＋ザクマシンガン］ vs ガンダム［ビームライフル］ | 1000m | BALANCED×BALANCED、MELEE×RANGED |
| `melee_only_vs_ranged` | ガンダム［ビームサーベル］ vs ザクII［ザクマシンガン］ | 1000m | BALANCED×BALANCED、MELEE×RANGED |

シナリオはスクリプト内の `SCENARIOS` で定義しています。両機のパイロットステータスは同じ値にそろえます（既定は全項目 1、`--pilot` で変更）。

### 指標

| 列 | 内容 |
|---|---|
| 攻撃数 | 命中判定を行った攻撃（ATTACK / MISS）の合計 |
| 距離 p10/p50/p90 | 交戦中（最初の攻撃以降、両機の生存中）の毎ステップの両機間距離。全試行の標本をまとめて集計する |
| <50m / <150m | 交戦中に `MELEE_RANGE`（50m）未満・150m 未満にいた割合 |
| 最適比 格闘/射撃 p50 | 攻撃時の距離 ÷ 使用武器の `optimal_range` の中央値。格闘武器は `weapon_type == "MELEE"` または `is_melee` |
| 初格闘 p50 | 最初の格闘攻撃（命中判定を行ったもの）までの時間の中央値。格闘機が相手に追いつくまでの時間の目安。格闘しなかった戦闘は除く |
| 格闘ミス最長 | 同じユニットの格闘 MISS が、そのユニットの命中を挟まずに続いた最長の時間と回数（射撃の MISS では途切れない） |
| 持ち替え/分 | `WEAPON_SWITCH_START` の 1 機・1 分あたりの回数 |
| 鍔迫り合い/分 (格闘比) | `MELEE_CLASH` の両機あわせた 1 分あたりの回数と、格闘の攻撃（命中判定した格闘 + 鍔迫り合い 1 回につき 2 回）のうち鍔迫り合いになった割合（Issue #600） |
| 仕切り直し/分 | `DISENGAGE` の 1 機・1 分あたりの回数（Issue #601） |
| セクタ F/FS/RS/R % | 攻撃セクタ FRONT / FRONT_SIDE / REAR_SIDE / REAR の割合 |
| 戦闘時間 p50 / 時間切れ / 勝率 | 戦闘時間の中央値、最大ステップまで両機が生存した割合、A・B の勝率（時間切れは引き分け） |

* 攻撃時の距離とセクタは、`BattleSimulator._calculate_hit_chance()` をインスタンス単位で包んで記録します。MISS ログにはセクタが載らず、移動後の位置からは攻撃時の距離を復元できないためです。包む処理は乱数を消費しないため、戦闘結果は変わりません（`tests/unit/test_engagement_bench.py` で確認）
* 再現性のため `random`・`numpy.random`・部位選択用の RNG（`combat._part_hit_rng`）をすべて試行ごとに固定します。ユニット ID も固定値にします
* 行動順の偏りを消すため、奇数シードの試行では B を PLAYER 側にします
* 結果 JSON には `meta`（作成日時・git リビジョン・シード等）と、シナリオ・条件ごとの集計値（`results.<シナリオ>.<戦略>/<rangeA>x<rangeB>`）、試行ごとの戦闘時間・勝者・格闘ミス最長が入ります
* `diff` はシードまたは試行回数が異なると警告を出します。パイロット能力が異なるときは、両方の値を表示します

本 Epic 着手前の計測結果は Issue #595 のコメントに残しています。

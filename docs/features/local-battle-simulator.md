# ローカルバトルシミュレータ

## 概要

本番の参加機体を使ってバトルをローカルで回し、結果をブラウザで再生する開発用のシミュレータ。
Epic #608 の機能で、本ドキュメントは Sub-Issue 1（Issue #609）の範囲を記述する。

* 戦闘処理は本番バッチと同じモジュールを使う
* 機体データは Neon 本番環境から Read Only で取得する

### 今後の予定（Epic #608）

| Sub-Issue | 内容 |
|---|---|
| 1 | 本番バッチの戦闘実行処理を共通モジュールへ切り出す（Issue #609、実装済み。本ドキュメントの「[戦闘実行の共通モジュール](#戦闘実行の共通モジュール)」） |
| 2 | 本番DBへの Read Only 接続と参加機体の取得（fetch）（Issue #610） |
| 3 | ローカルシミュレーションの実行と世代管理（run）（Issue #611） |
| 4 | 開発用バトルビューア `/dev/sim`（Issue #612） |
| 5 | 世代間の比較とバランス分析表示（Issue #613） |
| 6 | エースパイロットの参加必須指定（Issue #614） |

---

## 戦闘実行の共通モジュール

`backend/app/services/battle_execution.py` に、ルーム戦の機体組み立てと戦闘実行をまとめた。
どの関数も DB セッションを使わない。本番バッチ（`backend/scripts/run_batch.py`）はこのモジュールを呼び、
DB の読み書きとフェーズ制御だけを持つ。本番バッチの挙動（勝敗・報酬・保存内容）は変えていない。

| 関数 | 役割 |
|---|---|
| `snapshot_to_mobile_suit(snapshot)` | `BattleEntry.mobile_suit_snapshot` から `MobileSuit` を組み立てる |
| `prepare_battle_units(player_snapshot, enemy_snapshots)` | 先頭をプレイヤー機、残りを敵機にする。`team_id` が無いユニットにはユニット ID を入れる |
| `run_battle(player_unit, enemy_units, conditions, max_steps)` | `BattleSimulator` を決着まで（最大 `max_steps`）回し、`BattleOutcome` を返す |
| `build_unit_view_fields(entry_unit, units)` | `BattleResult` の `player_info`・`enemies_info` を組み立てる。プレイヤーごとに値が変わる |
| `build_battlefield_view_fields(simulator)` | `BattleResult` の `obstacles_info`・`map_bounds` を組み立てる。ルーム内で共通のため、本番バッチはプレイヤーのループの外で1回だけ呼ぶ |
| `resolve_team_id(unit)` / `alive_team_ids(units)` | チームの解決と、生き残ったチームの集合 |

`BattleOutcome` は `simulator`・`player_win`・`kills`（プレイヤー機自身の撃墜数）・`steps_used` を持つ。

### 本番バッチとの役割分担

| 処理 | 置き場所 |
|---|---|
| 環境変数 `MAX_SIMULATION_STEPS` の読み込み | `run_batch.py`（既定値は `battle_execution.DEFAULT_MAX_STEPS`） |
| 戦域の条件（`TheaterService.battle_conditions()`） | `run_batch.py`（DB を読むため） |
| バトルログ・`BattleResult` の保存、報酬・戦利品・NPC 成長 | `run_batch.py` の `_save_battle_results()` |

### 注意点

* `snapshot_to_mobile_suit()` は渡した dict の位置・速度・武器・ID をモデルの型に書き換える。
  本番バッチはこの書き換え後の dict を `BattleResult.ms_snapshot` に保存するため、挙動を変えずに残している。
  元の dict を残したい呼び出し元はコピーを渡す
* `run_battle()` は渡したユニットの HP 等を戦闘後の状態に書き換える。`BattleResult` では
  `player_info` にエントリー時点の機体、`enemies_info` に戦闘後のユニットを入れる
* CI のエンジンスモークテスト（`scripts/simulation/engine_ci_smoke.py`）は合成ユニットで `BattleSimulator` を
  直接回しており、このモジュールを通らない。`dt` を変えて回すため、本 Issue では置き換えていない

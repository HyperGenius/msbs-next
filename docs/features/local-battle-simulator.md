# ローカルバトルシミュレータ

## 概要

本番の参加機体を使って、バトルをローカルで実行する開発用のツール。
Epic #608 で作る。このドキュメントは Sub-Issue 1〜5（Issue #609〜#613）、7（Issue #699）、10（Issue #703）の範囲を書く。

* 戦闘処理は本番バッチと同じモジュール（`app/services/battle_execution.py`）を使う
* `fetch` で本番DBから参加機体・NPC・エースと戦域条件を読み、手元の JSON（ロスター）に保存する
* 本番DBへの接続は `fetch` の1回だけ。以降の実行（`run`）はロスターだけで行い、DB には接続しない
* `run` は同じロスター・同じシードなら同じログを再現する。1回の `run` を1世代として保存し、直近5世代を残す
* 本番DBには書き込まない。SELECT 権限だけのロールと `default_transaction_read_only` の2つで防ぐ
* 保存した結果は、開発環境の `/dev/sim` で本番の履歴詳細と同じ画面で再生できる
* `report` / `compare` で世代の勝率・戦闘時間・行動分布などを集計し、2つの世代を比べられる。`/dev/sim` でも比べられ、再生中に AI の判断（ファジィスコア）を確かめられる
* `log-bench` / `log-compare` で、シード固定の50機の戦闘のログのサイズと端末の負荷を、保存形式ごとに測って比べられる（Epic #631 の計測基準。Issue #632）
* `replay-fixture` で、旧形式と配信用ログの一致テストに使う戦闘のログを作れる（Issue #634）
* `fetch-log` で、本番の戦闘の解析用ログ（GCS）を取得し、`/dev/sim` でファジィスコア付きで再生できる（Issue #637）
* `fetch --mission` で作戦（友軍・敵機・ロール・小隊・撤退ポイント・作戦目標）をロスターに入れ、本番の作戦ルームと同じ手順で戦い、`/dev/sim` で撤退ポイントとロールを描いて再生できる（Issue #699）
* Admin Tool の `/local-sim` から `run` を実行し、世代の一覧・集計を確認できる（Issue #701）
* Admin Tool の `/local-sim` から `fetch` でロスターを作れる。プレイヤーは所有機から出撃機体を選ぶ（Issue #705）
* Admin Tool の `/local-sim/rosters/[name]` でロスターの機体・戦域・作戦の値を編集し、本番DBを変えずに別名のロスターとして保存できる（Issue #703）

### 今後の予定（Epic #608）

| Sub-Issue | 内容 |
|---|---|
| 1 | 本番バッチの戦闘実行処理を `app/services/` へ切り出す（Issue #609、実装済み。本ドキュメントの「[戦闘実行の共通モジュール](#戦闘実行の共通モジュール)」） |
| 2 | Read Only 接続と参加機体の取得 `fetch`（Issue #610、実装済み。本ドキュメントの「[fetch: 参加機体の取得](#fetch-参加機体の取得)」） |
| 3 | ロスターからの実行と世代管理 `run`（Issue #611、実装済み。本ドキュメントの「[run: ロスターからの実行](#run-ロスターからの実行)」「[世代管理](#世代管理-list--pin--unpin)」） |
| 4 | 開発用バトルビューア `/dev/sim`（Issue #612、実装済み。本ドキュメントの「[/dev/sim: 開発用バトルビューア](#devsim-開発用バトルビューア)」） |
| 5 | 世代間の比較とバランス分析表示（Issue #613、実装済み。本ドキュメントの「[report / compare: 世代の集計と比較](#report--compare-世代の集計と比較)」「[世代の比較とAIの判断の表示](#devsim-世代の比較とaiの判断の表示)」） |
| 6 | エースパイロットの参加必須指定（Issue #614） |
| 7 | 作戦の戦闘の実行と再生（Issue #699、実装済み。本ドキュメントの「[作戦の戦闘](#作戦の戦闘)」） |

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
| `seed_battle_rngs(seed)` | 戦闘で使う乱数をすべて固定する（[再現性](#再現性)）。本番バッチは呼ばない |

`BattleOutcome` は `simulator`・`player_win`・`kills`（プレイヤー機自身の撃墜数）・`steps_used` を持つ。

### 本番バッチとの役割分担

| 処理 | 置き場所 |
|---|---|
| 環境変数 `MAX_SIMULATION_STEPS` の読み込み | `run_batch.py`（既定値は `battle_execution.DEFAULT_MAX_STEPS`） |
| 戦域の条件（`TheaterService.battle_conditions()`） | `run_batch.py`（DB を読むため） |
| バトルログ・`BattleResult` の保存、報酬・戦利品・NPC 成長 | `run_batch.py` の `_save_battle_results()` |
| 作戦の友軍・敵機・配置・目標の組み立て（`build_mission_battle()`）と、作戦の結果のカラム（`objective_result_fields()`・`WIN_LOSS_BY_OBJECTIVE_STATUS`） | `app/services/mission_battle.py`。本番バッチとローカルシミュレータの両方が呼ぶ（Issue #699 で `run_batch._objective_fields()` を移した） |

### 注意点

* `snapshot_to_mobile_suit()` は渡した dict の位置・速度・武器・ID をモデルの型に書き換える。
  本番バッチはこの書き換え後の dict を `BattleResult.ms_snapshot` に保存するため、挙動を変えずに残している。
  元の dict を残したい呼び出し元はコピーを渡す
* `run_battle()` は渡したユニットの HP 等を戦闘後の状態に書き換える。`BattleResult` では
  `player_info` にエントリー時点の機体、`enemies_info` に戦闘後のユニットを入れる
* CI のエンジンスモークテスト（`scripts/simulation/engine_ci_smoke.py`）は合成ユニットで `BattleSimulator` を
  直接回しており、このモジュールを通らない。`dt` を変えて回すため、本 Issue では置き換えていない

---

## 準備: Read Only の接続

### 1. SELECT 権限だけのロールを作る（オーナー作業）

Neon の Console / API / CLI で作ったロールには `neon_superuser` が付く。SQL で作ること。

```sql
CREATE ROLE msbs_readonly WITH LOGIN PASSWORD '...';
GRANT CONNECT ON DATABASE <db名> TO msbs_readonly;
GRANT USAGE ON SCHEMA public TO msbs_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO msbs_readonly;
-- 今後 Alembic で追加されるテーブルにも SELECT を付ける（<owner> はマイグレーションを実行するロール）
ALTER DEFAULT PRIVILEGES FOR ROLE <owner> IN SCHEMA public GRANT SELECT ON TABLES TO msbs_readonly;
```

### 2. 接続文字列を設定する

`backend/.env` に `NEON_READONLY_DATABASE_URL` を書く（`backend/.env.example` 参照）。

* 未設定ならエラーで終了する。`NEON_DATABASE_URL` にはフォールバックしない
* 接続時に `options` へ `-c default_transaction_read_only=on` を足す。Neon の `options=endpoint%3D...` は残す

### 3. 書き込みが拒否されることを確かめる

```bash
cd backend
python -m scripts.simulation.local_sim check-readonly
```

次の2つを試し、両方とも拒否されれば終了コード 0 になる。

| 確認 | 期待するエラー |
|---|---|
| `UPDATE pilots ... WHERE false`（既定の Read Only トランザクション） | `25006 cannot execute UPDATE in a read-only transaction` |
| `SET TRANSACTION READ WRITE` で Read Only を外した後の `INSERT INTO pilots SELECT ... WHERE false` | `42501 permission denied for table pilots` |

`default_transaction_read_only` はセッション側で外せる。そのため、ロールの権限で拒否されることも確かめる。
どの文も `WHERE false` で0行を対象にし、最後にロールバックする。防御が効いていなくてもデータは変わらない。

### 仕組み

`app/db.py` は import 時に `NEON_DATABASE_URL` を読んでエンジンを作る。
`readonly_db.use_readonly_database()` は、`app` を import する前に `NEON_DATABASE_URL` を Read Only の接続文字列で上書きする。
`app/core/gamedata.py`（エースのマスター読み込み）など `app.db.engine` を直接使う箇所も、同じ Read Only のエンジンを使う。

* `app.db` が先に import されていたら、書き込み可能なエンジンが残っているためエラーで終了する
* 接続後に `SHOW transaction_read_only` が `on` であることを確かめてから処理を始める
* 取得中のセッションは `autoflush=False` で作り、コミットしない。最後にロールバックする

---

## fetch: 参加機体の取得

```bash
cd backend
python -m scripts.simulation.local_sim fetch --pilot user_xxx --npc 7
python -m scripts.simulation.local_sim fetch --ms <機体ID>:A --ms <機体ID>:A --ace 1 --npc 4
python -m scripts.simulation.local_sim fetch --pilot user_xxx --npc 9 --theater solomon --minovsky 0.6 --name solomon_test
```

| オプション | 説明 |
|---|---|
| `--ms <機体ID>[:<チーム>]` | 指定した機体を参加させる（複数指定可） |
| `--pilot <パイロットID>[:<チーム>]` | パイロットの出撃機体（`active_mobile_suit_id`）を参加させる。ID は `pilots.id` か `user_id`（複数指定可）。プレイヤーの出撃機体はエントリーごとに選ぶため `active_mobile_suit_id` が未設定のことがある。その場合はエラーになるので `--ms` で機体を直接指定する（戦域ごとにビルドが異なるため、所有機の先頭へのフォールバックはしない）。Admin Tool ではプレイヤーを選ぶと所有機の一覧が出るので、そこから選ぶ（[ロスター作成](#ロスター作成fetchissue-705)） |
| `--npc N` | 本番の永続化NPCから N 機を選ぶ。足りない分は本番と同様に NPC を生成して補う |
| `--ace N` | エースパイロットをランダムに N 機参加させる。同じエースは重ねない |
| `--ace-id <エースID>` | 必ず参加させるエース（複数指定可）。`--ace N` と併用すると、指定したエースを含めて N 機にする。存在しない ID と重複はエラー（Issue #702、#614） |
| `--theater <戦域ID>` | 戦域。省略すると戦域なし（宇宙） |
| `--minovsky <0〜1>` | ミノフスキー濃度。省略すると戦域の `base_minovsky`（戦域なしなら 0） |
| `--mission <作戦ID>` | 本番の作戦マスター（`missions`）で戦う。[作戦の戦闘](#作戦の戦闘)を参照 |
| `--mission-builder <名前>` | 本番に反映する前の作戦を、リポジトリの定義から作る（`retreat_support`）。`--mission` とは併用できない |
| `--name <名前>` | ロスター名。省略すると日時（例: `20261005-213000`） |
| `--force` | 同名のロスターを上書きする |

参加機体が2機未満のときはエラーにする（作戦では1機以上）。

### 機体の選び方とスナップショット

スナップショットは本番と同じ関数で作る。

| 取得元 | 選び方 | スナップショット |
|---|---|---|
| `--ms` / `--pilot`（プレイヤー） | 指定どおり | エントリー登録と同じ。`WeaponService.resync_mobile_suit_weapons()` の後に `MobileSuitService.build_entry_snapshot()`（地形適正は機体マスターの値） |
| `--ms` / `--pilot`（NPC のパイロット） | 指定どおり。出撃機体が未設定なら所有機の先頭 | マッチングと同じ `build_npc_entry_snapshot()`（`npc_pilot_level` 付き）。初期位置をランダムにし、HP を全快にする |
| `--npc` | `MatchingService.choose_npcs()`。本番の `select_npcs_for_room()` と同じ選び方で、出撃機体を保存しない | 同上。ロスターに入っている機体は選ばない |
| `--npc` の不足分 | `MatchingService._create_npc_mobile_suit()` で生成 | 同上（レベル1） |
| `--ace` / `--ace-id` | `--ace-id` のエースを先に入れ、`--ace` の残りをエースのマスターから重複なしでランダムに選ぶ | `MatchingService.build_ace_mobile_suit()` で作り、`build_npc_entry_snapshot()` |

* チームを付けた機体は、スナップショットの `team_id` にチーム名を入れ、`side` を `PLAYER` にする（本番のチームエントリーと同じ）
* チームを付けない機体と NPC・エースは `team_id` が `null`。本番と同様に個人戦扱い（実行時に `team_id` = 機体ID）
* 生成した NPC・エースの機体ID は本番DBに無い

### ロスターの形式

保存先は `battle_logs/local_sim/rosters/<名前>.json`（gitignore 済み）。世代管理（Sub-Issue 3）の対象外。
手で編集して条件を変えられるよう、整形した JSON で保存する。
スキーマは `backend/scripts/simulation/local_sim/roster.py` の Pydantic モデル（`Roster`）。

```json
{
  "schema_version": 3,
  "name": "solomon_test",
  "fetched_at": "2026-10-05T12:30:00Z",
  "conditions": {
    "theater_id": "solomon",
    "environment": "SPACE",
    "environment_profile": { "environment_id": "SPACE", "sensor_range_multiplier": 1.0, "...": "..." },
    "theater_name": "ソロモン宙域",
    "environment_name": "宇宙",
    "viewer_preset": "SPACE",
    "minovsky_density": 0.6,
    "battlefield": { "obstacles": [], "spawn_zones": [], "obstacle_density": "MEDIUM" }
  },
  "entries": [
    {
      "source": {
        "kind": "pilot",
        "mobile_suit_id": "…",
        "pilot_id": "…",
        "pilot_name": "…",
        "ace_id": null
      },
      "is_npc": false,
      "snapshot": { "name": "Zaku II", "team_id": null, "...": "BattleEntry.mobile_suit_snapshot と同じ" }
    }
  ],
  "ace_pilots": [ { "id": "ace_char_aznable", "mobile_suit": { "...": "..." }, "skills": { "flanking": 3 } } ],
  "master_mobile_suits": [],
  "mission": null
}
```

| 項目 | 内容 |
|---|---|
| `conditions` | `TheaterService.battle_conditions()` で解決した戦域条件（`BattleConditions` と同じ項目） |
| `conditions.theater_name` / `environment_name` / `viewer_preset` | 戦域・環境タイプの表示名とビューアの背景プリセット。`run` は DB を読まないため、結果に載せる値を取得時に保存する |
| `entries[].source.kind` | `mobile_suit` / `pilot` / `npc` / `generated_npc` / `ace` |
| `entries[].snapshot` | 本番の `BattleEntry.mobile_suit_snapshot` と同じ形式 |
| `ace_pilots` | 参加エースと、作戦に置いたエースの `ace_pilots` マスター。エンジンは戦闘中に `get_ace_pilot_by_id()` でエースのスキルを読むため、`run` はこの値を使って DB を読まずに実行する |
| `master_mobile_suits` | 作戦の機体が参照する `master_mobile_suits`（`created_at` / `updated_at` を除く）。武器の `master_weapon_id` は書き込み済み。`run` はこの値から作戦の機体を作る。`schema_version` 2 以前のロスターは空として読む |
| `mission` | 作戦（[作戦の戦闘](#作戦の戦闘)）。`null` なら `entries` の機体だけで戦う。`schema_version` 1 のロスターは作戦なしとして読む |

### 本番マッチングとの共通化

`MatchingService` から DB に書かない部分を切り出し、本番とローカルシミュレータの両方から呼ぶ。本番の挙動は変えない。

| 関数 | 内容 |
|---|---|
| `MatchingService.choose_npcs()` | 永続化NPCをランダムに選ぶ。DB に書かない。`select_npcs_for_room()` はこれを呼んでから出撃機体を保存する |
| `MatchingService.build_ace_mobile_suit()` | エースのマスター1件から出撃機体を作る。`_create_ace_pilot()` はこれをランダムな1件で呼ぶ |
| `build_npc_entry_snapshot()` | NPC・エースのエントリー用スナップショット |
| `reset_npc_for_battle()` | 永続化NPCの機体を出撃前の状態（ランダムな初期位置・HP全快）に戻す |

### 検証

* `tests/unit/test_local_sim_fetch.py`: 機体の選択、DB に書かないこと、戦域条件、ロスターの保存、Read Only の接続文字列
* ローカルの PostgreSQL に上記の SQL で SELECT 権限だけのロールを作り、`check-readonly` で2つの書き込みが拒否されることと、`fetch` の前後で全テーブルの内容（`pg_dump`）と `pg_stat_user_tables` の書き込み件数が変わらないことを確認した

---

## run: ロスターからの実行

```bash
cd backend
python -m scripts.simulation.local_sim run --roster solomon_test --rounds 20
python -m scripts.simulation.local_sim run --roster solomon_test --rounds 20 --seed 611 --label before
python -m scripts.simulation.local_sim run --roster ../battle_logs/local_sim/rosters/edited.json --pin
```

| オプション | 説明 |
|---|---|
| `--roster <名前>` | ロスター名、またはロスターの JSON ファイルのパス（必須） |
| `--rounds N` | 戦闘数（既定 1） |
| `--steps N` | 1戦の最大ステップ数。既定は本番バッチと同じ `battle_execution.DEFAULT_MAX_STEPS`（3000 = 300秒） |
| `--seed N` | 1戦目のシード。N 戦目は `seed + N - 1`。省略するとランダムに決め、`manifest.json` に記録する |
| `--label <名前>` | 世代の名前。ディレクトリ名と一覧に使う。省略するとロスター名 |
| `--pin` | 保存する世代を最初からピン留めする |

### 戦闘の組み立て

戦闘は本番バッチと同じ `battle_execution` の関数で行う。

* 勝敗と撃墜数を判定する機体（以下「判定する機体」）は、`is_npc` が `false` の先頭の機体。全機が NPC なら先頭の機体。本番の `player_entries[0]` と同じ選び方
* 判定する機体を `prepare_battle_units()` のプレイヤー機にし、残りを敵機にする。チームは `team_id` で決まる
* 勝敗は判定する機体のチームが生き残ったか。最大ステップ数で打ち切ったときも、生き残っていれば `WIN`（本番と同じ）
* スナップショットは戦闘ごとにコピーしてから渡す（`snapshot_to_mobile_suit()` が dict を書き換えるため）
* ロスターに作戦があれば、作戦ルームと同じ手順で戦い、勝敗を作戦の結果で決める（[作戦の戦闘](#作戦の戦闘)）

### DB に接続しない仕組み

* CLI は `app` 配下を import する前に `run.forbid_database()` を呼び、`app.db` を「参照するとエラーになるモジュール」に差し替える。
  `backend/.env` に `NEON_DATABASE_URL` があっても接続しない
* エンジンは戦闘中に `get_ace_pilot_by_id()` でエースのスキルを読む。`run` はロスターの `ace_pilots` を
  `gamedata.use_static_ace_pilots()` で渡し、DB を読まずに返す。実行後は DB 参照に戻す
* 戦域名・環境名はロスターの `conditions` から読む。ロスターに無ければ、戦域名は戦域IDにする

### 再現性

`seed_battle_rngs(seed)` を各戦闘の前に呼び、エンジンが使う次の3つの乱数を固定する。

| 乱数 | 使う処理 |
|---|---|
| `random`（グローバル） | 命中・クリティカル・ダメージ乱数・格闘コンボなど |
| `combat._part_hit_rng` | 被弾部位の選択 |
| `app/engine/rng.py` の `new_numpy_rng()` | スポーン位置・障害物の配置・初速 |

`np.random.default_rng()` は `np.random.seed()` で固定できない。そのため、エンジンは numpy の生成器を `new_numpy_rng()` で作る。
`seed_numpy_rngs()` でシードを固定すると、作るたびに固定したシードから派生した系列を返す。
固定しなければ毎回シードなしで作るため、本番の挙動は変わらない。

* N 戦目の結果は `seed + N - 1` だけで決まり、前の戦闘に左右されない（`--seed 612` の1戦目と `--seed 611 --rounds 2` の2戦目は一致する）
* 別プロセス・別の `PYTHONHASHSEED` で実行しても、`battle_NNN.json` はバイト単位で一致することを確認した
* チームの戦略コントローラ（`BattleSimulator._strategy_controllers`）はユニットの順に並ぶ。
  以前は `set` から作っていたため、同じステップで複数のチームの戦略が変わると、`STRATEGY_CHANGED` の行の順序が
  `PYTHONHASHSEED` で変わった（チームが多い50機の個人戦で起きる。行の中身と戦闘の結果は変わらない）
* コード・ファジィルールが変われば結果も変わる。`manifest.json` の `git` と `fuzzy_rules_hash` で実行時の状態を確かめる

### 保存形式

```text
battle_logs/local_sim/
  rosters/                         # fetch のロスター（世代管理の対象外）
  generations/
    20261005-213000_<label>/       # 1世代 = 1回の run
      manifest.json                # 実行条件・再現情報・勝敗サマリー・ピン留め状態
      report.json                  # 集計値（report / compare・/dev/sim の比較画面が読む）
      roster.json                  # 実行時のロスターのコピー（ファイルをそのままコピー）
      battle_001.json              # 1戦分
      battle_002.json
```

* スキーマは `backend/scripts/simulation/local_sim/generations.py` の Pydantic モデル（`Manifest` / `BattleRecord`）。Sub-Issue 4 のビューアはこれで読む
* 世代は一時ディレクトリ（`.tmp-<世代ID>`）に書き、全部書けてから世代ディレクトリへ移す。途中で失敗した世代は残らない
* 同じ秒・同じラベルの世代があれば、ディレクトリ名に `-2` などを付ける

#### manifest.json

```json
{
  "schema_version": 1,
  "generation_id": "20261005-213000_before",
  "label": "before",
  "created_at": "2026-10-05T21:30:00+09:00",
  "pinned": false,
  "roster_name": "solomon_test",
  "roster_file": "roster.json",
  "player_entry_index": 0,
  "player_name": "Zaku II",
  "seed": 611,
  "rounds": 20,
  "max_steps": 3000,
  "git": { "commit": "0be8a5d…", "dirty": true },
  "fuzzy_rules_hash": "ae1c1073…",
  "theater_id": "solomon",
  "environment": "SPACE",
  "minovsky_density": 0.35,
  "mission_id": null,
  "mission_name": null,
  "summary": { "battles": 20, "wins": 8, "losses": 12, "draws": 0, "timeouts": 1, "total_kills": 15 },
  "battles": [
    { "index": 1, "file": "battle_001.json", "seed": 611, "win_loss": "LOSE", "kills": 2,
      "elapsed_time": 128.9, "steps_used": 1289, "timed_out": false }
  ]
}
```

| 項目 | 内容 |
|---|---|
| `player_entry_index` / `player_name` | 判定する機体の、ロスターの `entries` での位置と機体名 |
| `seed` | 1戦目のシード。N 戦目は `seed + N - 1`（`battles[].seed`） |
| `git.commit` / `git.dirty` | 実行時の HEAD と、未コミットの変更（未追跡のファイルを含む）の有無。git が無ければ `null` |
| `fuzzy_rules_hash` | `backend/data/fuzzy_rules/` の全ファイルの相対パスと中身から作った SHA-256 |
| `summary` | 戦闘数・勝ち・負け・引き分け（作戦だけ）・打ち切り（`timed_out`）の数・判定する機体の撃墜数の合計 |
| `mission_id` / `mission_name` | 作戦の ID と名前。作戦の無い世代は `null` |
| `battles[].timed_out` | 最大ステップ数で打ち切ったか |

#### battle_NNN.json

本番の `BattleResult` の表示用の項目と、ログを持つ。

| 項目 | 内容 |
|---|---|
| `index` / `seed` | 戦闘番号（1 始まり）とシード |
| `win_loss` / `kills` | 判定する機体の勝敗（`WIN` / `LOSE`。作戦では `DRAW` もある）と撃墜数 |
| `elapsed_time` / `steps_used` / `timed_out` | 戦闘の経過時間（秒）・使ったステップ数・打ち切ったか |
| `environment` / `theater_id` / `theater_name` / `environment_name` / `viewer_preset` / `minovsky_density` | 戦域条件と表示名 |
| `player_info` | エントリー時点の判定する機体（本番と同じく戦闘前の状態） |
| `enemies_info` | 判定する機体以外の全ユニット（戦闘後の状態） |
| `obstacles_info` / `map_bounds` | 障害物と、戦闘終了時のフィールド範囲 |
| `part_hit_summary` / `weapon_accuracy_summary` / `detection_summary` | 結果画面の戦果サマリー。本番の `BattleResult` と同じ `compute_result_summary_fields()` で集計する。項目を足す前（Issue #633 より前）の世代では null |
| `mission_id` / `mission_name` / `objective_status` / `objective_progress` / `objective_required` / `objective_detail` | 作戦の結果。本番の `BattleResult` と同じ項目・同じ関数（`objective_result_fields()`）で作る。作戦の無い戦闘と、項目を足す前（Issue #699 より前）の世代では null |
| `logs` | `BattleLog` の一覧。`strip_debug_fields()` を通さず、`fuzzy_scores` などのデバッグ項目を残す |

1戦のサイズはログの行数に比例する。5機・約1300ステップの戦闘で約1.5万行・約14MB だった
（Issue の見積もりの 650KB は 601行の `battle_logs/sample.json` の値）。
20戦×5世代では 1GB を超えうるため、不要な世代は消すかピン留めを外す。
ログはインデントを付けずに保存し、`manifest.json` だけ整形する。

---

## 作戦の戦闘

作戦（`missions`）の戦闘を、本番バッチの作戦ルームと同じ手順でローカル実行し、`/dev/sim` で再生する（Issue #699）。
小隊の陣形（#688）や支援ターゲット選択（#689）など、ロールと小隊で動きが変わる機能を本番と同じ画面で確かめ、
作戦マスター（敵の編成・配置・小隊）の調整を本番に反映する前に試すために使う。

```bash
cd backend
# 本番の作戦マスター（撤退支援は作戦ID 4）
python -m scripts.simulation.local_sim fetch --pilot user_xxx --mission 4 --name retreat
# 本番に反映する前の作戦（リポジトリの build_retreat_support_mission()）
python -m scripts.simulation.local_sim fetch --pilot user_xxx --mission-builder retreat_support --name retreat_dev
python -m scripts.simulation.local_sim run --roster retreat --rounds 20 --seed 1
python -m scripts.simulation.local_sim report retreat
```

### fetch

* `--mission <作戦ID>` は本番の作戦マスターを Read Only の接続で読む。`--mission-builder <名前>` は DB の `missions` を読まず、
  `fetch.MISSION_BUILDERS` に登録したリポジトリの定義で作る（プレイヤー機の取得には DB を使う）
* 本番の作戦ルームと同じく、参加機体は `--ms` / `--pilot` のプレイヤー機だけ。`--npc` / `--ace` / `--ace-id`、チームの指定（`:<チーム>`）はエラーにする。
  プレイヤー機は全員、先頭のプレイヤー機のチームに入る
* 戦域を指定しないときは、作戦の環境（`missions.environment`）で戦う。戦域を指定したときは戦域の環境（本番と同じ）
* 作戦はロスターの `mission` に保存する。友軍・敵機の機体は `run` で作戦マスターから組み立てる
* 作戦の機体が参照する機体マスターとエース（[retreat-support-mission.md](retreat-support-mission.md#機体マスターエースの参照issue-719)）は、
  `load_mission_masters()` で読んでロスターの `master_mobile_suits` / `ace_pilots` に保存する。参照先が無い作戦はエラーにする

```json
"mission": {
  "source": "builder",
  "builder": "retreat_support",
  "master": {
    "id": 4, "name": "撤退支援", "environment": "SPACE",
    "enemy_config": { "enemies": [ { "master_mobile_suit_id": "zaku_ii", "name": "追撃前衛機 #1", "role": "VANGUARD", "squad_id": "pursuit-1" } ] },
    "allies_config": [ { "master_mobile_suit_id": "gm", "name": "撤退機 #1", "current_hp_ratio": 0.4, "role": "WITHDRAW", "...": "..." } ],
    "objective": { "type": "RETREAT_SUPPORT", "params": { "required": 2 } },
    "layout": { "spawn_zones": [ "..." ], "retreat_points": [ "..." ] }
  }
}
```

| 項目 | 内容 |
|---|---|
| `source` | `production`（本番の作戦マスター）か `builder`（リポジトリの定義） |
| `builder` | `source` が `builder` のときの定義の名前 |
| `master` | `Mission` の `model_dump()`。手で編集すると、友軍・敵機・ロール・小隊・配置・作戦目標を変えて試せる |

### run

本番バッチの作戦ルーム（`run_batch._process_room()` の `room.mission_id` の分岐）と同じ手順で戦う。

1. `prepare_battle_units()` で判定する機体と他のプレイヤー機を組み立て、他のプレイヤー機の `side` を `PLAYER` にする
2. `build_mission_battle()` で友軍・敵機・スポーン領域・撤退ポイント・ロールと小隊・作戦目標を組み立てる。参照先の機体マスターとエースは、ロスターの `master_mobile_suits` / `ace_pilots` から渡す（`roster_mission_masters()`）
3. `run_battle(objective=..., retreat_points=..., unit_assignments=..., suppression=...)` で戦う。射撃の制圧（`battle-engine-feature.md` 40 章）は本番と同じく作戦の係数（`MissionBattleSetup.suppression`）で有効になる
4. 勝敗は判定する機体のチームから見た作戦の結果（`SUCCESS` / `FAILURE` / `DRAW` → `WIN` / `LOSE` / `DRAW`）。作戦の結果のカラムは本番と同じ `objective_result_fields()` で作る

* 友軍機は `enemies_info` に入るが、`side` が `PLAYER` のため BattleViewer では味方として描かれる
* 友軍・敵機の ID は `build_mission_battle(unit_id_namespace=...)` で、作戦マスターでの位置から決める（本番は省略してランダム）。
  戦闘ごとに ID が変わると、`report` の機体ごとの集計が戦闘の数だけ分かれるため
* 作戦の無いロスターは今までどおり戦う。main と同じロスター・同じシードで `battle_NNN.json` のログが一致することを確認した（違いは `schema_version` だけ）
* 1戦ごとの表示に離脱数を足した（例: `[1/10] seed=1 WIN 撃墜 2 / 11.0s / 離脱 2/3`）

### report / compare

作戦の世代では、`report` に作戦の成功率と離脱した友軍の数を出す。

```text
作戦（撤退支援）:
  成功      9 回  90.0%
  失敗      1 回  10.0%
  引き分け  0 回   0.0%
離脱した友軍: 平均 2.50 / 3 機（成功に必要 2 機） / 撃破された友軍: 平均 0.50 機
  離脱 1/3  1 回  10.0%
  離脱 2/3  3 回  30.0%
  離脱 3/3  6 回  60.0%
```

`compare` と `/dev/sim` の世代の比較は、作戦成功率・離脱した友軍/戦・撃破された友軍/戦の差を出す。

### /dev/sim

* `localSimBattleToResult()` が `mission_id` と作戦の結果（`objective_*`）を `BattleResult` に移す。
  `BattleReplayPanel` が `objective_detail` の `retreat_points` / `unit_roles` を BattleViewer に渡し、撤退ポイントと友軍（撤退中）を描く
* `SimReplay` のヘッダーに作戦名（`撤退支援 · <ラベル> #<戦闘番号>`）と、作戦の結果（作戦成功・離脱 2/3（必要 2）・撃破された友軍）を出す。
  表示は本番の戦歴一覧と同じ `getObjectiveSummary()` / `OBJECTIVE_STATUS_LABELS` を使う
* 世代の一覧に作戦名、バトルの一覧に `DRAW`（黄）を出す
* `fetch-log` で本番の作戦ルームの戦闘を取り込んだときも、作戦の結果と作戦名を引き継ぐ（`DRAW` も取り込める）

### 検証（作戦の戦闘）

* `tests/unit/test_local_sim_fetch.py`: 作戦の保存（リポジトリの定義・本番の作戦マスター）、作戦の環境、NPC・エース・チームの指定の拒否、`schema_version` 1 のロスターの読み込み、参照先の機体マスター・エースの保存、参照先が無い作戦の拒否
* `tests/unit/test_local_sim_run.py`: 作戦の戦闘（友軍・敵機・撤退ポイント・ロール・勝敗の対応）、同じシードでの再現、ロスターの作戦マスターの手での編集、ロスターに保存した機体マスター・エースから DB なしで作ること、作戦の無いロスター
* `tests/unit/test_local_sim_analysis.py`: 作戦の成功率・離脱数の集計とテキスト表示、比較の差
* `tests/unit/test_mission_battle.py`: `unit_id_namespace` による ID の固定
* `frontend/tests/unit/localSimAnalysis.test.ts`: 比較表の作戦の行、`localSimBattleToResult()` の作戦の結果
* 本番の機体1機（Hambrabi）と `retreat_support` の作戦で `run --rounds 10` を実行し（9 勝 1 敗）、`/dev/sim` で撤退ポイント・友軍のリング・作戦の結果が表示されることを確認した。
  追撃部隊の狙撃機は、射撃時に標的から最も近い格闘機より 100〜200m 遠い位置にいた（#688 の陣形）

---

## ロスターの編集: roster-save（Issue #703）

調整したい値（機体の HP・装甲・機動性・武装、戦域の条件、作戦の敵の編成）を、本番DBのマスターに書かずに試す。
ロスターを編集して別名で保存し、元のロスターと同じシードで `run` して、世代の比較で効果を確かめる。
確かめた値を本番に反映するときは、今までどおり Admin Tool のマスター編集で行う（本機能の対象外）。

### CLI

```bash
cd backend
python -m scripts.simulation.local_sim roster-save --name <名前> [--force] < roster.json
```

| オプション | 説明 |
|---|---|
| `--name <名前>` | 保存するロスター名。標準入力の JSON の `name` は無視してこの名前にする |
| `--force` | 同名のロスターを上書きする。既定では上書きしない |

標準入力のロスターを `Roster`（Pydantic）で検証してから保存する。形式が合わない、またはロスター名が使えないときは、保存せず終了コード 1 で終わる。
Admin Tool に形式の定義を重ねて書かないため、形式のチェックはこの CLI に任せている。保存は DB に接続しない。

### Admin Tool

`/local-sim` の「実行」でロスターを選び、「このロスターを編集」から `/local-sim/rosters/[name]` を開く。

| 区分 | 編集できる項目 |
|---|---|
| 機体（`entries[].snapshot`） | HP・装甲・機動性・索敵範囲・耐性・EN・適性/補正・戦術・欠損部位・武器スロット数・武装・地形適正。機体の複製・取り外し |
| 戦域の条件（`conditions`） | 環境（環境タイプの効果の写しも取り替える）・ミノフスキー濃度・障害物の密度 |
| 作戦（`mission.master`） | 友軍・敵機の機体名・HP・装甲・機動性・ロール・小隊・武器の威力/射程/命中率、機体の複製・取り外し、作戦目標の必要数（`params.required`）。機体マスター・エースを参照する機体は、参照先を表示し、表示名・開始時の HP の割合・ロール・小隊を変える（性能は `master_mobile_suits` / `ace_pilots` の JSON を手で直す） |

* 機体の入力欄は NPC 機・エース機の編集と同じ部品（`MobileSuitSpecSection`・`WeaponListSection`・`TerrainAdaptabilityFields`）と同じ検証（武装数はスロット数以下・武器 ID の重複なし）を使う。
  フォームで扱わない項目（位置・`team_id`・武器の `weapon_type` など）は元の値を引き継ぐ（`mergeWeaponSources()` と同じ考え方）。
  最大 HP を変えると現在 HP も揃える
* フォームを通しても値が変わらなかった機体は、元のスナップショットをそのまま保存する（狙う部位配分の丸めなどを変更として扱わない）
* 元のロスターから変えた値は、琥珀色の枠と「元: …」で強調する。機体ごとに変更点の一覧も出す。複製した機体は「追加した機体」として扱う
* 「名前を付けて保存」は既定で `<元の名前>-edit` に保存する。同名があると 409 になり、「上書きする」にチェックを入れたときだけ上書きする
* 入力が不正なとき（赤い項目、ミノフスキー濃度が 0〜1 の外、作戦の機体の値が数でない）は保存を押せない。最終的な形式のチェックは CLI の `Roster` が行う

### Route Handler

| ルート | 説明 |
|---|---|
| `GET /api/local-sim/rosters/{名前}` | ロスターの JSON を返す。無ければ 404 |
| `POST /api/local-sim/rosters/{名前}/save` | body `{ roster, force? }` を `roster-save` で `{名前}` として保存する。同名があり force でなければ 409、形式が不正なら 422 |

どちらも開発環境（`next dev`）でだけ動く。

### 比較の流れ

1. `/local-sim/rosters/<元>` で値を変えて `<元>-edit` に保存する
2. `/local-sim` で両方のロスターを同じシードで実行する（ラベルを分けると世代を見分けやすい）
3. `/dev/sim` で2つの世代を比較する（[世代の比較](#devsim-世代の比較とaiの判断の表示)）

### 検証（roster-save）

* `backend/tests/unit/test_local_sim_roster_save.py`: 名前の付け替え、`--force` なしでは上書きしないこと、形式・ロスター名が不正なときは保存しないこと
* `admin-tool/tests/unit/rosterEdit.test.ts`: フォーム値とスナップショットの変換（引き継ぎ・最大 HP・狙う部位配分）、変更点の比較、機体の複製

---

## 世代管理: list / pin / unpin

```bash
cd backend
python -m scripts.simulation.local_sim list
python -m scripts.simulation.local_sim pin before
python -m scripts.simulation.local_sim unpin 20261005-2130
```

* `run` の保存後、ピン留めしていない世代が5つを超えたら古い順に削除する（`generations.KEEP_UNPINNED_GENERATIONS`）
* ピン留めした世代は5世代の数に含めず、削除しない。`run --pin` で最初からピン留めできる
* `pin` / `unpin` の引数は世代ID、その前方一致、またはラベル。複数の世代に該当するとエラーにする
* ピン留めを外した世代は、次の `run` で新しい5世代に入らなければ削除される
* `list` は世代を古い順に、世代ID・出どころ（`local` / `本番`）・日時・ラベル・戦闘数・勝敗・ピン留め（行頭の `*`）で表示する
* `manifest.json` が無いディレクトリと一時ディレクトリは、一覧にも削除の対象にもならない

### 検証（run）

* `tests/unit/test_local_sim_run.py`: 保存する内容、同じシードでのログの一致、戦闘ごとの独立性、DB を参照しないこと、失敗時に世代を残さないこと、6回目の実行での削除とピン留め、`pin` / `unpin`
* SQLite のテストDBで作ったロスターを、`NEON_READONLY_DATABASE_URL` を外した状態で `run --seed 611 --rounds 2` を2回（`PYTHONHASHSEED` を変えて）実行し、`battle_001.json`・`battle_002.json` が一致することを確認した

---

## report / compare: 世代の集計と比較

```bash
cd backend
python -m scripts.simulation.local_sim report before
python -m scripts.simulation.local_sim compare before after
python -m scripts.simulation.local_sim compare 20261005-2130 after --format json
```

| サブコマンド | 内容 |
|---|---|
| `report <世代>` | 世代の全戦闘を集計して表示し、世代ディレクトリの `report.json` に保存する（作り直す） |
| `compare <世代A> <世代B>` | 2つの世代の集計値を並べ、差（B − A）を表示する。`report.json` が無いか古い形式の世代は、集計して保存してから比べる |

* 世代の指定は `pin` と同じ（世代ID・その前方一致・ラベル）
* `--format json` で集計値を JSON で出す（`compare` は `{"a": …, "b": …}`）
* DB には接続しない（`run` と同じく `forbid_database()` を呼ぶ）
* `run` は保存時に `report.json` も書く。`report` が要るのは、この機能より前に作った世代か、集計の形式（`REPORT_SCHEMA_VERSION`）が変わったときだけ

### 集計する項目

実装は `backend/scripts/simulation/local_sim/analysis.py`（`GenerationAnalyzer`）。1戦ずつ積算し、戦闘を全部メモリに持たない。

| 項目 | 内容 |
|---|---|
| 勝敗 | 判定する機体の勝ち・負け・引き分け（作戦だけ）の数と勝率 |
| 作戦 | 作戦の成功・失敗・引き分けの数と成功率、離脱した友軍・撃破された友軍の数（平均）と離脱数ごとの戦闘の数（作戦の世代だけ） |
| 打ち切り | 最大ステップ数で打ち切った戦闘の数と割合 |
| 戦闘時間 | 経過時間（秒）の平均・最短・最長 |
| 判定する機体の撃墜数 | 合計と1戦あたり |
| 行動分布 | 全ユニットの `ATTACK`・`MOVE`・`USE_SKILL`・`RETREAT`・`MISS`・`DAMAGE`・`DESTROYED` の回数と割合 |
| 戦略遷移 | `STRATEGY_CHANGED` の `前 → 後` ごとの回数 |
| 武器の使用回数 | `ATTACK` の武器名ごとの回数（`report.json` だけに入れる） |
| 機体ごとの撃墜数 / 被撃墜数 | 機体 ID ごとの合計。撃墜した機体は `battle_digest.compute_unit_kills()` と同じく、`DESTROYED` の直前にある同じ対象への `ATTACK` / `MELEE_COMBO` の機体とする |
| 警告 | 下記の異常検出 |

`compare` は戦闘数が違っても比べられるよう、回数を1戦あたりか割合で並べる。
機体は ID で対応させる。片方の世代にしかいない機体（ロスターが違うとき）は `-` になる。
実行条件（ロスター・判定する機体・シード・最大ステップ数・コミット・ファジィルールのハッシュ・戦域・作戦）も並べ、違う項目に `≠` を付ける。
どちらかの世代に作戦があれば、作戦成功率・離脱した友軍/戦・撃破された友軍/戦も並べる。

### 異常検出

`run_simulation.py bench` と同じ `sim_bench.balance_warnings()` で、同じ閾値（`backend/app/engine/constants.py` の `BALANCE_WARN_*`）を使う。

| 条件 | 閾値 | ローカルシミュレータでの読み替え |
|---|---|---|
| 引き分け率が高い | `BALANCE_WARN_DRAW_RATE` | 打ち切り率。bench の引き分けは最大ステップ到達のため、打ち切りを同じ扱いにする |
| 一方の勝率が高い | `BALANCE_WARN_WIN_RATE` | 判定する機体の勝率と、負けた割合（「相手側」の勝率）の両方を見る |
| 平均戦闘時間が長い | `BALANCE_WARN_AVG_DURATION` | そのまま |

### 出力例（compare）

```text
=== 世代比較 ===
  A: 20261005-222241_before (3 戦)
  B: 20261005-222250_after (3 戦)

条件（≠ は A と B で違う項目）:
                  A                                    B
  ロスター        run_test                             run_test
  seed            611                                  900                                  ≠
  ...

集計値:
                                      A        B  差 (B-A)
  勝率                             0.0%    33.3%   +33.3pt
  打ち切り率                       0.0%    33.3%   +33.3pt
  平均戦闘時間                    78.1s   171.4s    +93.3s
  撃墜数/戦                        0.33     0.67     +0.33
  行動: ATTACK                     1.2%     0.7%    -0.6pt
  ...

機体ごとの撃墜数 / 被撃墜率（* は判定する機体。片方にしかいない機体は -）:
  機体                          撃墜/戦 A     B     差  被撃墜率 A       B       差
  *Zaku II                           0.33  0.67  +0.33      100.0%   66.7%  -33.3pt
   Qubeley (Haman Karn)              2.67  1.00  -1.67        0.0%   33.3%  +33.3pt

⚠️  [A] 相手側 の勝率が高すぎます (100.0% > 80%): バランスが偏っている可能性があります
⚠️  [B] 打ち切り率が高すぎます (33.3% > 20%): 戦闘が長期化しすぎている可能性があります
```

### report.json

スキーマは `analysis.py` の Pydantic モデル（`GenerationReport`）。`/dev/sim` の比較画面はこのファイルを読む。

| 項目 | 内容 |
|---|---|
| `schema_version` | `REPORT_SCHEMA_VERSION`。集計の項目や計算を変えたら上げる。`compare` と `/dev/sim` は違う値のファイルを使わない |
| `battles` / `wins` / `losses` / `draws` / `timeouts` | 戦闘数・勝ち・負け・引き分け・打ち切り |
| `elapsed_time` | `{avg, min, max}`（秒） |
| `player_kills` | 判定する機体の撃墜数の合計 |
| `action_counts` / `strategy_transitions` / `weapon_usage` | 行動・戦略遷移・武器ごとの回数 |
| `units[]` | `unit_id`・`name`・`pilot_name`・`is_player`（判定する機体か）・`battles`・`kills`・`deaths`。ロスターの順で、判定する機体が先頭 |
| `objective` | 作戦の結果（`mission_name`・`battles`・`success`・`failure`・`draw`・`required`・`total`・`progress`・`lost`・`progress_counts`）。作戦の無い世代は `null` |
| `warnings` | 警告文 |

### 集計を CLI で行う理由

`/dev/sim` の比較画面は、Route Handler で `battle_NNN.json` を集計せず、CLI が書いた `report.json` を読む。

* 集計の実装を Python の1か所に保つ。TypeScript に同じ集計を書くと、CLI と画面の値がずれうる
* 1世代は数十〜数百MB になる。比較のたびに全戦闘を読み直さずに済む

### 検証（report / compare）

* `tests/unit/test_local_sim_analysis.py`: 撃墜した機体の判定、集計値、bench と同じ警告、`run` が保存する `report.json` と読み直した集計の一致、古い `report.json` の作り直し、テキスト表示
* SQLite のテストDBで作ったロスターで `run --rounds 3` を2回（シード違い）実行し、`report`・`compare` の出力を確認した

---

## /dev/sim: 開発用バトルビューア

`run` で保存した世代を、本番の履歴詳細と同じ部品でブラウザ再生する。開発環境（`npm run dev`）専用。

```bash
cd frontend
npm run dev
# http://localhost:3000/dev/sim を開く
```

1. 左の「世代」に世代が新しい順に並ぶ（ラベル・日時・戦闘数・勝敗・撃墜数・ロスター名・コミット。ピン留めは 📌）
2. 世代を選ぶと「バトル」に戦闘の一覧が出る（戦闘番号・勝敗・経過時間・撃墜数・打ち切り・シード）
3. バトルを選ぶと右側で再生する

* 選んだ世代とバトルは URL（`/dev/sim?gen=<世代ID>&battle=<戦闘番号>`）に入る。再読み込みしても同じバトルを開く
* 世代が無いときは、`fetch` と `run` の実行方法を表示する
* 読み込み元は環境変数 `LOCAL_SIM_DIR`。省略するとリポジトリ直下の `battle_logs/local_sim`（`npm run dev` を動かす `frontend/` の親）。
  変えたときは `npm run dev` を起動し直す
* 世代の一覧は開いたときに1回だけ読む。新しく `run` した世代を出すにはページを再読み込みする

### 本番の履歴詳細との共通化

`BattleDetailModal` の再生部分を `frontend/src/components/history/BattleReplayPanel.tsx` に切り出した。
`BattleReplayPanel` はログと機体情報を props で受け取り、`BattleViewer`・`ChapterTrack`・`useBattleChapters`・`TurnController`・`BattleSummaryPanel` で描画する。
ヘッダーも履歴詳細と同じ `ModalHeader` を使う（✕ でバトルの選択を外す）。

| | 履歴詳細（`BattleDetailModal`） | `/dev/sim`（`SimReplay`） |
|---|---|---|
| バトルの情報 | API の `BattleResult` | `battle_NNN.json` を `localSimBattleToResult()` で `BattleResult` に変換 |
| ログ | `useBattleLogs()`（バックエンドの NDJSON） | `useLocalSimBattleLogs()`（Route Handler の NDJSON） |

どちらも `useNdjsonBattleLogs()` でログを段階的に読む。全件が届く前から再生でき、続きの読み込み中は表示が出る。
`battle_NNN.json` に無い項目（被攻撃回数・戦利品・ダイジェストなど本番のバッチで作る項目）は「—」か非表示になる。
戦果サマリーの集計（被弾部位・命中率・索敵）は `battle_NNN.json` の保存値を使い、本番と同じくログの到着前に表示する。
保存値が無い古い世代では、ログから計算する。

### Route Handler

`frontend/src/app/api/dev/sim/`。ファイルの読み込みは `_lib/localSimStore.ts` にまとめた。

| パス | 返す内容 |
|---|---|
| `GET /api/dev/sim/generations` | 読み込み元の絶対パスと、全世代の `manifest.json`（新しい順） |
| `GET /api/dev/sim/generations/{世代ID}/battles/{戦闘番号}` | `battle_NNN.json` のログ以外の項目と、ログの件数（`log_count`） |
| `GET /api/dev/sim/generations/{世代ID}/battles/{戦闘番号}/logs` | ログの NDJSON（本番の `/api/battles/{id}/logs` と同じ形式） |
| `GET /api/dev/sim/generations/{世代ID}/battles/{戦闘番号}/decisions?unit={機体ID}` | 1機の AI の判断ログ（`fuzzy_scores` か `strategy_mode` を持つログ）。項目は `timestamp`・`action_type`・`target_id`・`message`・`strategy_mode`・`fuzzy_scores` |
| `GET /api/dev/sim/generations/{世代ID}/report` | 世代の `report.json`。無ければ 404 |

* 一覧は `manifest.json` だけで作る。`battle_NNN.json`（1戦で数MB〜十数MB）はバトルを選んだときにだけ読む
* `logs` は表示に使わない `fuzzy_scores` を除いて返す。転送量が約1/4減る（7.5MB のファイルで 5.75MB）。ファイルはそのまま
* `fuzzy_scores` は `decisions` で、選んだ1機の分だけ返す（4機・約860ステップの戦闘で、1機あたり約600件・約0.5MB）
* 世代ID は CLI のラベルと同じく、英数字で始まり英数字と `_.-` だけのものに限る（`..` と書き込み中の `.tmp-` を弾く）
* 戦闘のファイル名は `manifest.json` の `battles[].file` から引き、`battle_<数字>.json` の形に限る
* シンボリックリンクを辿った先が読み込み元の外なら読まない

### 開発環境だけで使えるようにする仕組み

| 層 | `NODE_ENV !== "development"` のとき |
|---|---|
| ページ（`app/dev/sim/page.tsx`） | `notFound()` で 404 |
| Route Handler | `{"detail": "Not Found"}` を 404 で返す |
| Clerk（`middleware.ts`） | `/dev(.*)`・`/api/dev(.*)` を公開ルートに入れない（未ログインなら Clerk が 404 にする） |

### 保存形式についての判断

1戦が十数MBになる問題（Issue #612 のコメント）は、保存形式を変えずにビューア側で対応した（案 A）。

* 一覧は `manifest.json` だけで作り、バトルは選んだときに1戦ずつ読む
* `fuzzy_scores` は `logs` から除き、デバッグ表示では1機分だけ `decisions` で返す
* 値が null の項目を省く案（B）と gzip の案（C）は採らなかった。ディスクの使用量は、世代管理（直近5世代）と不要な世代のピン留めを外す運用で抑える

### 検証（/dev/sim）

* `frontend/tests/unit/localSimStore.test.ts`: 世代の並び順・一時ディレクトリの除外・パスの検証・シンボリックリンク・`fuzzy_scores` の除去・NDJSON・開発環境の判定
* `run --rounds 3` で作った世代（1戦 7〜10MB）を `npm run dev` で開き、世代一覧・バトル一覧・再生・チャプター・戦果サマリーが表示されることを確認した
* `npm run build && npm run start` で `/dev/sim` と `/api/dev/sim/...` が 404 になることを確認した。`middleware.ts` を外した状態でも、ページと Route Handler 自身が 404 を返すことを確認した

---

## /dev/sim: 世代の比較とAIの判断の表示

### 世代の比較

上部の「世代の比較」タブで、2つの世代の集計値を並べる。

* A（比べる元）と B（比べる先）を選ぶ。既定は1つ前の世代（A）と最新の世代（B）
* 選んだ世代は URL（`/dev/sim?view=compare&a=<世代ID>&b=<世代ID>`）に入る
* 表は CLI の `compare` と同じ項目（実行条件・集計値・機体ごとの撃墜数 / 被撃墜率・警告）。違う実行条件は黄色で示す
* 集計値は各世代の `report.json` を読む。無いか古い形式の世代には、`local_sim report <世代ID>` の実行を案内する
* 表の値と差は `frontend/src/utils/localSimAnalysis.ts` で作る。書式は CLI の `compare`（`analysis.py`）に揃える

### AI の判断（デバッグ）

再生画面のターンコントローラーの下に、選んだ機体の AI の判断を表示する。再生位置に合わせて更新する。

| 表示 | 元のログ | 内容 |
|---|---|---|
| 行動の判断 | 再生位置以前で最後の `AI_DECISION` | `strategy_mode`、選んだ行動（メッセージの `[行動] を選択`）、`fuzzy_scores`（出力変数ごとの集合の活性化度。例: `action` の `ATTACK`・`MOVE` …）を横棒で表示する。メッセージ（ファジィ推論の入力値）も出す |
| ターゲット選択 | 再生位置以前で最後の、`fuzzy_scores` を持つ `TARGET_SELECTION` | 候補ごとの優先度スコア（`all_scores`）と、選んだ候補の入力値（`inputs`） |

* 機体は判定する機体（★）が既定。セレクトで切り替える
* `fuzzy_scores` の中身は `docs/features/fuzzy-engine.md` を参照
* 再生位置の判断は二分探索で引く（`lastAtOrBefore()`）
* `BattleReplayPanel` に、再生位置を受け取って描画する `renderTimelinePanel` を追加した。履歴詳細（`BattleDetailModal`）は渡さないため、表示は変わらない

### 検証（比較・AI の判断）

* `frontend/tests/unit/localSimAnalysis.test.ts`: 比較表の値と差、機体の対応付け、実行条件の違い、再生位置の判断の引き方、選んだ行動の取り出し
* `frontend/tests/unit/localSimStore.test.ts`: `report.json` の読み込み、判断ログの抽出
* `run --rounds 3` で作った2世代を `npm run dev` で開き、比較画面、`report.json` が無い世代への案内、再生位置と機体の切り替えで AI の判断が変わることを確認した

---

## log-bench / log-compare: ログのサイズと端末負荷の計測

Epic #631（配信用ログと解析用ログの分離）の計測基準。Issue #632 で作った。
ロスターの機体で1戦を回し、同じログを保存形式ごとに変換して、サイズとパースの負荷を測る。
配信用の形式（Issue #634）の前後を、同じ条件の数字で比べるために使う。

```bash
cd backend
python -m scripts.simulation.local_sim log-bench --roster bench50 --label before
python -m scripts.simulation.local_sim log-bench --roster small5 --units 50 --formats stored,draft
python -m scripts.simulation.local_sim log-compare before after
```

| オプション | 説明 |
|---|---|
| `--roster <名前>` | ロスター名、またはロスターの JSON ファイルのパス（必須） |
| `--units N` | 戦闘に出す機体数。既定は本番の定員（`MatchingService` の `room_size` = 50） |
| `--seed N` | 戦闘のシード。既定は固定値（`log_bench.DEFAULT_SEED` = 632） |
| `--steps N` | 最大ステップ数。既定は本番バッチと同じ `DEFAULT_MAX_STEPS` |
| `--label <名前>` | 計測結果の名前。省略するとロスター名 |
| `--formats a,b` | 測る形式（下記）。省略すると全部 |
| `--runs N` | パースを測る回数（既定 5）。中央値を使う |
| `--no-parse` | Node でのパースの計測を省く |
| `--keep-ndjson <DIR>` | 形式ごとの NDJSON を残す。ブラウザ（DevTools のスロットリング）で確かめるときに使う |
| `--format json` | 計測結果を JSON で標準出力に出す（経過の表示と保存先は標準エラー） |

* DB には接続しない（`run` と同じく `forbid_database()` を呼ぶ）
* 結果は `battle_logs/local_sim/log_bench/<日時>_<ラベル>.json` に保存する（gitignore 済み）。世代管理の対象外で、自動では消さない
* `log-compare` の引数は、ファイルのパス・ID（ファイル名から `.json` を除いたもの）・その前方一致・ラベル

### 戦闘の組み立て

本番の基準（50機・全機が個人戦）に合わせる。

* ロスターの全機の `team_id` を `null` にする（実行時に `team_id` = 機体ID の個人戦になる）
* ロスターの機体が `--units` に足りなければ、先頭から順に複製する。複製した機体の ID は、元の ID と複製の番号から
  `uuid5` で決める。名前とスナップショットは元の機体と同じ
* ロスターの機体が `--units` より多いとエラーにする
* 判定する機体の選び方・乱数の固定は `run` と同じ（`seed_battle_rngs()` / `run_battle()`）

50機のロスターは `fetch --npc 49` などで作る。手元に50機のロスターが無ければ、少ない機体のロスターを `--units 50` で複製する。

### 形式

実装は `backend/scripts/simulation/local_sim/log_bench.py` の `LOG_FORMATS`。同じ戦闘のログ（`simulator.logs`）を変換する。

| 形式 | 内容 |
|---|---|
| `stored` | 本番が保存・配信している形式。`strip_debug_fields()` の出力 |
| `draft` | 目標値を決めるための試算。`AI_DECISION` を除く。`TARGET_SELECTION` は機体ごとに相手が変わった行だけ残す。null の項目を省き、小数を1桁に丸める |
| `draft_no_message` | `draft` から、MOVE・WAIT・TARGET_SELECTION の `message` も省く |
| `replay` | 配信用ログ（Issue #634）。`app/engine/replay_log.py` の `to_replay_logs()` の出力。先頭のヘッダー行も1行として数え、`action_type` ごとの行数では `(ヘッダー)` と表示する。スキーマは `docs/features/battle-log-feature.md` の「配信用ログ（replay）」 |

`draft` はビューアで再生できることを確かめていない。サイズの見積もりだけに使う。

### 計測する項目

| 項目 | 測り方 |
|---|---|
| 行数・`action_type` ごとの行数と展開後のサイズ | NDJSON の行ごと |
| 展開後のサイズ | 本番と同じ `logs_to_ndjson_text()`（`ensure_ascii=False`）で書いた NDJSON のバイト数 |
| gzip 後のサイズ | `GZipMiddleware` と同じ圧縮。圧縮レベルは既定値（9）。GCS から読む単位（256KB）ごとに `Z_SYNC_FLUSH` する。テストで、実際の `GZipMiddleware` の転送量と一致することを確かめている |
| 項目ごとのサイズ | `"key": value, ` の分を項目ごとに足す。値が null の分も出す。残り（括弧・改行）は1行1バイト |
| パース時間 | `parse_bench.mjs` を `node --expose-gc` で実行する。`fetchBattleLogsNdjson()` と同じ手順（64KB ごとに `TextDecoder` で読み、改行で区切って `JSON.parse`、500件ごとに配列をコピー）。`--runs` 回の中央値 |
| ヒープ（保持分） | GC の後、パースした配列を持ったまま GC して、`heapUsed` の増えた分 |

表示では、gzip 後のサイズから Lighthouse の Slow 4G（1.6Mbps）での転送時間と、パース時間を4倍した値（Chrome DevTools の CPU 4倍スロットリングの目安）も出す。

### 再現性

* 同じロスター・同じシード・同じコードなら、行数・サイズ・項目の内訳・ヒープは同じ値になる。`PYTHONHASHSEED` を変えても NDJSON はバイト単位で一致する
* パース時間はマシンと、そのときの負荷で変わる。同じマシンで続けて測った値だけを比べる。負荷の高いときは、同じ NDJSON でも1.5〜1.8倍になった
* 計測結果には、コミット・ファジィルールのハッシュ・OS・CPU・Node のバージョンを記録する。`log-compare` は条件や環境が違うと警告を出す

### 計測結果（Issue #632 時点）

M1 Mac・Node 20.19.6。ロスターは本番DBを使わず、テスト用の SQLite でマスターから作った（生成 NPC とエースだけ）。
パース時間は、マシンの負荷が低いときの値。

| ロスター | 戦闘 | 形式 | 行数 | 展開後 | gzip | Slow 4G | パース | ×4 | ヒープ |
|---|---|---|---|---|---|---|---|---|---|
| 50機（生成 NPC 47・エース 3） | 191.6秒 | `stored` | 112,679 | 83.5MB | 6.09MB | 29.0秒 | 322ms | 1.29秒 | 66.9MB |
| | | `draft` | 47,231 | 15.7MB | 1.12MB | 5.4秒 | 80ms | 0.32秒 | 20.5MB |
| | | `draft_no_message` | 47,231 | 11.9MB | 0.95MB | 4.5秒 | 69ms | 0.27秒 | 15.9MB |
| 5機を50機に複製 | 213.1秒 | `stored` | 110,446 | 81.5MB | 5.53MB | 26.3秒 | 335ms | 1.34秒 | 65.3MB |
| | | `draft` | 52,658 | 17.4MB | 1.16MB | 5.5秒 | 87ms | 0.35秒 | 23.0MB |
| | | `draft_no_message` | 52,658 | 13.2MB | 0.96MB | 4.6秒 | 79ms | 0.32秒 | 17.8MB |

* `stored` の行数の53〜59%は `AI_DECISION` と `TARGET_SELECTION`。`TARGET_SELECTION` を相手が変わった行だけにすると、約3万行が約470行になる
* `stored` の展開後のサイズの約44%は値が null の項目。最も大きい項目は `message`（約18%）
* 本番の50機ルームの試算（PR #630 のコメント、約211秒・10.8万行・展開後 73〜78MB・gzip 4.7〜4.8MB）と同じ規模になった

### 目標値

計測結果と次の想定から、50機・約200秒の個人戦（`log-bench` の既定の条件）で、配信用ログが満たす値を決めた。Epic #631 の決定事項に書いている。

| 項目 | 目標 | 想定と根拠 |
|---|---|---|
| gzip 後のサイズ | 1.2MB 以下 | Slow 4G（1.6Mbps）で全量の転送が約6秒以内。NDJSON のストリーミングで、最初の500件（gzip で十数KB）が届けば再生は始まる。全量が届くまでの時間は、終盤へのシークとチャプターが使えるまでの時間になる。現状は約26〜29秒 |
| 展開後のサイズ | 20MB 以下 | パース時間とヒープは展開後のサイズにほぼ比例する（`stored` で 82MB・パース約330ms・ヒープ約66MB） |
| パース時間 | M1 Mac の Node で 100ms 以下（CPU 4倍で 400ms 以下） | ミドルレンジの Android を CPU 4倍スロットリングで見込む。パースはストリーミング中にチャンクごとに分かれて動くため、1回の長いタスクにはならない |
| ヒープ（保持分） | 25MB 以下 | ビューア（three.js）と同じタブで持つ。現状の約66MBを3分の1程度にする |

* `draft` はどちらのロスターでも全項目を満たす。ただし gzip 後のサイズの余裕は小さい（1.12〜1.16MB）。本番のロスターで戦闘が長いと超えうる
* `draft_no_message`（gzip 0.95MB）なら余裕がある。`message` を省くかは Issue #634 で決める

### 計測結果（Issue #634 時点）

配信用ログ（`replay`）の計測。M1 Mac・Node 20.19.6。ロスターは Issue #632 と同じ作り方（テスト用の SQLite でマスターから作った生成 NPC 47・エース 3）。
ロスターを作り直し、Issue #632 の後にエンジンの変更も入ったため、Issue #632 の時点とは別の戦闘になった。`stored` も同じ戦闘で測り直した。

| 戦闘 | 形式 | 行数 | 展開後 | gzip | Slow 4G | パース | ×4 | ヒープ |
|---|---|---|---|---|---|---|---|---|
| 177.4秒 | `stored` | 122,501 | 91.1MB | 6.54MB | 31.2秒 | 345ms | 1.38秒 | 73.5MB |
| | `draft` | 49,365 | 16.6MB | 1.19MB | 5.7秒 | 77ms | 0.31秒 | 21.7MB |
| | `draft_no_message` | 49,365 | 12.5MB | 1.00MB | 4.8秒 | 74ms | 0.30秒 | 16.7MB |
| | `replay` | 49,366 | 11.6MB | 0.96MB | 4.6秒 | 71ms | 0.28秒 | 16.3MB |

* `replay` は目標値（gzip 1.2MB・展開後 20MB・パース 100ms・ヒープ 25MB）をすべて満たす
* この戦闘では `draft`（message を残す試算）の gzip が 1.19MB で、目標値ぎりぎりになった。配信用ログでは MOVE・WAIT・TARGET_SELECTION の `message` を省いた
* `replay` が `draft_no_message` より小さいのは、`is_crit: false` と、描画に使わない項目（`strategy_mode` など）を省いたため

### ブラウザでの計測（Issue #635）

ビューアが配信用ログを読めるようにした後、同じ戦闘の旧形式と配信用ログを `/dev/sim` で再生して比べた。
戦闘は上の計測と同じ条件（`bench50`・seed 632・177.4秒）で `run` し、`battle_NNN.json` の `logs` を `to_replay_logs()` の出力に書き換えた世代を別に作った。

条件:

* M1 Mac。Playwright の Chromium（ヘッドレス、GPU は Metal）。Chrome DevTools と同じ Slow 4G（562.5ms・180KB/s）と CPU 4倍スロットリングを CDP で掛けた
* `npm run dev` の前に、`/logs` の応答だけを gzip で返すプロキシを置いた。本番の `GZipMiddleware` と同じ転送量にするため（Route Handler は圧縮しない）
* 開発ビルドのページの JS は本番より大きい。ページはスロットリングを掛けずに開き、バトルを選ぶ直前に掛けた。時間はバトルを選んでからの値
* 再生ボタンを押し、全件を読み終えてから10秒後まで再生した

| 形式 | 転送量 | 再生開始 | 全件を読み終える | 長いタスク（合計・最長） | JS ヒープ（ページ全体） |
|---|---|---|---|---|---|
| 旧形式 | 6.85MB | 3.4秒 | 64.9秒 | 58.1秒・2.07秒 | 302MB |
| 配信用ログ | 0.97MB | 3.1秒 | 7.7秒 | 3.2秒・0.25秒 | 68MB |

* 配信用ログは再生開始から止まらずに進んだ。全件を読み終える前から再生でき、バトルを選んでから18秒で 9.7秒の位置まで進んだ
* 旧形式は読み込み中に長いタスクが続き、再生が実時間の4分の1程度に落ちた（75秒で 18.2秒の位置）
* JS ヒープは three.js の描画と開発ビルドの React を含む。上の Node の計測（ログだけ）とは比べられない
* 計測の途中で、`useNdjsonBattleLogs()` の不具合を2つ直した（`docs/features/battle-log-feature.md` の「逐次パース結果をUIへ段階的に反映する」）。直す前は、ビューアが全件の取得を待ってからマウントされていた（再生開始が旧形式で約44秒、配信用ログで約7.6秒）
* 時間帯ごとに分けて読み込む方式は採らなかった。配信用ログでは全件を読み終えるまで約8秒で、その間も再生できるため

---

## replay-fixture: 旧形式と配信用ログの一致テストのログ

Issue #634 で作った。同じ戦闘の旧形式（`strip_debug_fields()` の出力）と配信用ログ（`to_replay_logs()` の出力）を、
機体の情報（`player_info` / `enemies_info`、`run` の `battle_NNN.json` と同じ組み立て）と一緒に、gzip した JSON に書く。

```bash
cd backend
python -m scripts.simulation.local_sim replay-fixture --roster replay6
```

| オプション | 説明 |
|---|---|
| `--roster <名前>` | ロスター名、またはロスターの JSON ファイルのパス（必須） |
| `--seed N` | 戦闘のシード。既定は `replay_fixture.DEFAULT_FIXTURE_SEED`（639） |
| `--steps N` | 最大ステップ数。既定は `replay_fixture.DEFAULT_FIXTURE_STEPS`（600 = 60秒）。リポジトリに置くファイルを数百KBに収めるため |
| `--out <パス>` | 保存先。既定は `backend/tests/fixtures/replay_log_parity.json.gz` |

* 次の2つのテストがこのファイルを読む
  * `frontend/tests/unit/replayLogParity.test.ts`: 旧形式と配信用ログから、ビューアの表示状態が一致することを確かめる
  * `backend/tests/unit/test_replay_log.py`: ファイルの配信用ログが、今の `to_replay_logs()` の出力と一致することを確かめる。変換を変えたらこのテストが落ちるので、フィクスチャを作り直す
* 同じロスター・同じシードなら、同じバイト列になる（gzip のヘッダーの時刻を 0 にしている）
* DB には接続しない（`run` と同じく `forbid_database()` を呼ぶ）
* 今のフィクスチャは、テスト用の SQLite でマスターから作った6機のロスター（生成 NPC 4・エース 2、戦域 `solomon`）で作った。撃破・クリティカル・EN の記録・相手の切り替えを含む。格闘（`MELEE_COMBO`・`MELEE_CLASH`）・ブースト・仕切り直しは含まない。これらの行は丸めと null の省略だけを受けるため、変換のルールは `test_replay_log.py` で確かめている

---

## fetch-log: 本番の解析用ログの取得

Issue #637 で作った。プレイヤーから報告された本番の戦闘を、手元の `/dev/sim` でファジィスコア付きで追うためのコマンド。
解析用ログ（エンジンの出力をデバッグ項目ごと gzip したもの。[battle-log-feature.md](battle-log-feature.md) の「解析用ログ」）を GCS から取り、
`run` と同じ形式（`manifest.json` / `battle_001.json`）の世代として保存する。

```bash
cd backend
python -m scripts.simulation.local_sim fetch-log --result <バトル結果ID>
python -m scripts.simulation.local_sim fetch-log --room <ルームID> --user-id user_xxxx --label report-1021 --pin
```

| オプション | 説明 |
|---|---|
| `--result <ID>` | バトル結果（`battle_results.id`）のID。`--room` とどちらか1つが必須 |
| `--room <ID>` | ルームID。ルームは参加者ごとに結果を持つので、`--user-id` に合う結果、無ければエントリーが早い結果を選ぶ。複数あるときは件数を表示する |
| `--user-id <ID>` | `--room` で、この Clerk User ID の視点の結果を選ぶ |
| `--label <名前>` | 世代のラベル。既定は `prod-<バトル結果IDの先頭8桁>` |
| `--pin` | ピン留めする |

* 必要な設定
  * `backend/.env` の `NEON_READONLY_DATABASE_URL`（[準備: Read Only の接続](#準備-read-only-の接続)）。`fetch` と同じ Read Only 接続で `battle_results` を読むだけ。DB には書き込まず、最後にロールバックする
  * `BATTLE_LOG_GCS_BUCKET`（本番は `msbs-next-battle-logs-prod`）と、`gcloud auth application-default login` の認証情報
* ログの取得元は `analysis-logs/{battle_log_id}.ndjson.gz`。`battle_log_id` は `battle_results` から引く
* 解析用ログは30日で削除される。無い場合は「解析用ログがありません。保存期間（30日）を過ぎて削除されたか、解析用ログの保存を始める前の戦闘です。」と表示して終了する（世代は作らない）
* `battle_001.json` の表示用項目（`player_info` / `enemies_info` / `obstacles_info` / `map_bounds` / `part_hit_summary` など）は `BattleResult` の値をそのまま入れる。
  戦域名・環境名・表示プリセットはマスターから引く（`TheaterService.labels_for()`）。`logs` は解析用ログをそのまま入れる（`fuzzy_scores` / `strategy_mode` を含む）
* `report.json` も作るので、`report` / `compare` も使える

### 本番の世代とローカルの世代の違い

`manifest.json` の `source` が `production` の世代は、本番で動いた戦闘を再現したものではなく、記録を取り込んだもの。次の項目が `run` の世代と違う。

| 項目 | 本番の世代 |
|---|---|
| `source` / `source_battle_result_id` / `source_room_id` | `production` / 取得元のバトル結果ID / ルームID。`run` の世代の `source` は `local`（古い世代は項目なしで、`local` として扱う） |
| `roster_name` / `roster_file` / `player_entry_index` | null。`roster.json` は作らない |
| `seed`（`battles[].seed` も） / `max_steps` | null。本番はシードも最大ステップ数も保存していない |
| `git` / `fuzzy_rules_hash` | 空 / null。取得時点のコードは、本番で戦闘したときのコードとは限らない |
| `rounds` / `battles` | 1。1つの世代に1戦だけ入る |
| `elapsed_time` / `steps_used` | ログの最大の時刻 / ログの時刻の種類数（目安）。本番はどちらも保存していない |
| `timed_out` | 常に false（本番は打ち切りを保存していない） |

* 勝敗が `WIN` / `LOSE` 以外の結果と、機体・障害物・フィールド範囲の表示用項目が無い古い結果は取り込めない（エラーにする）
* シードが無いので、本番の戦闘をローカルで再実行して再現することはできない。再生して調べる用途

### 世代管理

本番から取得した世代も、`run` の世代と同じ扱いにする。ピン留めしていない世代が5つを超えたら古い順に削除する。
取得した世代を残したいときは `--pin` を付けるか、`pin` を使う。
解析用ログは30日で消えるため、後で見直す戦闘はピン留めしておく。

### /dev/sim での見分け方

* 世代一覧に「本番」のバッジを出し、ロスター名の代わりに取得元のバトル結果IDを表示する
* 戦闘の一覧ではシードを出さない。再生画面の見出しは `seed N` の代わりに「本番の戦闘」と出す
* 再生と AI の判断（ファジィスコア）の表示は、`run` の世代と同じ（[AI の判断（デバッグ）](#devsim-世代の比較とaiの判断の表示)）
* 条件の比較では、null の項目を `-` と表示する

### 検証（fetch-log）

* `tests/unit/test_local_sim_fetch_log.py`: 結果とログからの記録の組み立て、バトル結果IDとルームIDでの選択、`manifest.json` / `battle_001.json` / `report.json` の保存、世代管理とピン留め、不正なラベルで世代を残さないこと、解析用ログ（gzip した NDJSON）の取得と、無いときのエラー
* 実際の本番DBと GCS への接続は、このリポジトリのテストでは行っていない。本番の戦闘での動作確認は、オーナーの認証情報が必要なため、マージ後に `fetch-log` で行う

---

## Admin Tool: `/local-sim`（Issue #701・#705）

Admin Tool（`admin-tool/`、`npm run dev` で手元だけ起動）から `fetch` でロスターを作り、`run` を実行し、世代の一覧・集計を見る。再生と比較は frontend の `/dev/sim` を別タブで開く（BattleViewer は frontend にしか無いため）。

* Cloud Run・GCS は使わない。Route Handler（Node）が `uv run python -m scripts.simulation.local_sim run ...`（`fetch ...`）を子プロセスで起動する（作業ディレクトリは `backend/`、引数は配列で渡しシェルを通さない）
* backend のサーバーは、ロスター作成フォームの選択肢（戦域・NPC・プレイヤーと所有機）を引くときだけ使う。`run` と結果の確認には要らない
* `run` はグローバルの乱数やエースのデータを書き換えるため、backend のリクエスト内ではなく別プロセスで実行する
* 開発環境（`NODE_ENV=development`）以外では全 Route Handler が 404 を返す

### Route Handler

| メソッド・パス | 内容 |
|---|---|
| `GET /api/local-sim/rosters` | ロスターの一覧（`rosters/*.json`） |
| `POST /api/local-sim/rosters` | `fetch` でロスターを作る（Issue #705）。実行中なら 409、同名のロスターがあり `force` でなければ 409、入力が不正なら 422 |
| `GET /api/local-sim/generations` | 世代の一覧（新しい順。戦闘ごとの内訳は省く） |
| `GET /api/local-sim/generations/{世代ID}` | `manifest.json` と `report.json` |
| `PATCH /api/local-sim/generations/{世代ID}` | ピン留めの切り替え（`{"pinned": bool}`。CLI の `pin` / `unpin`） |
| `POST /api/local-sim/runs` | 実行開始。実行中なら 409、入力が不正なら 422 |
| `GET /api/local-sim/runs/current` | 現在（直近）の `run` / `fetch` の進捗。`kind` で見分ける |
| `DELETE /api/local-sim/runs/current` | 実行中の `run` / `fetch` の中止 |

* ジョブの状態はサーバーのメモリ（`globalThis`）に持つ。`run` と `fetch` は1つのジョブとして扱い、同時に実行するのは1つだけ（`runner.ts` の `launch()` を共通で使う）
* 進捗は CLI の出力 `[i/N] seed=…` から読む。子プロセスは `PYTHONUNBUFFERED=1` で起動する。UI は実行中だけ1秒ごとにポーリングする（SWR）
* 終了コードが 0 以外なら、標準エラーを表示する
* ロスター名・ラベル・世代ID は CLI と同じ規則（英数字で始まり英数字と `_.-` だけ）でサーバー側でも確かめる。パスの検証は frontend の `localSimStore.ts` と同じ（実パスが保存先の外に出ないこと）
* 読み込み元は `LOCAL_SIM_DIR`（既定はリポジトリ直下の `battle_logs/local_sim`）。`run` 自体は CLI の既定の保存先に書くため、`LOCAL_SIM_DIR` を変えるときは CLI 側と一致させること
* 再生・比較の URL の基準は `NEXT_PUBLIC_DEV_SIM_URL`（既定 `http://localhost:3000`）

### ロスター作成（fetch、Issue #705）

`/local-sim` の「ロスター作成」フォームで `fetch` の引数を組み立てる。

| フォーム | CLI の引数 |
|---|---|
| ロスター名（省略すると CLI が日時から作る） | `--name` |
| 戦域（管理 API `GET /api/admin/theaters` の一覧。読めないときは ID を手で入れる） | `--theater` |
| ミノフスキー濃度（省略すると戦域の基準） | `--minovsky` |
| NPC 数・エース数 | `--npc` / `--ace` |
| 必ず参加させるエース（管理 API `GET /api/admin/ace-pilots` の一覧からチェック） | `--ace-id`（複数） |
| 作戦「本番の作戦マスター」: `missions.id` を入れる | `--mission <ID>` |
| 作戦「リポジトリの定義」: `retreat_support` など | `--mission-builder <名前>` |
| 参加機体「プレイヤー」: 名前で引いたパイロットの所有機から選ぶ | `--ms <機体ID>[:チーム]` |
| 参加機体「NPC」: NPC のパイロットを選ぶ（出撃機体が未設定なら CLI が所有機の先頭にする） | `--pilot <pilots.id>[:チーム]` |
| 参加機体「機体ID」: 手で入れる | `--ms <機体ID>[:チーム]` |
| 同名のロスターがあれば上書きを確認する | `--force` |

* プレイヤーの出撃機体は本番ではエントリーごとに決まり、`pilots.active_mobile_suit_id` は設定されないことが多い。そのため `--pilot` は使わず、所有機を毎回選んで `--ms` で渡す（戦域ごとにビルドが異なるため、所有機の先頭へのフォールバックはしない）。`active_mobile_suit_id` を Admin Tool から設定する機能は作らない
* プレイヤーと所有機の一覧は、読み取り専用の管理 API で引く（下表）。backend の接続先DB（`NEON_DATABASE_URL`）を読む。ロスターの中身は `fetch` が本番DBから Read Only の接続で読み直す
* 引数はサーバー側でも CLI と同じ規則で確かめる（`shared.ts` の `buildFetchArgs()`）。機体ID は UUID、パイロットID は英数字で始まり英数字と `_-` だけ、ロスター名・チーム名・戦域ID は英数字で始まり英数字と `_.-` だけ、NPC 数・エース数は 0〜100 の整数、ミノフスキー濃度は 0〜1。`-` で始まる値はオプションと取り違えるため弾く
* 作戦を選ぶと、NPC 数・エース数・エースの選択・チーム・NPC の行を無効にする（CLI と同じ制約。Issue #702）。`buildFetchArgs()` も、作戦と NPC・エース・チームの併用、`--mission` と `--mission-builder` の併用を本番DBへ接続する前に拒む。本番の作戦マスターの一覧を引く管理 API は無いため、ID を直接入れる
* 同名のロスターは、フォームで上書きを確認してから `force`（`--force`）を付ける。Route Handler も `force` でなければ先に 409 を返す（CLI は本番DBから読み終えた後に拒むため）
* 終わったらロスター一覧を取り直し、作ったロスターを「実行」のロスターに選ぶ。ロスター名は CLI の出力 `N 機を保存しました: <パス>` から読む
* 失敗したときは CLI の標準エラーを出す。`NEON_READONLY_DATABASE_URL` が未設定なら `エラー: NEON_READONLY_DATABASE_URL が設定されていません。…` がそのまま出る
* 参加機体が2機未満（作戦以外）や、同じ機体の2回指定は CLI が拒む。作戦（`--mission` / `--mission-builder`）はフォームに無い。CLI で作る

#### 管理 API（読み取り専用）

| メソッド・パス | 内容 |
|---|---|
| `GET /api/admin/players?name=&limit=` | プレイヤー（`is_npc = false`）のパイロットを名前順に返す。`name` は部分一致（大文字小文字を区別しない。`%`・`_` はワイルドカードにしない）、`limit` は既定 50・最大 200。所有機の数を付ける |
| `GET /api/admin/players/{pilot_id}/mobile-suits` | プレイヤーの所有機（機体名・ID・機体マスターID・`active_mobile_suit_id` の機体か）を名前順に返す。NPC のパイロットは 404 |

どちらも `X-API-Key` が要り、DB には書き込まない。

### 中止

「中止」は子プロセスへの SIGTERM。`fetch` は DB を読むだけなので、そのまま終わる（ロスターは最後に書くため、取得中に止めればロスターは残らない）。`run` は SIGTERM を受けると `SystemExit(143)` を送出し、`run_generation()` の `except BaseException` を通って `GenerationWriter.discard()` が書きかけの世代（`.tmp-<世代ID>`）を消す。

### 表示する項目

* 世代の一覧: ラベル・日時・戦闘数・勝敗・打ち切り・ピン留め。2つ選んで「比較」で `/dev/sim?view=compare&a=&b=` を開く
* 世代の詳細: 勝率・打ち切り・平均戦闘時間・判定機の撃墜数・機体ごとの撃墜数/被撃墜率（`report.json`）、戦闘の一覧（勝敗・撃墜・経過時間・シード）と「再生」（`/dev/sim?gen=&battle=`）
* 作戦の世代（`fetch --mission`）: 一覧に作戦名、詳細に作戦の成功率（成功/失敗/引き分け）・離脱した友軍の1戦平均・撃破された友軍の合計を出す（`report.json` の `objective`）。引き分けは勝敗に「分」で出す

### 検証（Admin Tool）

* `backend/tests/unit/test_local_sim_run.py::test_sigterm_during_run_leaves_no_generation`: SIGTERM で書きかけの世代が残らないこと
* `admin-tool/tests/unit/localSim.test.ts`: 名前の検証、`run` / `fetch` の引数の組み立て、フォームの参加機体から `--ms` / `--pilot` への変換、CLI 出力の解析（進捗・世代ID・ロスター名）、`/dev/sim` の URL
* `backend/tests/unit/test_admin_players.py`: プレイヤーだけを返すこと、名前の絞り込み（大文字小文字・ワイルドカード）、件数の上限、所有機の名前順と出撃機体の印、NPC は 404、取得で DB を書き換えないこと
* `next dev` で Route Handler を確認済み（一覧・不正な入力の 422・存在しないロスターで失敗した際の標準エラー表示・実行中でないときの中止が 409）。ロスターの作成には本番DBへの接続が必要なため、実際の戦闘の実行と画面の操作は未確認
* `fetch`（Issue #705）: `next dev` で、不正な機体ID の 422、実行中の `run` 開始が 409、同名のロスターで 409、`NEON_READONLY_DATABASE_URL` 未設定で失敗した際の標準エラー表示をフォームと API で確認した。本番DBへの接続と、選択肢（管理 API）を引いた状態での画面の操作は未確認

# ローカルバトルシミュレータ

## 概要

本番の参加機体を使って、バトルをローカルで実行する開発用のツール。
Epic #608 で作る。このドキュメントは Sub-Issue 1〜5（Issue #609〜#613）の範囲を書く。

* 戦闘処理は本番バッチと同じモジュール（`app/services/battle_execution.py`）を使う
* `fetch` で本番DBから参加機体・NPC・エースと戦域条件を読み、手元の JSON（ロスター）に保存する
* 本番DBへの接続は `fetch` の1回だけ。以降の実行（`run`）はロスターだけで行い、DB には接続しない
* `run` は同じロスター・同じシードなら同じログを再現する。1回の `run` を1世代として保存し、直近5世代を残す
* 本番DBには書き込まない。SELECT 権限だけのロールと `default_transaction_read_only` の2つで防ぐ
* 保存した結果は、開発環境の `/dev/sim` で本番の履歴詳細と同じ画面で再生できる
* `report` / `compare` で世代の勝率・戦闘時間・行動分布などを集計し、2つの世代を比べられる。`/dev/sim` でも比べられ、再生中に AI の判断（ファジィスコア）を確かめられる

### 今後の予定（Epic #608）

| Sub-Issue | 内容 |
|---|---|
| 1 | 本番バッチの戦闘実行処理を `app/services/` へ切り出す（Issue #609、実装済み。本ドキュメントの「[戦闘実行の共通モジュール](#戦闘実行の共通モジュール)」） |
| 2 | Read Only 接続と参加機体の取得 `fetch`（Issue #610、実装済み。本ドキュメントの「[fetch: 参加機体の取得](#fetch-参加機体の取得)」） |
| 3 | ロスターからの実行と世代管理 `run`（Issue #611、実装済み。本ドキュメントの「[run: ロスターからの実行](#run-ロスターからの実行)」「[世代管理](#世代管理-list--pin--unpin)」） |
| 4 | 開発用バトルビューア `/dev/sim`（Issue #612、実装済み。本ドキュメントの「[/dev/sim: 開発用バトルビューア](#devsim-開発用バトルビューア)」） |
| 5 | 世代間の比較とバランス分析表示（Issue #613、実装済み。本ドキュメントの「[report / compare: 世代の集計と比較](#report--compare-世代の集計と比較)」「[世代の比較とAIの判断の表示](#devsim-世代の比較とaiの判断の表示)」） |
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
| `seed_battle_rngs(seed)` | 戦闘で使う乱数をすべて固定する（[再現性](#再現性)）。本番バッチは呼ばない |

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
| `--pilot <パイロットID>[:<チーム>]` | パイロットの出撃機体（`active_mobile_suit_id`）を参加させる。ID は `pilots.id` か `user_id`（複数指定可） |
| `--npc N` | 本番の永続化NPCから N 機を選ぶ。足りない分は本番と同様に NPC を生成して補う |
| `--ace N` | エースパイロットをランダムに N 機参加させる。同じエースは重ねない |
| `--theater <戦域ID>` | 戦域。省略すると戦域なし（宇宙） |
| `--minovsky <0〜1>` | ミノフスキー濃度。省略すると戦域の `base_minovsky`（戦域なしなら 0） |
| `--name <名前>` | ロスター名。省略すると日時（例: `20261005-213000`） |
| `--force` | 同名のロスターを上書きする |

参加機体が2機未満のときはエラーにする。

### 機体の選び方とスナップショット

スナップショットは本番と同じ関数で作る。

| 取得元 | 選び方 | スナップショット |
|---|---|---|
| `--ms` / `--pilot`（プレイヤー） | 指定どおり | エントリー登録と同じ。`WeaponService.resync_mobile_suit_weapons()` の後に `MobileSuitService.build_entry_snapshot()`（地形適正は機体マスターの値） |
| `--ms` / `--pilot`（NPC のパイロット） | 指定どおり。出撃機体が未設定なら所有機の先頭 | マッチングと同じ `build_npc_entry_snapshot()`（`npc_pilot_level` 付き）。初期位置をランダムにし、HP を全快にする |
| `--npc` | `MatchingService.choose_npcs()`。本番の `select_npcs_for_room()` と同じ選び方で、出撃機体を保存しない | 同上。ロスターに入っている機体は選ばない |
| `--npc` の不足分 | `MatchingService._create_npc_mobile_suit()` で生成 | 同上（レベル1） |
| `--ace` | エースのマスターから重複なしでランダムに選ぶ | `MatchingService.build_ace_mobile_suit()` で作り、`build_npc_entry_snapshot()` |

* チームを付けた機体は、スナップショットの `team_id` にチーム名を入れ、`side` を `PLAYER` にする（本番のチームエントリーと同じ）
* チームを付けない機体と NPC・エースは `team_id` が `null`。本番と同様に個人戦扱い（実行時に `team_id` = 機体ID）
* 生成した NPC・エースの機体ID は本番DBに無い

### ロスターの形式

保存先は `battle_logs/local_sim/rosters/<名前>.json`（gitignore 済み）。世代管理（Sub-Issue 3）の対象外。
手で編集して条件を変えられるよう、整形した JSON で保存する。
スキーマは `backend/scripts/simulation/local_sim/roster.py` の Pydantic モデル（`Roster`）。

```json
{
  "schema_version": 1,
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
  "ace_pilots": [ { "id": "ace_char_aznable", "mobile_suit": { "...": "..." }, "skills": { "flanking": 3 } } ]
}
```

| 項目 | 内容 |
|---|---|
| `conditions` | `TheaterService.battle_conditions()` で解決した戦域条件（`BattleConditions` と同じ項目） |
| `conditions.theater_name` / `environment_name` / `viewer_preset` | 戦域・環境タイプの表示名とビューアの背景プリセット。`run` は DB を読まないため、結果に載せる値を取得時に保存する |
| `entries[].source.kind` | `mobile_suit` / `pilot` / `npc` / `generated_npc` / `ace` |
| `entries[].snapshot` | 本番の `BattleEntry.mobile_suit_snapshot` と同じ形式 |
| `ace_pilots` | 参加エースの `ace_pilots` マスター。エンジンは戦闘中に `get_ace_pilot_by_id()` でエースのスキルを読むため、`run` はこの値を使って DB を読まずに実行する |

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
  "summary": { "battles": 20, "wins": 8, "losses": 12, "timeouts": 1, "total_kills": 15 },
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
| `summary` | 戦闘数・勝ち・負け・打ち切り（`timed_out`）の数・判定する機体の撃墜数の合計 |
| `battles[].timed_out` | 最大ステップ数で打ち切ったか |

#### battle_NNN.json

本番の `BattleResult` の表示用の項目と、ログを持つ。

| 項目 | 内容 |
|---|---|
| `index` / `seed` | 戦闘番号（1 始まり）とシード |
| `win_loss` / `kills` | 判定する機体の勝敗（`WIN` / `LOSE`）と撃墜数 |
| `elapsed_time` / `steps_used` / `timed_out` | 戦闘の経過時間（秒）・使ったステップ数・打ち切ったか |
| `environment` / `theater_id` / `theater_name` / `environment_name` / `viewer_preset` / `minovsky_density` | 戦域条件と表示名 |
| `player_info` | エントリー時点の判定する機体（本番と同じく戦闘前の状態） |
| `enemies_info` | 判定する機体以外の全ユニット（戦闘後の状態） |
| `obstacles_info` / `map_bounds` | 障害物と、戦闘終了時のフィールド範囲 |
| `logs` | `BattleLog` の一覧。`strip_debug_fields()` を通さず、`fuzzy_scores` などのデバッグ項目を残す |

1戦のサイズはログの行数に比例する。5機・約1300ステップの戦闘で約1.5万行・約14MB だった
（Issue の見積もりの 650KB は 601行の `battle_logs/sample.json` の値）。
20戦×5世代では 1GB を超えうるため、不要な世代は消すかピン留めを外す。
ログはインデントを付けずに保存し、`manifest.json` だけ整形する。

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
* `list` は世代を古い順に、世代ID・日時・ラベル・戦闘数・勝敗・ピン留め（行頭の `*`）で表示する
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
| 勝敗 | 判定する機体の勝ち・負けの数と勝率 |
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
実行条件（ロスター・判定する機体・シード・最大ステップ数・コミット・ファジィルールのハッシュ・戦域）も並べ、違う項目に `≠` を付ける。

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
| `battles` / `wins` / `losses` / `timeouts` | 戦闘数・勝ち・負け・打ち切り |
| `elapsed_time` | `{avg, min, max}`（秒） |
| `player_kills` | 判定する機体の撃墜数の合計 |
| `action_counts` / `strategy_transitions` / `weapon_usage` | 行動・戦略遷移・武器ごとの回数 |
| `units[]` | `unit_id`・`name`・`pilot_name`・`is_player`（判定する機体か）・`battles`・`kills`・`deaths`。ロスターの順で、判定する機体が先頭 |
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

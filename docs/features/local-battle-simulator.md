# ローカルバトルシミュレータ

## 概要

本番の参加機体を使って、バトルをローカルで実行する開発用のツール。
Epic #608 で作る。このドキュメントは Sub-Issue 2（Issue #610）の範囲を書く。

* `fetch` で本番DBから参加機体・NPC・エースと戦域条件を読み、手元の JSON（ロスター）に保存する
* 本番DBへの接続は `fetch` の1回だけ。以降の実行（`run`、Sub-Issue 3）はロスターだけで行う
* 本番DBには書き込まない。SELECT 権限だけのロールと `default_transaction_read_only` の2つで防ぐ

### 今後の予定（Epic #608）

| Sub-Issue | 内容 |
|---|---|
| 1 | 本番バッチの戦闘実行処理を `app/services/` へ切り出す（Issue #609） |
| 2 | Read Only 接続と参加機体の取得 `fetch`（Issue #610、実装済み。本ドキュメント） |
| 3 | ロスターからの実行と世代管理 `run`（Issue #611） |
| 4 | 開発用バトルビューア `/dev/sim`（Issue #612） |
| 5 | 世代間の比較とバランス分析表示（Issue #613） |
| 6 | エースパイロットの参加必須指定（Issue #614） |

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

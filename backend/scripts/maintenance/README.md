# clear_battle_results.py

`battle_results` テーブルのデータを削除するスクリプトです。  
バトルログのスキーマ変更など後方互換性がなくなった際に使用します。

> ⚠️ **破壊的操作です。本番DBに対して実行する場合は十分に注意してください。**

## 使い方

```bash
cd backend

# 削除対象件数を確認するだけ（実際には削除しない）
python scripts/clear_battle_results.py --dry-run

# 全件削除（確認プロンプトあり）
python scripts/clear_battle_results.py

# 確認プロンプトをスキップして全件削除
python scripts/clear_battle_results.py --yes

# 特定ユーザーの結果のみ削除
python scripts/clear_battle_results.py --user-id user_xxxxxxxxxxxx
```

## オプション

| オプション | 説明 |
|---|---|
| `--dry-run` | 削除対象件数を表示するだけで実際には削除しない |
| `--user-id USER_ID` | 削除対象を特定の Clerk User ID に絞り込む |
| `--yes` / `-y` | 確認プロンプトをスキップして即座に削除を実行 |

---

# offload_battle_logs_to_gcs.py

`battle_logs.logs` をCloud Storageへオフロードするスクリプトです（Issue #493）。
Neonの課金対象Network Transferをリプレイ閲覧のたびに消費してしまう問題への対策として、
ログ本体をNeonから追い出し `gcs_path` に置き換えます。既存データのバックフィルと、
バトル終了時の非同期オフロード失敗分の再試行を兼ねます（Cloud Schedulerなどでの
定期実行を想定）。

> ⚠️ 実DB（Neon）への書き込みを伴います。実行前にユーザーへ確認してください。

## 使い方

```bash
cd backend

# 対象件数を確認するだけ（実際には送信しない）
python scripts/maintenance/offload_battle_logs_to_gcs.py --dry-run

# 先頭50件のみ処理
python scripts/maintenance/offload_battle_logs_to_gcs.py --limit 50

# 全件処理（確認プロンプトあり）
python scripts/maintenance/offload_battle_logs_to_gcs.py

# #489で退避・削除された巨大行をローカルバックアップから復元する場合
python scripts/maintenance/offload_battle_logs_to_gcs.py --restore-archived --dry-run
```

`BATTLE_LOG_GCS_BUCKET` 環境変数でアップロード先バケットを指定します。

## オプション

| オプション | 説明 |
|---|---|
| `--dry-run` | 対象件数を表示するだけで実際にはアップロード・更新しない |
| `--limit N` | 1回の実行で処理する件数の上限 |
| `--yes` / `-y` | 確認プロンプトをスキップして即座に実行 |
| `--restore-archived` | `gcs_path`未設定の通常行ではなく、#489で退避・削除された巨大行の復元モードに切り替える。`battle_results.battle_log_id`の再リンクは行わず、候補を表示するのみ（手動確認が必要） |

---

# sync_mobile_suit_en.py

機体マスター（`master_mobile_suits.specs`）の `max_en` / `en_recovery` を、作成済みの機体（`mobile_suits`）へ同期するスクリプトです（Issue #675）。
機体の EN は購入・作成時のコピーなので、機体マスターの EN を変えたあとに実行します。同期先とルールは `docs/features/admin-mobile-suits.md` を参照してください。

> ⚠️ `--apply` を付けると実DB（Neon）へ書き込みます。本番に対しては、読み取りのみの実行結果を確認・承認してから実行してください。

## 使い方

```bash
cd backend

# 全機体マスターの差分を表示するだけ（書き込まない）
python scripts/maintenance/sync_mobile_suit_en.py

# 機体マスターを絞る（複数指定・カンマ区切りも可。練習機は gm_trainer / zaku_ii_trainer）
python scripts/maintenance/sync_mobile_suit_en.py --master-id gm,zaku_ii

# NPC機も同期する
python scripts/maintenance/sync_mobile_suit_en.py --include-npc

# 書き込む（確認プロンプトあり）
python scripts/maintenance/sync_mobile_suit_en.py --apply
```

## GitHub Actions から実行する

ローカルの `backend/.env` が無くても、Actions の `Sync Mobile Suit EN`（`.github/workflows/sync-mobile-suit-en.yml`）から手動で実行できます。接続先は `secrets.NEON_DATABASE_URL` です。

1. Actions の画面で `Sync Mobile Suit EN` を選び、`Run workflow` を押す。
2. `master_ids`（カンマ区切り）を必要なら入力する。空なら全機体マスター。NPC機も同期するなら `include_npc` を `true` にする。
3. `apply` は既定で `false`（差分の表示のみ）。まずこのまま実行し、ジョブサマリーの差分を確認する。
4. 差分を承認したら、同じ入力で `apply` を `true` にして再実行する。書き込む前に同じ形式で差分が出るので、確認時との一致を見られる。

実行ログとジョブサマリーに、実行者・入力値・差分が残ります。不正な機体マスターIDを指定するとジョブは失敗します。同時に実行できるのは1つだけです。

## オプション

| オプション | 説明 |
|---|---|
| `--master-id ID` | 対象の機体マスターID・練習機ID。複数指定・カンマ区切り可。省略すると全件 |
| `--include-npc` | NPC機（`user_id` が `npc-` で始まる）も同期する。付けなければ差分の件数だけ表示する |
| `--apply` | 書き込む。付けなければ差分の表示のみ |
| `--yes` / `-y` | `--apply` の確認プロンプトを省く |

## 出力の読み方

```
== mobile_suits（プレイヤー機）（12 行）
  gm / en_recovery: 100 → 40 (8件)
  zaku_ii / en_recovery: 100 → 40 (4件)
```

- 同期先ごとに、更新する行数と「機体マスターID / フィールド: 変更前 → 変更後 (件数)」を表示します。
- 何度実行しても結果は同じです。同期済みなら「変更なし」と表示します。
- コピー元は `master_mobile_suit_id` → 機体名が一致する機体マスターの順に引きます。練習機も機体マスターにあります（Issue #680）。機体名を変えた機体は、`master_mobile_suit_id` が無いと対象外です。
- エース機（`ace_pilots`）は対象外です。エース専用の EN は管理画面で設定してください。
- バトルエントリー済みの機体は、エントリー時のスナップショット（`mobile_suit_snapshot`）で戦うため、次のエントリーから反映されます。

---

# sync_weapon_master.py

武器マスター（`master_weapons`）の値を、武器スペックのコピーを持つデータへ同期するスクリプトです（Issue #656）。
バランス調整で武器マスターを変えたあとに実行します。同期先とルールは `docs/features/weapon-data-model.md` を参照してください。

> ⚠️ `--apply` を付けると実DB（Neon）へ書き込みます。本番に対しては、読み取りのみの実行結果を確認・承認してから実行してください。

## 使い方

```bash
cd backend

# 全武器の差分を表示するだけ（書き込まない）
python scripts/maintenance/sync_weapon_master.py

# 武器を絞る（複数指定・カンマ区切りも可）
python scripts/maintenance/sync_weapon_master.py --weapon-id giant_bazooka

# 同期するフィールドを絞る
python scripts/maintenance/sync_weapon_master.py --weapon-id giant_bazooka --fields max_ammo

# 書き込む（確認プロンプトあり）
python scripts/maintenance/sync_weapon_master.py --weapon-id giant_bazooka --apply
```

## GitHub Actions から実行する

ローカルの `backend/.env` が無くても、Actions の `Sync Weapon Master`（`.github/workflows/sync-weapon-master.yml`）から手動で実行できます。接続先は `secrets.NEON_DATABASE_URL` です。

1. Actions の画面で `Sync Weapon Master` を選び、`Run workflow` を押す。
2. `weapon_ids`（カンマ区切り）と `fields`（カンマ区切り）を必要なら入力する。空なら全武器・全フィールド。
3. `apply` は既定で `false`（差分の表示のみ）。まずこのまま実行し、ジョブサマリーの差分を確認する。
4. 差分を承認したら、同じ入力で `apply` を `true` にして再実行する。書き込む前に同じ形式で差分が出るので、確認時との一致を見られる。

実行ログとジョブサマリーに、実行者・入力値・差分が残ります。不正な武器IDやフィールドを指定するとジョブは失敗します。同時に実行できるのは1つだけです。

## オプション

| オプション | 説明 |
|---|---|
| `--weapon-id ID` | 対象の武器マスターID。複数指定・カンマ区切り可。省略すると全武器 |
| `--fields F1,F2` | 同期するフィールド。省略すると全スペックフィールドと `name` |
| `--apply` | 書き込む。付けなければ差分の表示のみ |
| `--yes` / `-y` | `--apply` の確認プロンプトを省く |

## 出力の読み方

```
== player_weapons.base_snapshot（23 行）
  giant_bazooka / max_ammo: None → 8 (23件)
```

- 同期先ごとに、更新する行数と「武器ID / フィールド: 変更前 → 変更後 (件数)」を表示します。
- 何度実行しても結果は同じです。同期済みなら「変更なし」と表示します。
- 購入した武器のスロットは、バトルエントリー時と同じ `resync_mobile_suit_weapons` で作り直します。そのため、`--fields` で絞っても、未反映だった改造差分などほかのフィールドが変わることがあります（表示に出ます）。
- エースパイロットの武器は更新せず、差分の件数だけを表示します。
- ショップの表示は、backend のマスターデータのキャッシュ（`MASTER_DATA_CACHE_TTL_SEC`、既定60秒）が切れるまで古い値のままです。

---

# backfill_weapon_power_bonus.py

機体強化（`weapon_power`）の加算値を既存の機体から推定し、`mobile_suits.weapon_power_bonus` に設定するスクリプトです（Issue #657）。
マイグレーション `o9c0d1e2f3a4`（`weapon_power_bonus` の追加）を当てたあと、1回だけ実行します。推定のしかたは `docs/features/weapon-data-model.md` の「機体強化の加算値を機体に持つ」を参照してください。

> ⚠️ `--apply` を付けると実DB（Neon）へ書き込みます。本番に対しては、読み取りのみの実行結果を確認・承認してから実行してください。

> ⚠️ `sync_weapon_master.py` より先に実行してください。武器マスターの同期は初期装備の威力をマスターの値に戻すため、推定に使う差が消えます。

## 使い方

```bash
cd backend

# 推定結果を表示するだけ（書き込まない）
python scripts/maintenance/backfill_weapon_power_bonus.py

# 書き込む（確認プロンプトあり）
python scripts/maintenance/backfill_weapon_power_bonus.py --apply
```

## オプション

| オプション | 説明 |
|---|---|
| `--apply` | 書き込む。付けなければ推定結果の表示のみ |
| `--yes` / `-y` | `--apply` の確認プロンプトを省く |

## 出力の読み方

```
3f2c...  Zaku II (user: user_xxx)
  加算値: 6  スロットごとの差: [6, 0, ?]
```

- スロットごとの差は「威力 − 加算前の威力」です。`?` は加算前の威力が分からないスロット（武器マスターに無い武器、加算前から上限以上の武器）です。
- 購入した武器のスロットの差が 0 なのは、resync で加算が消えたためです。書き込むと resync でこのスロットに加算を戻します。
- 「※差がスロット間で揃っていません」と出た機体は、武器マスターの威力を後から変えた可能性があります。差の最大値を加算値にしているので、必要なら管理画面などで直してください。
- 対象は `weapon_power_bonus` が 0 のプレイヤー機体だけです。2回目以降の実行では、設定済みの機体は表示されません。

---

# backfill_trainer_master_id.py

所持している練習機の `mobile_suits.master_mobile_suit_id` に、練習機の機体マスターIDを設定するスクリプトです（Issue #680）。
マイグレーション `r3f4a5b6c7d8`（練習機を機体マスターへ投入）を当てたあと、1回だけ実行します。
詳細は `docs/features/admin-mobile-suits.md` の「練習機（初期支給機体）」を参照してください。

> ⚠️ `--apply` を付けると実DB（Neon）へ書き込みます。本番に対しては、読み取りのみの実行結果を確認・承認してから実行してください。

## 使い方

```bash
cd backend

# 設定する件数を表示するだけ（書き込まない）
python scripts/maintenance/backfill_trainer_master_id.py

# 書き込む（確認プロンプトあり）
python scripts/maintenance/backfill_trainer_master_id.py --apply
```

## オプション

| オプション | 説明 |
|---|---|
| `--apply` | 書き込む。付けなければ件数の表示のみ |
| `--yes` / `-y` | `--apply` の確認プロンプトを省く |

## 出力の読み方

```
== mobile_suits.master_mobile_suit_id（3 行）
  MS-06T Zaku II Trainer: NULL → zaku_ii_trainer (2件)
  RGM-79T GM Trainer: NULL → gm_trainer (1件)
```

- 対象は `master_mobile_suit_id` が NULL で、機体名が練習機の機体マスターと一致する機体です。機体名を変えた練習機は対象外です。
- `user_id` が NULL の機体（マッチング時に作られるエース機のコピーなど）は対象外です。
- 何度実行しても結果は同じです。設定済みなら「変更なし」と表示します。

---

# export_master_data.py

DB のマスターデータを JSON に書き出すスクリプトです。
対象は6つのマスター（機体・武器・エースパイロット・技術・環境タイプ・戦域）と、設計図マスター（`blueprints.json`。購入に必要な技術Lvを含む）です。

マスターの正本は DB です。書き出したデータは `seed_master_data.py --data-dir` で新しい環境へ投入したり、計測ツールの `--master-dir` に渡したりします。
**書き出したデータは Git に入れません**（Git に残すと、再び DB とずれる JSON になるため）。既定の出力先は `.gitignore` 対象です。

## 使い方

```bash
cd backend

# 本番 DB から読み取り専用で書き出す（NEON_READONLY_DATABASE_URL を使う）
python scripts/maintenance/export_master_data.py

# 出力先を指定する
python scripts/maintenance/export_master_data.py --output-dir /tmp/master

# 本番以外の DB から書き出す
python scripts/maintenance/export_master_data.py --database-url sqlite:///./dev.db

# 書き出したデータを空の DB へ投入する
DATABASE_URL=sqlite:///./dev.db python scripts/seed/seed_master_data.py
```

## オプション

| オプション | 説明 |
|---|---|
| `--output-dir` | 出力先。既定は `scripts/maintenance/output/master_data/` |
| `--database-url` | 本番 DB の代わりに読む DB の URL。省略時は `NEON_READONLY_DATABASE_URL`（SELECT 権限だけのロール）で読み取り専用の接続を使う |

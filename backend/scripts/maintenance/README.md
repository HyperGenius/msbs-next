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

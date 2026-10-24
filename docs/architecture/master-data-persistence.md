# マスターデータ永続化 — Postgres テーブル移行ガイド

## 概要

機体・武器のマスターデータを Docker イメージ同梱 JSON から Neon Postgres テーブルへ移行。
管理画面で変更したデータがデプロイを跨いで永続化される。

## 正本は DB

マスターデータの正本は DB（`master_*` テーブル・`ace_pilots`）である。
対象は機体・武器・エースパイロット・技術・環境タイプ・戦域の6つと、付随する設計図マスター。

* 値を変えるときは、管理画面か `backend/scripts/maintenance/` のスクリプトで DB を直す。
* ゲーム本体（`backend/app`）は DB だけを読む。
* JSON は Git に置かない。かつて `backend/data/master/` に JSON があったが、本番 DB に自動で反映されず、管理画面の変更も戻らないため、値がずれた（Issue #659 で廃止）。
* `backend/tests/fixtures/master/` の JSON はテスト専用の固定データで、本番の値とは一致させない。

`backend/data/master/` に残る `backgrounds.json`・`thresholds.json` は DB テーブルを持たず、実行時に読む JSON が正本である。

## 新規テーブル

### `master_mobile_suits`

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | TEXT PRIMARY KEY | スネークケース ID（例: `rx_78_2`） |
| `name` | TEXT NOT NULL | 機体名 |
| `price` | INTEGER NOT NULL | 購入価格 |
| `faction` | TEXT NOT NULL DEFAULT '' | 勢力（FEDERATION / ZEON / 空文字=共通） |
| `description` | TEXT NOT NULL | 説明文 |
| `specs` | JSONB NOT NULL | `MasterMobileSuitSpec` の全フィールド |
| `created_at` | TIMESTAMPTZ | 作成日時 |
| `updated_at` | TIMESTAMPTZ | 更新日時 |

### `master_weapons`

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | TEXT PRIMARY KEY | スネークケース ID（例: `zaku_mg`） |
| `name` | TEXT NOT NULL | 武器名 |
| `price` | INTEGER NOT NULL | 購入価格 |
| `description` | TEXT NOT NULL | 説明文 |
| `weapon` | JSONB NOT NULL | `Weapon` モデルの全フィールド |
| `created_at` | TIMESTAMPTZ | 作成日時 |
| `updated_at` | TIMESTAMPTZ | 更新日時 |

## セットアップ手順

### 1. マイグレーション実行

```bash
cd backend
alembic upgrade head
```

マイグレーションファイル: `alembic/versions/r1s2t3u4v5w6_add_master_mobile_suits_and_weapons_tables.py`

### 2. マスターデータの投入（新しい環境）

新しい環境（開発用 DB など）は「本番から書き出す → 投入する」の手順で作る。

```bash
# 1. 本番 DB から読み取り専用で書き出す（NEON_READONLY_DATABASE_URL を使う）
python scripts/maintenance/export_master_data.py
#    出力先: scripts/maintenance/output/master_data/（.gitignore 対象）

# 2. 空の DB へ投入する（既存レコードはスキップ）
DATABASE_URL="postgresql://..." python scripts/seed/seed_master_data.py

# 本番に繋げない場合は、テスト用データで投入する（値は本番と一致しない）
DATABASE_URL="postgresql://..." python scripts/seed/seed_master_data.py --data-dir tests/fixtures/master
```

**書き出す内容**: 6つのマスターの JSON と `blueprints.json`（設計図マスターと、購入に必要な技術Lv）。
`blueprints.json` が無いディレクトリを投入したときは、新規の機体・武器に標準配備の設計図マスターを作る。

**環境変数**:
- `NEON_READONLY_DATABASE_URL`: 書き出し元。SELECT 権限だけのロールの接続 URL（`--database-url` で別の DB から書き出せる）
- `DATABASE_URL`: 投入先の接続 URL（`postgresql://...`）
- `NEON_DATABASE_URL`: 投入先の代替環境変数（`DATABASE_URL` が未設定の場合に参照）。チーム共有の本番 DB を指すので注意する

**べき等性**: 同一コマンドを複数回実行しても重複 INSERT しない（既存レコードはスキップ）。

**`--force` は本番 DB に使わない**: 既存レコード（管理画面で変更した値を含む）を上書きする。開発環境のリセット用。

書き出したデータは Git に入れない。Git に残すと、再び DB とずれる JSON になるため。

## キャッシュ設計

- `gamedata.py` は DB クエリ結果を TTL キャッシュとして保持
- デフォルト TTL: 60 秒（環境変数 `MASTER_DATA_CACHE_TTL_SEC` で変更可能）
- `GET /api/admin/reload-master` でキャッシュをクリアし、最新データを返す

```bash
# テスト環境でキャッシュを無効化
MASTER_DATA_CACHE_TTL_SEC=0 python -m uvicorn main:app
```

## 後方互換性

- `backgrounds.json` は変更なし（ファイルのまま）
- `STARTER_KITS`（練習機）は当時ハードコードのまま残したが、Issue #680 で `master_mobile_suits` の行（`is_trainer` / `starter_faction`）に移した。詳細は [admin-mobile-suits.md](../features/admin-mobile-suits.md) の「練習機（初期支給機体）」
- `_get_shop_listings()` / `_get_weapon_shop_listings()` はシグネチャ変更なし
- `SHOP_LISTINGS` / `WEAPON_SHOP_LISTINGS` 変数は引き続き `_LazyListProxy` で提供

## 関連ファイル

| ファイル | 説明 |
|---------|------|
| `backend/app/models/models.py` | `MasterMobileSuit` / `MasterWeapon` テーブルモデルを追加 |
| `backend/app/core/gamedata.py` | DB 参照・TTL キャッシュに切り替え |
| `backend/app/services/mobile_suit_service.py` | DB CRUD に変更 |
| `backend/app/services/weapon_service.py` | DB CRUD に変更 |
| `backend/app/routers/admin.py` | 全エンドポイントに `session: Session = Depends(get_session)` を追加 |
| `backend/scripts/maintenance/export_master_data.py` | DB のマスターを JSON に書き出す（既定は本番 DB を読み取り専用で読む） |
| `backend/scripts/seed/seed_master_data.py` | JSON ディレクトリから投入する（`--data-dir` / `--force`） |
| `backend/scripts/master_data.py` | JSON ディレクトリと DB の読み書き（書き出し・投入・計測ツールが共有） |
| `backend/alembic/versions/r1s2t3u4v5w6_*.py` | マイグレーションスクリプト |
| `backend/tests/fixtures/master/` | テスト専用の固定データ（本番の値とは一致させない） |
| `backend/tests/conftest.py` | StaticPool 共有エンジン + テスト用データの自動投入フィクスチャ |

# マスターデータ永続化 — Postgres テーブル移行ガイド

## 概要

機体・武器のマスターデータを Docker イメージ同梱 JSON から Neon Postgres テーブルへ移行。
管理画面で変更したデータがデプロイを跨いで永続化される。

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

### 2. シードデータ投入

```bash
# 既存レコードは上書きしない（管理画面変更を保護）
DATABASE_URL="postgresql://..." python scripts/seed/seed_master_data.py

# --force で既存レコードも上書き（開発環境リセット用）
DATABASE_URL="postgresql://..." python scripts/seed/seed_master_data.py --force
```

**環境変数**:
- `DATABASE_URL`: Neon Postgres の接続 URL（`postgresql://...`）
- `NEON_DATABASE_URL`: 代替環境変数（`DATABASE_URL` が未設定の場合に参照）

**べき等性**: 同一コマンドを複数回実行しても重複 INSERT しない（既存レコードはスキップ）。

## キャッシュ設計

- `gamedata.py` は DB クエリ結果を TTL キャッシュとして保持
- デフォルト TTL: 60 秒（環境変数 `MASTER_DATA_CACHE_TTL_SEC` で変更可能）
- `GET /api/admin/reload-master` でキャッシュをクリアし、最新データを返す

```bash
# テスト環境でキャッシュを無効化
MASTER_DATA_CACHE_TTL_SEC=0 python -m uvicorn main:app
```

## 後方互換性

- `backgrounds.json` と `STARTER_KITS` は変更なし（ファイル / ハードコードのまま）
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
| `backend/scripts/seed/seed_master_data.py` | シードスクリプト（`--force` フラグ対応） |
| `backend/alembic/versions/r1s2t3u4v5w6_*.py` | マイグレーションスクリプト |
| `backend/data/master/mobile_suits.json` | シードデータ（Git 管理継続） |
| `backend/data/master/weapons.json` | シードデータ（Git 管理継続） |
| `backend/tests/conftest.py` | StaticPool 共有エンジン + 自動シードフィクスチャ |

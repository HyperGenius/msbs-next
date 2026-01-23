# Neon Database Migration Guide

本プロジェクトでは、データベースを Supabase (HTTP/PostgREST) から Neon (PostgreSQL/SQLAlchemy) へ移行しました。
このドキュメントは、その移行手順と構成、運用方法をまとめたものです。

## 1. Infrastructure Setup (Terraform)

Neon のプロジェクト、ロール、データベースは Terraform で管理されています。

* **Location**: `infra/neon/`
* **Resources**:
    * `neon_project`: プロジェクト定義 (Region: `aws-ap-southeast-1` / Singapore)
    * `neon_role`: DBオーナー定義
    * `neon_database`: データベース定義 (`msbs_db`)
* **Setup**:
    詳細な実行手順は [docs/infra.md](./infra.md) を参照してください。

## 2. Backend Architecture Changes

データアクセス層を刷新し、直接 DB 接続 (TCP) を行う標準的な Python Web API 構成に変更しました。

### Dependencies
`backend/requirements.txt` を更新:
* **Removed**: `supabase` (削除完了)
* **Added**:
    * `sqlmodel`: Pydantic と SQLAlchemy を統合した ORM
    * `psycopg2-binary`: PostgreSQL アダプタ
    * `alembic`: DBマイグレーションツール

### Code Changes
* **Connection (`app/db.py`)**:
    * `create_engine` (SQLAlchemy) を使用した接続プール管理に変更。
    * Dependency Injection 用の `get_session` 関数を提供。
* **Models (`app/models/models.py`)**:
    * Pydantic モデルを `SQLModel` (`table=True`) に書き換え。
    * `position` (Vector3) や `weapons` (List) は `sa_column=Column(JSON)` を使用して JSON 型として保存。

## 3. Database Migration (Alembic)

スキーマ変更の管理には Alembic を使用します。

### 環境設定
`backend/alembic/env.py` をカスタマイズし、以下を自動読み込みするように設定済みです:
1.  `backend/.env` (環境変数 `DATABASE_URL`)
2.  `app.models.models` (SQLModel メタデータ)

### マイグレーション手順 (Workflow)

モデル (`models.py`) を変更した際は、以下の手順でDBに反映します。

1.  **マイグレーションファイルの生成**
    ```bash
    cd backend
    alembic revision --autogenerate -m "変更内容の記述"
    ```
    * `backend/alembic/versions/` に新しい Python ファイルが生成されます。

2.  **生成ファイルの確認と修正 (重要)**
    * 生成されたファイルを確認し、**`import sqlmodel` が不足している場合は手動で追加**してください。
    * (Alembic + SQLModel の既知の問題により、`sqlmodel.sql.sqltypes` を使用しているのに関連 import が漏れることがあります)

3.  **マイグレーションの適用**
    ```bash
    alembic upgrade head
    ```

## 4. Troubleshooting

### `NameError: name 'sqlmodel' is not defined`
`alembic upgrade` 実行時にこのエラーが出た場合、生成されたマイグレーションファイル (`versions/xxxx.py`) の冒頭に `import sqlmodel` を追加してください。

### `DATABASE_URL not found`
`alembic` コマンドは `backend` ディレクトリ直下で実行してください。`env.py` は親ディレクトリの `.env` を探しに行きます。
import os
import sys
from logging.config import fileConfig

# .env を読み込むために必要
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# モデル定義を読み込むためにパスを追加
sys.path.append(os.getcwd())

# モデルをインポートしてテーブルを認識させる
from app.models import models  # noqa

# alembic
from alembic import context

# Alembic Config object
config = context.config

# .env ファイルを読み込む
load_dotenv()

# alembic.ini の設定を読み込む
fileConfig(config.config_file_name)  # type: ignore

# ターゲットのメタデータを指定（SQLModelの情報）
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # 環境変数からURLを取得
    url = os.environ.get("NEON_DATABASE_URL")
    if not url:
        raise ValueError("NEON_DATABASE_URL not found in .env")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # 環境変数からURLを取得して設定を上書き
    connectable = config.attributes.get("connection", None)

    if connectable is None:
        db_url = os.environ.get("NEON_DATABASE_URL")
        if not db_url:
            raise ValueError("NEON_DATABASE_URL not found in .env")

        # alembic.ini の設定を上書き
        config.set_main_option("sqlalchemy.url", db_url)

        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

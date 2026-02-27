# backend/app/db.py
import json
import os
from collections.abc import Generator
from typing import Any
from uuid import UUID

from dotenv import load_dotenv
from sqlmodel import Session, create_engine

# .envファイルを読み込む
load_dotenv()

url = os.environ.get("NEON_DATABASE_URL")

if not url:
    raise ValueError("NEON_DATABASE_URL is missing in .env file")


# --- 追加: JSONシリアライザ関数 ---
def json_serializer(obj: Any) -> str:
    """PydanticモデルをJSON互換のdictに変換してシリアライズする関数."""

    def default(o: Any) -> Any:
        # UUID型を文字列に変換
        if isinstance(o, UUID):
            return str(o)
        # model_dump (Pydantic v2) があれば使う
        if hasattr(o, "model_dump"):
            return o.model_dump()
        # dict (Pydantic v1) があれば使う
        if hasattr(o, "dict"):
            return o.dict()
        raise TypeError(
            f"Object of type {o.__class__.__name__} is not JSON serializable"
        )

    return json.dumps(obj, default=default)


# --------------------------------

# エンジンの作成
# json_serializer を指定して、Pydanticモデルをそのまま保存できるようにする
# pool_pre_ping: 接続使用前に有効性をチェック（古い接続を自動再接続）
# pool_recycle: 接続を定期的にリサイクル（3600秒 = 1時間）
# pool_size: プールに保持する接続数
# max_overflow: プールサイズを超えて作成できる追加接続数

# SQLiteの場合は pool_size と max_overflow を使用しない
engine_args = {
    "echo": os.environ.get("SQL_ECHO", "false").lower() == "true",
    "json_serializer": json_serializer,
}

if not url.startswith("sqlite"):
    engine_args.update(
        {
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "pool_size": 5,
            "max_overflow": 10,
        }
    )

engine = create_engine(url, **engine_args)


def get_session() -> Generator[Session, None, None]:
    """FastAPI Dependency Injection用のセッション生成関数."""
    with Session(engine) as session:
        yield session

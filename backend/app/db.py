# backend/app/db.py
import json
import os
from collections.abc import Generator
from typing import Any

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
engine = create_engine(url, echo=True, json_serializer=json_serializer)


def get_session() -> Generator[Session, None, None]:
    """FastAPI Dependency Injection用のセッション生成関数."""
    with Session(engine) as session:
        yield session

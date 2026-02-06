# backend/tests/conftest.py
import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

os.environ["CLERK_JWKS_URL"] = (
    "https://example.clerk.accounts.dev/.well-known/jwks.json"
)
os.environ["CLERK_PUBLISHABLE_KEY"] = "pk_test_mock"
os.environ["CLERK_SECRET_KEY"] = "sk_test_mock"
os.environ["NEON_DATABASE_URL"] = "sqlite://"

# 環境変数をセットした後に app をインポート
from app.db import get_session, json_serializer
from main import app


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    """テスト用のインメモリDBセッションを作成."""
    # SQLiteのインメモリDBを使用（json_serializerを追加）
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        json_serializer=json_serializer,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """DBセッションをオーバーライドしたテストクライアント."""

    def get_session_override() -> Session:
        return session

    app.dependency_overrides[get_session] = get_session_override

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

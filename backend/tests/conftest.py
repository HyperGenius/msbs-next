# backend/tests/conftest.py
import json
import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, delete
from sqlmodel.pool import StaticPool

os.environ["CLERK_JWKS_URL"] = (
    "https://example.clerk.accounts.dev/.well-known/jwks.json"
)
os.environ["CLERK_PUBLISHABLE_KEY"] = "pk_test_mock"
os.environ["CLERK_SECRET_KEY"] = "sk_test_mock"
os.environ["NEON_DATABASE_URL"] = "sqlite://"
# テスト中はキャッシュを常に無効化してDBから直接取得する
os.environ["MASTER_DATA_CACHE_TTL_SEC"] = "0"

# app.db をインポートして engine を StaticPool に差し替える（全セッションが同一インメモリDBを共有）
import app.db as app_db  # noqa: E402
from app.db import get_session, json_serializer  # noqa: E402

_test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    json_serializer=json_serializer,
)
# 差し替え: get_session() および _load_*_from_db() が同一エンジンを参照するようにする
app_db.engine = _test_engine

from main import app  # noqa: E402

# テーブルを一括作成
SQLModel.metadata.create_all(_test_engine)

_MASTER_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "master"


def _seed_master_data(session: Session) -> None:
    """master_mobile_suits / master_weapons テーブルにシードデータを投入する."""
    from app.models.models import MasterMobileSuit, MasterWeapon

    # --- mobile_suits ---
    ms_data = json.loads(
        (_MASTER_DATA_DIR / "mobile_suits.json").read_text(encoding="utf-8")
    )
    for item in ms_data:
        specs = dict(item["specs"])
        record = MasterMobileSuit(
            id=item["id"],
            name=item["name"],
            price=item["price"],
            faction=item.get("faction", ""),
            description=item["description"],
            specs=specs,
        )
        session.add(record)

    # --- weapons ---
    weapons_data = json.loads(
        (_MASTER_DATA_DIR / "weapons.json").read_text(encoding="utf-8")
    )
    for item in weapons_data:
        record = MasterWeapon(
            id=item["id"],
            name=item["name"],
            price=item["price"],
            description=item["description"],
            weapon=dict(item["weapon"]),
        )
        session.add(record)

    session.commit()


@pytest.fixture(autouse=True)
def setup_master_data_db() -> Generator[None, None, None]:
    """全テストの前に全DBテーブルをクリアし、マスターデータを再投入する.

    テスト間の完全な分離を保証する。
    """
    import app.core.gamedata as gd
    from app.models.models import (
        BattleEntry,
        BattleResult,
        BattleRoom,
        Friendship,
        Leaderboard,
        MasterMobileSuit,
        MasterWeapon,
        MobileSuit,
        Pilot,
        PlayerWeapon,
        Season,
        Team,
        TeamMember,
    )

    # キャッシュをリセット
    gd._shop_listings_cache = None
    gd._weapon_shop_listings_cache = None
    gd._cache_expires_at = None

    # 全テーブルをクリア（外部キー制約がない SQLite では順不同で削除可能）
    with Session(_test_engine) as seed_session:
        seed_session.exec(delete(TeamMember))
        seed_session.exec(delete(Team))
        seed_session.exec(delete(Friendship))
        seed_session.exec(delete(Leaderboard))
        seed_session.exec(delete(BattleEntry))
        seed_session.exec(delete(BattleRoom))
        seed_session.exec(delete(BattleResult))
        seed_session.exec(delete(PlayerWeapon))
        seed_session.exec(delete(MobileSuit))
        seed_session.exec(delete(Pilot))
        seed_session.exec(delete(Season))
        seed_session.exec(delete(MasterMobileSuit))
        seed_session.exec(delete(MasterWeapon))
        seed_session.commit()
        _seed_master_data(seed_session)

    yield

    # テスト後にキャッシュをリセット
    gd._shop_listings_cache = None
    gd._weapon_shop_listings_cache = None
    gd._cache_expires_at = None


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    """テスト用のインメモリDBセッションを作成."""
    with Session(_test_engine) as session:
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

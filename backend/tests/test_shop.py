"""ショップ機能のテスト."""

import uuid

from fastapi import status

from app.core.auth import get_current_user
from app.models.models import MobileSuit, Pilot
from main import app


def test_get_shop_listings(client, session):
    """ショップの商品一覧を取得できることをテスト（勢力フィルタリング含む）."""
    # 勢力なしパイロットを作成（全機体が返る）
    test_user_id = "test_user_listings"
    pilot = Pilot(
        user_id=test_user_id,
        name="Test Pilot",
        level=1,
        exp=0,
        credits=1000,
        faction="",
    )
    session.add(pilot)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.get("/api/shop/listings")
        assert response.status_code == status.HTTP_200_OK

        listings = response.json()
        assert len(listings) > 0

        # 最初の商品の構造をチェック
        first_item = listings[0]
        assert "id" in first_item
        assert "name" in first_item
        assert "price" in first_item
        assert "description" in first_item
        assert "specs" in first_item

        # specsの構造をチェック
        specs = first_item["specs"]
        assert "max_hp" in specs
        assert "armor" in specs
        assert "mobility" in specs
        assert "weapons" in specs
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_purchase_mobile_suit_success(client, session):
    """モビルスーツの購入が成功することをテスト."""
    # パイロットを作成
    test_user_id = "test_user_123"
    pilot = Pilot(
        user_id=test_user_id,
        name="Test Pilot",
        level=1,
        exp=0,
        credits=1000,
        faction="ZEON",
    )
    session.add(pilot)
    session.commit()

    # 認証の依存関係をオーバーライド
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post("/api/shop/purchase/zaku_ii")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "message" in data
        assert "mobile_suit_id" in data
        assert "remaining_credits" in data
        assert data["remaining_credits"] == 500  # 1000 - 500

        # DBに機体が追加されていることを確認
        mobile_suit_id = uuid.UUID(data["mobile_suit_id"])
        mobile_suit = session.get(MobileSuit, mobile_suit_id)
        assert mobile_suit is not None
        assert mobile_suit.user_id == test_user_id
        assert mobile_suit.name == "Zaku II"
    finally:
        # クリーンアップ
        app.dependency_overrides.pop(get_current_user, None)


def test_purchase_mobile_suit_insufficient_credits(client, session):
    """所持金不足で購入できないことをテスト."""
    # 所持金不足のパイロットを作成
    test_user_id = "test_user_456"
    pilot = Pilot(
        user_id=test_user_id,
        name="Poor Pilot",
        level=1,
        exp=0,
        credits=100,  # 500必要なのに100しかない
        faction="ZEON",
    )
    session.add(pilot)
    session.commit()

    # 認証の依存関係をオーバーライド
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post("/api/shop/purchase/zaku_ii")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "所持金が不足しています" in response.json()["detail"]
    finally:
        # クリーンアップ
        app.dependency_overrides.pop(get_current_user, None)


def test_purchase_mobile_suit_not_found(client, session):
    """存在しない商品の購入でエラーになることをテスト."""
    # パイロットを作成
    test_user_id = "test_user_789"
    pilot = Pilot(
        user_id=test_user_id,
        name="Test Pilot",
        level=1,
        exp=0,
        credits=10000,
        faction="ZEON",
    )
    session.add(pilot)
    session.commit()

    # 認証の依存関係をオーバーライド
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post("/api/shop/purchase/nonexistent_item")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "商品が見つかりません" in response.json()["detail"]
    finally:
        # クリーンアップ
        app.dependency_overrides.pop(get_current_user, None)


def test_shop_listings_filtered_by_faction(client, session):
    """勢力によってショップ商品がフィルタリングされることをテスト."""
    test_user_id = "test_user_faction"

    # 連邦軍パイロットを作成
    pilot = Pilot(
        user_id=test_user_id,
        name="Federation Pilot",
        level=1,
        exp=0,
        credits=10000,
        faction="FEDERATION",
    )
    session.add(pilot)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.get("/api/shop/listings")
        assert response.status_code == status.HTTP_200_OK

        listings = response.json()
        # 連邦軍パイロットはジオン専用機体（Zaku II, Dom, Gouf, Gelgoog）を見られない
        ids = [item["id"] for item in listings]
        assert "gundam" in ids  # 連邦専用機体は見える
        assert "gm" in ids  # 連邦専用機体は見える
        assert "zaku_ii" not in ids  # ジオン専用機体は見えない
        assert "dom" not in ids  # ジオン専用機体は見えない
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_purchase_faction_mismatch(client, session):
    """勢力が合致しない機体を購入しようとするとエラーになることをテスト."""
    test_user_id = "test_user_faction_mismatch"

    # ジオン軍パイロットを作成
    pilot = Pilot(
        user_id=test_user_id,
        name="Zeon Pilot",
        level=1,
        exp=0,
        credits=10000,
        faction="ZEON",
    )
    session.add(pilot)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        # ジオンパイロットが連邦専用機体（Gundam）を購入しようとする
        response = client.post("/api/shop/purchase/gundam")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "購入できません" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)

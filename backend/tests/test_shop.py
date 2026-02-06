"""ショップ機能のテスト."""

import uuid

from fastapi import status

from app.core.auth import get_current_user
from app.db import get_session
from app.models.models import MobileSuit, Pilot
from main import app


def test_get_shop_listings(client):
    """ショップの商品一覧を取得できることをテスト."""
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

"""武器ショップ機能のテスト."""

from fastapi import status

from app.core.auth import get_current_user
from app.models.models import MobileSuit, Pilot
from main import app


def test_get_weapon_listings(client):
    """武器ショップの商品一覧を取得できることをテスト."""
    response = client.get("/api/shop/weapons")
    assert response.status_code == status.HTTP_200_OK

    listings = response.json()
    assert len(listings) > 0

    # 最初の商品の構造をチェック
    first_item = listings[0]
    assert "id" in first_item
    assert "name" in first_item
    assert "price" in first_item
    assert "description" in first_item
    assert "weapon" in first_item

    # weaponの構造をチェック
    weapon = first_item["weapon"]
    assert "id" in weapon
    assert "name" in weapon
    assert "power" in weapon
    assert "range" in weapon
    assert "accuracy" in weapon
    assert "type" in weapon


def test_purchase_weapon_success(client, session):
    """武器の購入が成功することをテスト."""
    # パイロットを作成
    test_user_id = "test_user_weapon_123"
    pilot = Pilot(
        user_id=test_user_id,
        name="Test Pilot",
        level=1,
        exp=0,
        credits=1000,
        inventory={},
    )
    session.add(pilot)
    session.commit()

    # 認証の依存関係をオーバーライド
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post("/api/shop/purchase/weapon/zaku_mg")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "message" in data
        assert "weapon_id" in data
        assert "remaining_credits" in data
        assert data["weapon_id"] == "zaku_mg"
        assert data["remaining_credits"] == 800  # 1000 - 200

        # DBでインベントリが更新されていることを確認
        session.refresh(pilot)
        assert "zaku_mg" in pilot.inventory
        assert pilot.inventory["zaku_mg"] == 1
    finally:
        # クリーンアップ
        app.dependency_overrides.pop(get_current_user, None)


def test_purchase_weapon_insufficient_credits(client, session):
    """所持金不足で武器を購入できないことをテスト."""
    # 所持金不足のパイロットを作成
    test_user_id = "test_user_weapon_456"
    pilot = Pilot(
        user_id=test_user_id,
        name="Poor Pilot",
        level=1,
        exp=0,
        credits=50,  # 200必要なのに50しかない
        inventory={},
    )
    session.add(pilot)
    session.commit()

    # 認証の依存関係をオーバーライド
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post("/api/shop/purchase/weapon/zaku_mg")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "所持金が不足しています" in response.json()["detail"]
    finally:
        # クリーンアップ
        app.dependency_overrides.pop(get_current_user, None)


def test_purchase_weapon_not_found(client, session):
    """存在しない武器の購入でエラーになることをテスト."""
    # パイロットを作成
    test_user_id = "test_user_weapon_789"
    pilot = Pilot(
        user_id=test_user_id,
        name="Test Pilot",
        level=1,
        exp=0,
        credits=10000,
        inventory={},
    )
    session.add(pilot)
    session.commit()

    # 認証の依存関係をオーバーライド
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post("/api/shop/purchase/weapon/nonexistent_weapon")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "武器が見つかりません" in response.json()["detail"]
    finally:
        # クリーンアップ
        app.dependency_overrides.pop(get_current_user, None)


def test_equip_weapon_success(client, session):
    """武器の装備が成功することをテスト."""
    # パイロットを作成
    test_user_id = "test_user_equip_123"
    pilot = Pilot(
        user_id=test_user_id,
        name="Test Pilot",
        level=1,
        exp=0,
        credits=1000,
        inventory={"zaku_mg": 1},  # 武器を所持
    )
    session.add(pilot)

    # 機体を作成
    mobile_suit = MobileSuit(
        user_id=test_user_id,
        name="Test Zaku",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        weapons=[],  # 最初は武器なし
        side="PLAYER",
    )
    session.add(mobile_suit)
    session.commit()
    session.refresh(mobile_suit)

    # 認証の依存関係をオーバーライド
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.put(
            f"/api/mobile_suits/{mobile_suit.id}/equip",
            json={"weapon_id": "zaku_mg", "slot_index": 0},
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data["weapons"]) == 1
        assert data["weapons"][0]["id"] == "zaku_mg"
    finally:
        # クリーンアップ
        app.dependency_overrides.pop(get_current_user, None)


def test_equip_weapon_not_owned(client, session):
    """所持していない武器を装備しようとしてエラーになることをテスト."""
    # パイロットを作成（武器を所持していない）
    test_user_id = "test_user_equip_456"
    pilot = Pilot(
        user_id=test_user_id,
        name="Test Pilot",
        level=1,
        exp=0,
        credits=1000,
        inventory={},  # 武器なし
    )
    session.add(pilot)

    # 機体を作成
    mobile_suit = MobileSuit(
        user_id=test_user_id,
        name="Test Zaku",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        weapons=[],
        side="PLAYER",
    )
    session.add(mobile_suit)
    session.commit()
    session.refresh(mobile_suit)

    # 認証の依存関係をオーバーライド
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.put(
            f"/api/mobile_suits/{mobile_suit.id}/equip",
            json={"weapon_id": "zaku_mg", "slot_index": 0},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "この武器を所持していません" in response.json()["detail"]
    finally:
        # クリーンアップ
        app.dependency_overrides.pop(get_current_user, None)

"""ショップ機能のテスト."""

import uuid

from fastapi import status
from sqlmodel import select

from app.core.auth import get_current_user
from app.models.models import (
    BlueprintSource,
    MasterBlueprint,
    MobileSuit,
    Pilot,
)
from app.services.blueprint_service import UNAVAILABLE_UNLOCK_HINT, BlueprintService
from main import app


def _make_restricted(session, blueprint_id: str) -> None:
    blueprint = session.get(MasterBlueprint, blueprint_id)
    assert blueprint is not None
    blueprint.is_standard_issue = False
    session.add(blueprint)
    session.commit()


def _create_pilot(session, user_id: str, credits: int, faction: str = "") -> Pilot:
    pilot = Pilot(
        user_id=user_id,
        name="Test Pilot",
        level=1,
        exp=0,
        credits=credits,
        faction=faction,
    )
    session.add(pilot)
    session.commit()
    return pilot


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
        assert "name_ja" in first_item
        assert "model_number" in first_item
        assert "price" in first_item
        assert "description" in first_item
        assert "weapon_slot_count" in first_item
        assert "beam_generator_lv" in first_item
        assert "flavor_text" in first_item
        assert "specs" in first_item
        assert first_item["is_standard_issue"] is True
        assert first_item["is_unlocked"] is True
        assert first_item["unlock_hint"] is None

        # specsの構造をチェック
        specs = first_item["specs"]
        assert "max_hp" in specs
        assert "armor" in specs
        assert "mobility" in specs
        assert "weapons" in specs
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_shop_listings_includes_flavor_text(client, session):
    """シードデータに設定したフレーバーテキストがレスポンスに含まれることをテスト."""
    test_user_id = "test_user_flavor_text"
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

        listings = {item["id"]: item for item in response.json()}
        assert listings["zaku_ii"]["flavor_text"] == (
            "「まずはこいつで慣れておけ」"
            "——量産機ながら、あらゆる戦場に順応してきた実績が語る信頼性。"
        )
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
        assert mobile_suit.master_mobile_suit_id == "zaku_ii"
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


def test_shop_listings_unlock_states(client, session):
    """機体一覧で、標準配備・設計図所持・未解放の状態が返ることをテスト."""
    test_user_id = "test_user_listing_unlock"
    _create_pilot(session, test_user_id, credits=10000)
    _make_restricted(session, "mobile_suit:gundam")
    _make_restricted(session, "mobile_suit:gelgoog")
    BlueprintService.grant_blueprint(
        session, test_user_id, "mobile_suit:gundam", BlueprintSource.DROP
    )
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: test_user_id
    try:
        response = client.get("/api/shop/listings")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_200_OK
    listings = {item["id"]: item for item in response.json()}
    assert listings["zaku_ii"]["is_standard_issue"] is True
    assert listings["zaku_ii"]["is_unlocked"] is True
    assert listings["zaku_ii"]["unlock_hint"] is None
    assert listings["gundam"]["is_standard_issue"] is False
    assert listings["gundam"]["is_unlocked"] is True
    assert listings["gundam"]["unlock_hint"] is None
    assert listings["gelgoog"]["is_standard_issue"] is False
    assert listings["gelgoog"]["is_unlocked"] is False
    assert listings["gelgoog"]["unlock_hint"] == UNAVAILABLE_UNLOCK_HINT


def test_purchase_mobile_suit_without_blueprint_forbidden(client, session):
    """設計図の無い非標準配備の機体は購入できず、クレジットが減らないことをテスト."""
    test_user_id = "test_user_purchase_locked_ms"
    pilot = _create_pilot(session, test_user_id, credits=10000)
    _make_restricted(session, "mobile_suit:gundam")

    app.dependency_overrides[get_current_user] = lambda: test_user_id
    try:
        response = client.post("/api/shop/purchase/gundam")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "この機体の設計図を所持していません"
    session.refresh(pilot)
    assert pilot.credits == 10000
    owned = session.exec(
        select(MobileSuit).where(MobileSuit.user_id == test_user_id)
    ).all()
    assert owned == []


def test_purchase_mobile_suit_with_blueprint(client, session):
    """設計図を所持していれば、非標準配備の機体を購入できることをテスト."""
    test_user_id = "test_user_purchase_unlocked_ms"
    pilot = _create_pilot(session, test_user_id, credits=10000)
    _make_restricted(session, "mobile_suit:gundam")
    BlueprintService.grant_blueprint(
        session, test_user_id, "mobile_suit:gundam", BlueprintSource.DROP
    )
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: test_user_id
    try:
        response = client.post("/api/shop/purchase/gundam")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_200_OK
    session.refresh(pilot)
    assert pilot.credits == 5000


def test_purchase_mobile_suit_faction_checked_before_blueprint(client, session):
    """勢力の判定が設計図の判定より先に行われることをテスト."""
    test_user_id = "test_user_faction_before_blueprint"
    _create_pilot(session, test_user_id, credits=10000, faction="ZEON")
    _make_restricted(session, "mobile_suit:gundam")

    app.dependency_overrides[get_current_user] = lambda: test_user_id
    try:
        response = client.post("/api/shop/purchase/gundam")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "勢力" in response.json()["detail"]


def test_purchase_mobile_suit_blueprint_checked_before_credits(client, session):
    """設計図の判定が所持金の判定より先に行われることをテスト."""
    test_user_id = "test_user_blueprint_before_credits"
    _create_pilot(session, test_user_id, credits=0)
    _make_restricted(session, "mobile_suit:gundam")

    app.dependency_overrides[get_current_user] = lambda: test_user_id
    try:
        response = client.post("/api/shop/purchase/gundam")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "この機体の設計図を所持していません"

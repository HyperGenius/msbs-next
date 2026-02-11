"""ショップ機能のAPIルーター."""

from datetime import UTC, datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.core.gamedata import (
    SHOP_LISTINGS,
    WEAPON_SHOP_LISTINGS,
    get_shop_listing_by_id,
    get_weapon_listing_by_id,
)
from app.db import get_session
from app.models.models import MobileSuit, Pilot, Weapon

router = APIRouter(prefix="/api/shop", tags=["shop"])


class ShopListingResponse(BaseModel):
    """ショップ商品のレスポンスモデル."""

    id: str
    name: str
    price: int
    description: str
    specs: dict


class PurchaseResponse(BaseModel):
    """購入レスポンスモデル."""

    message: str
    mobile_suit_id: str
    remaining_credits: int


class WeaponListingResponse(BaseModel):
    """武器商品のレスポンスモデル."""

    id: str
    name: str
    price: int
    description: str
    weapon: dict


class WeaponPurchaseResponse(BaseModel):
    """武器購入レスポンスモデル."""

    message: str
    weapon_id: str
    remaining_credits: int


@router.get("/listings", response_model=list[ShopListingResponse])
async def get_shop_listings() -> list[ShopListingResponse]:
    """ショップの商品一覧を取得する.

    Returns:
        list[ShopListingResponse]: 商品一覧
    """
    listings = []
    for item in SHOP_LISTINGS:
        # 型チェックのためのキャスト
        item = cast(dict[str, Any], item)
        # Weaponオブジェクトをdictに変換
        specs = cast(dict[str, Any], item["specs"]).copy()
        specs["weapons"] = [w.model_dump() for w in specs["weapons"]]

        listings.append(
            ShopListingResponse(
                id=cast(str, item["id"]),
                name=cast(str, item["name"]),
                price=cast(int, item["price"]),
                description=cast(str, item["description"]),
                specs=specs,
            )
        )

    return listings


@router.post("/purchase/{item_id}", response_model=PurchaseResponse)
async def purchase_mobile_suit(
    item_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> PurchaseResponse:
    """モビルスーツを購入する.

    Args:
        item_id: 購入する商品のID
        session: データベースセッション
        user_id: 現在のユーザーID

    Returns:
        PurchaseResponse: 購入結果

    Raises:
        HTTPException: 商品が存在しない、所持金不足などのエラー
    """
    # 1. 商品データを取得
    listing = get_shop_listing_by_id(item_id)
    if not listing:
        raise HTTPException(status_code=404, detail="商品が見つかりません")

    # 2. パイロット情報を取得
    statement = select(Pilot).where(Pilot.user_id == user_id)
    pilot = session.exec(statement).first()

    if not pilot:
        raise HTTPException(status_code=404, detail="パイロット情報が見つかりません")

    # 3. 所持金チェック
    if pilot.credits < listing["price"]:
        raise HTTPException(
            status_code=400,
            detail=f"所持金が不足しています。必要: {listing['price']} Credits, 所持: {pilot.credits} Credits",
        )

    # 4. 所持金を減算
    pilot.credits -= listing["price"]
    pilot.updated_at = datetime.now(UTC)

    # 5. 機体を生成
    specs = listing["specs"]
    new_mobile_suit = MobileSuit(
        user_id=user_id,
        name=listing["name"],
        max_hp=specs["max_hp"],
        current_hp=specs["max_hp"],
        armor=specs["armor"],
        mobility=specs["mobility"],
        sensor_range=specs["sensor_range"],
        beam_resistance=specs.get("beam_resistance", 0.0),
        physical_resistance=specs.get("physical_resistance", 0.0),
        weapons=specs["weapons"],
        side="PLAYER",
    )

    session.add(new_mobile_suit)
    session.commit()
    session.refresh(new_mobile_suit)
    session.refresh(pilot)

    return PurchaseResponse(
        message=f"{listing['name']}を購入しました！",
        mobile_suit_id=str(new_mobile_suit.id),
        remaining_credits=pilot.credits,
    )


@router.get("/weapons", response_model=list[WeaponListingResponse])
async def get_weapon_listings() -> list[WeaponListingResponse]:
    """武器ショップの商品一覧を取得する.

    Returns:
        list[WeaponListingResponse]: 武器商品一覧
    """
    listings = []
    for item in WEAPON_SHOP_LISTINGS:
        # 型チェックのためのキャスト
        item = cast(dict[str, Any], item)
        weapon = cast(Weapon, item["weapon"])

        listings.append(
            WeaponListingResponse(
                id=cast(str, item["id"]),
                name=cast(str, item["name"]),
                price=cast(int, item["price"]),
                description=cast(str, item["description"]),
                weapon=weapon.model_dump(),
            )
        )

    return listings


@router.post("/purchase/weapon/{weapon_id}", response_model=WeaponPurchaseResponse)
async def purchase_weapon(
    weapon_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> WeaponPurchaseResponse:
    """武器を購入する.

    Args:
        weapon_id: 購入する武器のID
        session: データベースセッション
        user_id: 現在のユーザーID

    Returns:
        WeaponPurchaseResponse: 購入結果

    Raises:
        HTTPException: 武器が存在しない、所持金不足などのエラー
    """
    # 1. 武器データを取得
    listing = get_weapon_listing_by_id(weapon_id)
    if not listing:
        raise HTTPException(status_code=404, detail="武器が見つかりません")

    # 2. パイロット情報を取得
    statement = select(Pilot).where(Pilot.user_id == user_id)
    pilot = session.exec(statement).first()

    if not pilot:
        raise HTTPException(status_code=404, detail="パイロット情報が見つかりません")

    # 3. 所持金チェック
    if pilot.credits < listing["price"]:
        raise HTTPException(
            status_code=400,
            detail=f"所持金が不足しています。必要: {listing['price']} Credits, 所持: {pilot.credits} Credits",
        )

    # 4. 所持金を減算
    pilot.credits -= listing["price"]

    # 5. インベントリに武器を追加
    if pilot.inventory is None:
        pilot.inventory = {}

    weapon_id_str = cast(str, listing["id"])
    current_count = pilot.inventory.get(weapon_id_str, 0)
    # 新しいdictオブジェクトを作成して代入（SQLModelのJSON変更検知のため）
    pilot.inventory = {**pilot.inventory, weapon_id_str: current_count + 1}

    pilot.updated_at = datetime.now(UTC)

    session.add(pilot)
    session.commit()
    session.refresh(pilot)

    return WeaponPurchaseResponse(
        message=f"{listing['name']}を購入しました！",
        weapon_id=weapon_id_str,
        remaining_credits=pilot.credits,
    )

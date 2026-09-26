"""ショップ機能のAPIルーター."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.core.gamedata import (
    SHOP_LISTINGS,
    WEAPON_SHOP_LISTINGS,
    get_shop_listing_by_id,
    get_weapon_listing_by_id,
    is_available_to_faction,
)
from app.db import get_session
from app.models.models import BlueprintTargetType, MobileSuit, Pilot, Weapon
from app.services.blueprint_service import BlueprintService
from app.services.weapon_service import WeaponService

router = APIRouter(prefix="/api/shop", tags=["shop"])


class ShopListingResponse(BaseModel):
    """ショップ商品のレスポンスモデル."""

    id: str
    name: str
    name_ja: str = ""
    model_number: str = ""
    price: int
    description: str
    weapon_slot_count: int = 1
    beam_generator_lv: int = 0
    flavor_text: str | None = None
    specs: dict
    is_standard_issue: bool
    is_unlocked: bool
    unlock_hint: str | None


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
    flavor_text: str | None = None
    weapon: dict
    is_standard_issue: bool
    is_unlocked: bool
    unlock_hint: str | None


class WeaponPurchaseResponse(BaseModel):
    """武器購入レスポンスモデル."""

    message: str
    weapon_id: str
    player_weapon_id: UUID
    remaining_credits: int


@router.get("/listings", response_model=list[ShopListingResponse])
async def get_shop_listings(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> list[ShopListingResponse]:
    """ショップの商品一覧を取得する（パイロットの勢力でフィルタリング）.

    Returns:
        list[ShopListingResponse]: 商品一覧
    """
    # パイロット情報を取得して勢力を確認
    statement = select(Pilot).where(Pilot.user_id == user_id)
    pilot = session.exec(statement).first()
    pilot_faction = pilot.faction if pilot else ""

    items = []
    for item in SHOP_LISTINGS:
        # 型チェックのためのキャスト
        item = cast(dict[str, Any], item)

        # 勢力フィルタリング: パイロットに勢力が設定されている場合、合致する機体のみ返す
        if not is_available_to_faction(
            pilot_faction, cast(str, item.get("faction", ""))
        ):
            continue
        items.append(item)

    unlock_states = BlueprintService.get_unlock_states(
        session,
        user_id,
        BlueprintTargetType.MOBILE_SUIT,
        [cast(str, item["id"]) for item in items],
    )

    listings = []
    for item in items:
        unlock_state = unlock_states[cast(str, item["id"])]

        # Weaponオブジェクトをdictに変換
        specs = cast(dict[str, Any], item["specs"]).copy()
        specs["weapons"] = [w.model_dump() for w in specs["weapons"]]

        listings.append(
            ShopListingResponse(
                id=cast(str, item["id"]),
                name=cast(str, item["name"]),
                name_ja=cast(str, item.get("name_ja", "")),
                model_number=cast(str, item.get("model_number", "")),
                price=cast(int, item["price"]),
                description=cast(str, item["description"]),
                weapon_slot_count=cast(int, item.get("weapon_slot_count", 1)),
                beam_generator_lv=cast(int, item.get("beam_generator_lv", 0)),
                flavor_text=cast(str | None, item.get("flavor_text")),
                specs=specs,
                is_standard_issue=unlock_state.is_standard_issue,
                is_unlocked=unlock_state.is_unlocked,
                unlock_hint=unlock_state.unlock_hint,
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
        HTTPException: 商品が存在しない、設計図が無い、所持金不足などのエラー
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

    # 3. 勢力バリデーション
    if not is_available_to_faction(pilot.faction, listing.get("faction", "")):
        raise HTTPException(
            status_code=403,
            detail=f"この機体はあなたの勢力（{pilot.faction}）では購入できません",
        )

    # 4. 設計図チェック
    if not BlueprintService.can_purchase(
        session, user_id, BlueprintTargetType.MOBILE_SUIT, item_id
    ):
        raise HTTPException(
            status_code=403, detail="この機体の設計図を所持していません"
        )

    # 5. 所持金チェック
    if pilot.credits < listing["price"]:
        raise HTTPException(
            status_code=400,
            detail=f"所持金が不足しています。必要: {listing['price']} Credits, 所持: {pilot.credits} Credits",
        )

    # 6. 所持金を減算
    pilot.credits -= listing["price"]
    pilot.updated_at = datetime.now(UTC)

    # 7. 機体を生成
    specs = listing["specs"]
    new_mobile_suit = MobileSuit(
        user_id=user_id,
        name=listing["name"],
        master_mobile_suit_id=listing["id"],
        max_hp=specs["max_hp"],
        current_hp=specs["max_hp"],
        armor=specs["armor"],
        mobility=specs["mobility"],
        sensor_range=specs["sensor_range"],
        beam_resistance=specs.get("beam_resistance", 0.0),
        physical_resistance=specs.get("physical_resistance", 0.0),
        melee_aptitude=specs.get("melee_aptitude", 1.0),
        shooting_aptitude=specs.get("shooting_aptitude", 1.0),
        accuracy_bonus=specs.get("accuracy_bonus", 0.0),
        evasion_bonus=specs.get("evasion_bonus", 0.0),
        acceleration_bonus=specs.get("acceleration_bonus", 1.0),
        turning_bonus=specs.get("turning_bonus", 1.0),
        weapons=specs["weapons"],
        missing_parts=specs.get("missing_parts", []),
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
async def get_weapon_listings(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> list[WeaponListingResponse]:
    """武器ショップの商品一覧を取得する.

    Returns:
        list[WeaponListingResponse]: 武器商品一覧
    """
    items = [cast(dict[str, Any], item) for item in WEAPON_SHOP_LISTINGS]
    unlock_states = BlueprintService.get_unlock_states(
        session,
        user_id,
        BlueprintTargetType.WEAPON,
        [cast(str, item["id"]) for item in items],
    )

    listings = []
    for item in items:
        weapon = cast(Weapon, item["weapon"])
        unlock_state = unlock_states[cast(str, item["id"])]

        listings.append(
            WeaponListingResponse(
                id=cast(str, item["id"]),
                name=cast(str, item["name"]),
                price=cast(int, item["price"]),
                description=cast(str, item["description"]),
                flavor_text=cast(str | None, item.get("flavor_text")),
                weapon=weapon.model_dump(),
                is_standard_issue=unlock_state.is_standard_issue,
                is_unlocked=unlock_state.is_unlocked,
                unlock_hint=unlock_state.unlock_hint,
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
        HTTPException: 武器が存在しない、設計図が無い、所持金不足などのエラー
    """
    player_weapon = WeaponService.purchase_weapon(session, user_id, weapon_id)

    # パイロット情報を取得してクレジットを返す（WeaponService 内で 404 が返るため None にはならない）
    pilot = session.exec(select(Pilot).where(Pilot.user_id == user_id)).first()

    listing = get_weapon_listing_by_id(weapon_id)
    weapon_name = listing["name"] if listing else weapon_id

    return WeaponPurchaseResponse(
        message=f"{weapon_name}を購入しました！",
        weapon_id=weapon_id,
        player_weapon_id=player_weapon.id,
        remaining_credits=pilot.credits,  # type: ignore[union-attr]
    )

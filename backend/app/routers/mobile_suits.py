# backend/app/routers/mobile_suits.py
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.core.gamedata import get_weapon_listing_by_id
from app.db import get_session
from app.engine.constants import MAX_WEAPON_SLOTS
from app.models.models import MobileSuit, MobileSuitUpdate, Pilot, Weapon
from app.services.mobile_suit_service import MobileSuitService

router = APIRouter(prefix="/api/mobile_suits", tags=["mobile_suits"])


class EquipWeaponRequest(BaseModel):
    """武器装備リクエストモデル."""

    weapon_id: str
    slot_index: int = 0


@router.get("/", response_model=list[MobileSuit])
def get_mobile_suits(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> list[MobileSuit]:
    """機体一覧取得."""
    return MobileSuitService.get_all_mobile_suits(session, user_id)


@router.put("/{ms_id}", response_model=MobileSuit)
async def update_mobile_suit(
    ms_id: str,
    ms_data: MobileSuitUpdate,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> MobileSuit:
    """機体更新."""
    updated_ms = MobileSuitService.update_mobile_suit(session, ms_id, ms_data)
    if not updated_ms:
        raise HTTPException(status_code=404, detail="Mobile Suit not found")
    return updated_ms


def _get_validated_mobile_suit(
    session: Session, ms_id: str, user_id: str
) -> MobileSuit:
    """機体を取得して所有者を検証する."""
    try:
        ms_uuid = uuid.UUID(ms_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="無効な機体IDです") from e

    mobile_suit = session.get(MobileSuit, ms_uuid)
    if not mobile_suit:
        raise HTTPException(status_code=404, detail="機体が見つかりません")

    if mobile_suit.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="この機体を編集する権限がありません"
        )
    return mobile_suit


def _validate_weapon_slot(slot_index: int) -> None:
    """武器スロットインデックスを検証する."""
    if slot_index < 0 or slot_index >= MAX_WEAPON_SLOTS:
        raise HTTPException(
            status_code=400,
            detail="スロットインデックスが範囲外です (有効: 0=メイン武器, 1=サブ武器)",
        )


def _validate_pilot_has_weapon(session: Session, user_id: str, weapon_id: str) -> None:
    """パイロットが指定の武器を所持しているか検証する."""
    statement = select(Pilot).where(Pilot.user_id == user_id)
    pilot = session.exec(statement).first()
    if not pilot:
        raise HTTPException(status_code=404, detail="パイロット情報が見つかりません")

    inventory = pilot.inventory or {}
    if inventory.get(weapon_id, 0) < 1:
        raise HTTPException(status_code=400, detail="この武器を所持していません")


def _get_weapon_id(weapon: object) -> str | None:
    """武器オブジェクト（またはdict）からIDを取得する."""
    if hasattr(weapon, "id"):
        return weapon.id  # type: ignore[union-attr]
    if isinstance(weapon, dict):
        return weapon.get("id")
    return None


def _validate_weapon_availability(
    session: Session,
    user_id: str,
    weapon_id: str,
    target_ms_id: uuid.UUID,
    slot_index: int,
) -> None:
    """武器の利用可能数を検証する.

    全機体の装備数を合計し、装備対象スロットに同じ武器が既にセットされている場合は
    1つ差し引いて（付け替えのため）、総所持数と比較する。
    """
    statement = select(Pilot).where(Pilot.user_id == user_id)
    pilot = session.exec(statement).first()
    if not pilot:
        raise HTTPException(status_code=404, detail="パイロット情報が見つかりません")

    total_owned = (pilot.inventory or {}).get(weapon_id, 0)

    # 全機体の装備数を集計（JSON保存のためweaponはdictで返る場合がある）
    ms_statement = select(MobileSuit).where(MobileSuit.user_id == user_id)
    all_mobile_suits = session.exec(ms_statement).all()
    total_equipped = sum(
        sum(
            1
            for w in (ms.weapons or [])
            if _get_weapon_id(w) == weapon_id
        )
        for ms in all_mobile_suits
    )

    # 装備対象スロットに既に同じ武器が入っている場合は付け替えなので1つ引く
    target_ms = session.get(MobileSuit, target_ms_id)
    if target_ms:
        current_weapons = target_ms.weapons or []
        if slot_index < len(current_weapons):
            if _get_weapon_id(current_weapons[slot_index]) == weapon_id:
                total_equipped -= 1

    available = total_owned - total_equipped
    if available < 1:
        raise HTTPException(status_code=400, detail="この武器の利用可能数が不足しています")


def _set_weapon_in_slot(
    mobile_suit: MobileSuit, slot_index: int, weapon_obj: Weapon
) -> None:
    """機体の指定スロットに武器をセットする."""
    new_weapons = list(mobile_suit.weapons or [])
    if slot_index >= len(new_weapons):
        new_weapons.append(weapon_obj)
    else:
        new_weapons[slot_index] = weapon_obj
    mobile_suit.weapons = new_weapons


@router.put("/{ms_id}/equip", response_model=MobileSuit)
async def equip_weapon(
    ms_id: str,
    equip_request: EquipWeaponRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> MobileSuit:
    """機体に武器を装備する.

    Args:
        ms_id: 機体ID
        equip_request: 装備する武器のID
        session: データベースセッション
        user_id: 現在のユーザーID

    Returns:
        MobileSuit: 更新された機体情報

    Raises:
        HTTPException: 機体が存在しない、武器を所持していないなどのエラー
    """
    mobile_suit = _get_validated_mobile_suit(session, ms_id, user_id)

    weapon_listing = get_weapon_listing_by_id(equip_request.weapon_id)
    if not weapon_listing:
        raise HTTPException(status_code=404, detail="武器が見つかりません")

    _validate_weapon_slot(equip_request.slot_index)
    _validate_pilot_has_weapon(session, user_id, equip_request.weapon_id)
    _validate_weapon_availability(
        session,
        user_id,
        equip_request.weapon_id,
        mobile_suit.id,
        equip_request.slot_index,
    )

    _set_weapon_in_slot(mobile_suit, equip_request.slot_index, weapon_listing["weapon"])

    session.add(mobile_suit)
    session.commit()
    session.refresh(mobile_suit)

    return mobile_suit

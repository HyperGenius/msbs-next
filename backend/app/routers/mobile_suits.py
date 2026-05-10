# backend/app/routers/mobile_suits.py
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.core.auth import get_current_user
from app.db import get_session
from app.models.models import (
    MobileSuit,
    MobileSuitResponse,
    MobileSuitUpdate,
)
from app.services.mobile_suit_service import MobileSuitService
from app.services.weapon_service import WeaponService

router = APIRouter(prefix="/api/mobile_suits", tags=["mobile_suits"])


class EquipWeaponRequest(BaseModel):
    """武器装備リクエストモデル."""

    player_weapon_id: uuid.UUID
    slot_index: int = 0


@router.get("", response_model=list[MobileSuitResponse])
def get_mobile_suits(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> list[MobileSuitResponse]:
    """機体一覧取得."""
    suits = MobileSuitService.get_all_mobile_suits(session, user_id)
    return [MobileSuitResponse.from_mobile_suit(ms) for ms in suits]


@router.put("/{ms_id}", response_model=MobileSuitResponse)
async def update_mobile_suit(
    ms_id: str,
    ms_data: MobileSuitUpdate,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> MobileSuitResponse:
    """機体更新."""
    updated_ms = MobileSuitService.update_mobile_suit(session, ms_id, ms_data)
    if not updated_ms:
        raise HTTPException(status_code=404, detail="Mobile Suit not found")
    return MobileSuitResponse.from_mobile_suit(updated_ms)


@router.put("/{ms_id}/equip", response_model=MobileSuitResponse)
async def equip_weapon(
    ms_id: str,
    equip_request: EquipWeaponRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> MobileSuitResponse:
    """機体に武器を装備する.

    Args:
        ms_id: 機体ID
        equip_request: 装備する武器インスタンスの UUID とスロット
        session: データベースセッション
        user_id: 現在のユーザーID

    Returns:
        MobileSuitResponse: 更新された機体情報

    Raises:
        HTTPException: 機体が存在しない、武器インスタンスが存在しないなどのエラー
    """
    try:
        ms_uuid = uuid.UUID(ms_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="無効な機体IDです") from e

    mobile_suit = WeaponService.equip_weapon(
        session,
        user_id,
        equip_request.player_weapon_id,
        ms_uuid,
        equip_request.slot_index,
    )

    return MobileSuitResponse.from_mobile_suit(mobile_suit)

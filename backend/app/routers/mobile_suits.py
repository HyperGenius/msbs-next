# backend/app/routers/mobile_suits.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.auth import get_current_user
from app.db import get_session
from app.models.models import MobileSuit, MobileSuitUpdate
from app.services.mobile_suit_service import MobileSuitService

router = APIRouter(prefix="/api/mobile_suits", tags=["mobile_suits"])


@router.get("/", response_model=list[MobileSuit])
def get_mobile_suits(session: Session = Depends(get_session)) -> list[MobileSuit]:
    """機体一覧取得."""
    return MobileSuitService.get_all_mobile_suits(session)


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

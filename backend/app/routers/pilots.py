"""パイロット情報のAPIルーター."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.db import get_session
from app.models.models import Pilot
from app.services.pilot_service import PilotService

router = APIRouter(prefix="/api/pilots", tags=["pilots"])


@router.get("/me", response_model=Pilot)
async def get_my_pilot(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> Pilot:
    """現在のユーザーのパイロット情報を取得する.

    Args:
        session: データベースセッション
        user_id: 現在のユーザーID

    Returns:
        Pilot: パイロット情報

    Raises:
        HTTPException: パイロットが見つからない場合
    """
    statement = select(Pilot).where(Pilot.user_id == user_id)
    pilot = session.exec(statement).first()

    if not pilot:
        # パイロットが見つからない場合は作成
        pilot_service = PilotService(session)
        pilot = pilot_service.get_or_create_pilot(user_id, "New Pilot")

    return pilot

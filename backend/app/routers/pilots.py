"""パイロット情報のAPIルーター."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.core.skills import get_all_skills
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


class SkillUnlockRequest(BaseModel):
    """スキル習得リクエスト."""

    skill_id: str


class SkillUnlockResponse(BaseModel):
    """スキル習得レスポンス."""

    pilot: Pilot
    message: str


@router.get("/skills", response_model=list)
async def get_skills() -> list:
    """利用可能なスキル一覧を取得する.

    Returns:
        list: スキル定義のリスト
    """
    return get_all_skills()


@router.post("/skills/unlock", response_model=SkillUnlockResponse)
async def unlock_skill(
    request: SkillUnlockRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> SkillUnlockResponse:
    """スキルを習得または強化する.

    Args:
        request: スキル習得リクエスト
        session: データベースセッション
        user_id: 現在のユーザーID

    Returns:
        SkillUnlockResponse: 習得後のパイロット情報とメッセージ

    Raises:
        HTTPException: パイロットが見つからない、またはスキル習得に失敗した場合
    """
    pilot_service = PilotService(session)

    # パイロット情報を取得
    statement = select(Pilot).where(Pilot.user_id == user_id)
    pilot = session.exec(statement).first()

    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")

    try:
        pilot, message = pilot_service.unlock_skill(pilot, request.skill_id)
        return SkillUnlockResponse(pilot=pilot, message=message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

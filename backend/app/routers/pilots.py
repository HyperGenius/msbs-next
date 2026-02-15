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


class CreatePilotRequest(BaseModel):
    """パイロット作成リクエスト."""

    name: str
    starter_unit_id: str = "zaku_ii"


@router.post("/create", response_model=Pilot)
async def create_pilot(
    request: CreatePilotRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> Pilot:
    """新規パイロットを作成し、選択したスターター機体を付与する.

    Args:
        request: パイロット作成リクエスト
        session: データベースセッション
        user_id: 現在のユーザーID

    Returns:
        Pilot: 作成されたパイロット情報

    Raises:
        HTTPException: パイロットが既に存在する、または無効なユニットIDの場合
    """
    # 既存のパイロットをチェック
    statement = select(Pilot).where(Pilot.user_id == user_id)
    existing_pilot = session.exec(statement).first()

    if existing_pilot:
        raise HTTPException(
            status_code=400, detail="Pilot already exists for this user"
        )

    # 有効なスターターユニットIDかチェック
    if request.starter_unit_id not in ["zaku_ii", "gm"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid starter unit ID: {request.starter_unit_id}. Must be 'zaku_ii' or 'gm'",
        )

    # パイロット作成
    pilot = Pilot(
        user_id=user_id,
        name=request.name,
        level=1,
        exp=0,
        credits=1000,
    )
    session.add(pilot)
    session.commit()
    session.refresh(pilot)

    # スターター機体を付与
    pilot_service = PilotService(session)
    pilot_service.create_starter_mobile_suit(user_id, request.starter_unit_id)

    return pilot


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
        raise HTTPException(
            status_code=404,
            detail="Pilot not found. Please create a pilot first using /api/pilots/create",
        )

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

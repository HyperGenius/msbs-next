"""パイロット情報のAPIルーター."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete
from sqlmodel import Session, col, select

from app.core.auth import get_current_user
from app.core.gamedata import get_starter_kit_by_faction
from app.core.skills import get_all_skills
from app.db import get_session
from app.models.models import BattleEntry, BattleResult, MobileSuit, Pilot
from app.services.pilot_service import PilotService

router = APIRouter(prefix="/api/pilots", tags=["pilots"])


class CreatePilotRequest(BaseModel):
    """パイロット作成リクエスト."""

    name: str
    starter_unit_id: str = "zaku_ii"


class RegisterPilotRequest(BaseModel):
    """パイロット登録リクエスト（オンボーディング用）."""

    name: str
    faction: str


class RegisterPilotResponse(BaseModel):
    """パイロット登録レスポンス."""

    pilot: dict
    mobile_suit_id: str
    message: str


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


@router.post("/register", response_model=RegisterPilotResponse)
async def register_pilot(
    request: RegisterPilotRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> RegisterPilotResponse:
    """新規パイロットを登録し、勢力に応じた練習機を付与する（オンボーディング用）.

    Args:
        request: パイロット登録リクエスト（name, faction）
        session: データベースセッション
        user_id: 現在のユーザーID

    Returns:
        RegisterPilotResponse: 作成されたパイロット情報と付与された機体のID

    Raises:
        HTTPException: パイロットが既に存在する、または無効な勢力の場合
    """
    # 既存のパイロットをチェック
    statement = select(Pilot).where(Pilot.user_id == user_id)
    existing_pilot = session.exec(statement).first()

    if existing_pilot:
        raise HTTPException(
            status_code=400, detail="Pilot already exists for this user"
        )

    # 有効な勢力かチェック
    valid_factions = ["FEDERATION", "ZEON"]
    if request.faction not in valid_factions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid faction: {request.faction}. Must be one of {valid_factions}",
        )

    # パイロット名のバリデーション
    name = request.name.strip()
    if not name or len(name) < 2 or len(name) > 15:
        raise HTTPException(
            status_code=400,
            detail="Pilot name must be between 2 and 15 characters",
        )

    # パイロット作成
    pilot = Pilot(
        user_id=user_id,
        name=name,
        faction=request.faction,
        level=1,
        exp=0,
        credits=1000,
    )
    session.add(pilot)
    session.commit()
    session.refresh(pilot)

    # 勢力に応じた練習機を取得
    starter_kit = get_starter_kit_by_faction(request.faction)
    if not starter_kit:
        raise HTTPException(
            status_code=500, detail="Starter kit not found for the specified faction"
        )

    specs = starter_kit["specs"]
    new_mobile_suit = MobileSuit(
        user_id=user_id,
        name=starter_kit["name"],
        max_hp=specs["max_hp"],
        current_hp=specs["max_hp"],
        armor=specs["armor"],
        mobility=specs["mobility"],
        sensor_range=specs.get("sensor_range", 500.0),
        beam_resistance=specs.get("beam_resistance", 0.0),
        physical_resistance=specs.get("physical_resistance", 0.0),
        melee_aptitude=specs.get("melee_aptitude", 1.0),
        shooting_aptitude=specs.get("shooting_aptitude", 1.0),
        accuracy_bonus=specs.get("accuracy_bonus", 0.0),
        evasion_bonus=specs.get("evasion_bonus", 0.0),
        acceleration_bonus=specs.get("acceleration_bonus", 1.0),
        turning_bonus=specs.get("turning_bonus", 1.0),
        weapons=specs["weapons"],
        side="PLAYER",
    )
    session.add(new_mobile_suit)
    session.commit()
    session.refresh(new_mobile_suit)
    session.refresh(pilot)

    return RegisterPilotResponse(
        pilot=pilot.model_dump(mode="json"),
        mobile_suit_id=str(new_mobile_suit.id),
        message=f"パイロット {name} を登録しました。{starter_kit['name']} を付与しました。",
    )


class PilotNameUpdateRequest(BaseModel):
    """パイロット名更新リクエスト."""

    name: str


@router.put("/me/name", response_model=Pilot)
async def update_pilot_name(
    request: PilotNameUpdateRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> Pilot:
    """現在のユーザーのパイロット名を更新する.

    Args:
        request: パイロット名更新リクエスト
        session: データベースセッション
        user_id: 現在のユーザーID

    Returns:
        Pilot: 更新後のパイロット情報

    Raises:
        HTTPException: パイロットが見つからない、またはバリデーションエラーの場合
    """
    statement = select(Pilot).where(Pilot.user_id == user_id)
    pilot = session.exec(statement).first()

    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")

    try:
        pilot_service = PilotService(session)
        pilot = pilot_service.update_pilot_name(pilot, request.name)
        return pilot
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class DeleteAccountResponse(BaseModel):
    """アカウント削除レスポンス."""

    message: str


@router.delete("/me", response_model=DeleteAccountResponse)
async def delete_my_account(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> DeleteAccountResponse:
    """現在のユーザーに紐づく全データを削除し、アカウントを初期状態にリセットする.

    削除対象: BattleEntry, BattleResult, MobileSuit, Pilot

    Args:
        session: データベースセッション
        user_id: 現在のユーザーID

    Returns:
        DeleteAccountResponse: 削除完了メッセージ

    Raises:
        HTTPException: 削除処理中にエラーが発生した場合
    """
    try:
        # 子レコードから順番にバルク削除（外部キー制約考慮）
        session.exec(delete(BattleEntry).where(col(BattleEntry.user_id) == user_id))
        session.exec(delete(BattleResult).where(col(BattleResult.user_id) == user_id))
        session.exec(delete(MobileSuit).where(col(MobileSuit.user_id) == user_id))
        session.exec(delete(Pilot).where(col(Pilot.user_id) == user_id))
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to reset account: {e}"
        ) from e

    return DeleteAccountResponse(message="アカウントを初期状態にリセットしました。")


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

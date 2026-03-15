"""パイロット情報のAPIルーター."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, or_
from sqlmodel import Session, col, select

from app.core.auth import get_current_user
from app.core.gamedata import get_background_by_id, get_starter_kit_by_faction
from app.core.skills import get_all_skills
from app.db import get_session
from app.models.models import (
    BattleEntry,
    BattleResult,
    Friendship,
    Leaderboard,
    MobileSuit,
    Pilot,
    Team,
    TeamMember,
)
from app.services.pilot_service import PilotService

router = APIRouter(prefix="/api/pilots", tags=["pilots"])


class RegisterPilotRequest(BaseModel):
    """パイロット登録リクエスト（オンボーディング用）."""

    name: str
    faction: str
    background: str
    bonus_dex: int = 0
    bonus_int: int = 0
    bonus_ref: int = 0
    bonus_tou: int = 0
    bonus_luk: int = 0


class RegisterPilotResponse(BaseModel):
    """パイロット登録レスポンス."""

    pilot: dict
    mobile_suit_id: str
    message: str


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
            detail="Pilot not found. Please register a pilot first using /api/pilots/register",
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

    # 経歴バリデーション
    background_data = get_background_by_id(request.background)
    if not background_data:
        valid_backgrounds = ["ACADEMY_ELITE", "STREET_SURVIVOR", "EX_MECHANIC"]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid background: {request.background}. Must be one of {valid_backgrounds}",
        )

    # ボーナスポイントバリデーション（合計5ポイント、各値0以上）
    bonus_points_total = 5
    bonus_values = [
        request.bonus_dex,
        request.bonus_int,
        request.bonus_ref,
        request.bonus_tou,
        request.bonus_luk,
    ]
    if any(v < 0 for v in bonus_values):
        raise HTTPException(
            status_code=400,
            detail="Bonus stat values must be non-negative",
        )
    if sum(bonus_values) != bonus_points_total:
        raise HTTPException(
            status_code=400,
            detail=f"Total bonus points must equal {bonus_points_total}",
        )

    base_stats = background_data["baseStats"]

    # パイロット作成
    pilot = Pilot(
        user_id=user_id,
        name=name,
        faction=request.faction,
        background=request.background,
        level=1,
        exp=0,
        credits=1000,
        dex=base_stats["DEX"] + request.bonus_dex,
        intel=base_stats["INT"] + request.bonus_int,
        ref=base_stats["REF"] + request.bonus_ref,
        tou=base_stats["TOU"] + request.bonus_tou,
        luk=base_stats["LUK"] + request.bonus_luk,
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

    削除対象: BattleEntry, BattleResult, MobileSuit, Pilot,
              TeamMember, Team, Friendship, Leaderboard

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

        # 自身がオーナーのチームに所属するメンバーレコードを削除
        owned_team_ids = select(Team.id).where(col(Team.owner_user_id) == user_id)
        session.exec(delete(TeamMember).where(col(TeamMember.team_id).in_(owned_team_ids)))
        # 自身がメンバーとして所属するレコードを削除
        session.exec(delete(TeamMember).where(col(TeamMember.user_id) == user_id))
        # 自身がオーナーのチームを削除
        session.exec(delete(Team).where(col(Team.owner_user_id) == user_id))

        # フレンド関係を削除
        session.exec(
            delete(Friendship).where(
                or_(
                    col(Friendship.user_id) == user_id,
                    col(Friendship.friend_user_id) == user_id,
                )
            )
        )

        # ランキングデータを削除
        session.exec(delete(Leaderboard).where(col(Leaderboard.user_id) == user_id))

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


class StatusAllocateRequest(BaseModel):
    """ステータスポイント割り振りリクエスト."""

    dex: int = 0
    intel: int = 0
    ref: int = 0
    tou: int = 0
    luk: int = 0


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


@router.post("/status/allocate", response_model=Pilot)
async def allocate_status_points(
    request: StatusAllocateRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> Pilot:
    """パイロットのステータスポイントを各ステータスへ割り振る.

    Args:
        request: 各ステータスへの割り振りポイント数
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
        pilot = pilot_service.allocate_status_points(
            pilot,
            dex=request.dex,
            intel=request.intel,
            ref=request.ref,
            tou=request.tou,
            luk=request.luk,
        )
        return pilot
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

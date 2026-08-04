"""プレイヤー武器インスタンス管理APIルーター."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.db import get_session
from app.models.models import Pilot, PlayerWeapon, PlayerWeaponResponse
from app.services.weapon_engineering_service import WeaponEngineeringService
from app.services.weapon_service import WeaponService

router = APIRouter(prefix="/api/player-weapons", tags=["player_weapons"])


class WeaponUpgradeRequest(BaseModel):
    """武器改造リクエスト."""

    target_stat: str  # "power_bonus" or "accuracy_bonus"
    steps: int = 1


class WeaponUpgradeResponse(BaseModel):
    """武器改造レスポンス."""

    message: str
    player_weapon: PlayerWeaponResponse
    remaining_credits: int
    cost_paid: int


class WeaponUpgradePreviewResponse(BaseModel):
    """武器改造プレビューレスポンス."""

    player_weapon_id: str
    stat_type: str
    current_value: int | float
    new_value: int | float
    cost: int
    at_max_cap: bool


@router.get("", response_model=list[PlayerWeaponResponse])
def list_player_weapons(
    unequipped: bool = Query(
        default=False, description="True の場合、未装備の武器のみ返す"
    ),
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> list[PlayerWeaponResponse]:
    """ログインユーザーの所有武器インスタンス一覧を返す.

    Args:
        unequipped: True の場合、未装備の武器のみ返す
        session: データベースセッション
        user_id: 現在のユーザーID

    Returns:
        list[PlayerWeaponResponse]: 所有武器インスタンス一覧
    """
    weapons = WeaponService.get_player_weapons(
        session, user_id, unequipped_only=unequipped
    )
    return [PlayerWeaponResponse.model_validate(w.model_dump()) for w in weapons]


@router.delete("/{pw_id}", status_code=204)
def delete_player_weapon(
    pw_id: uuid.UUID,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> None:
    """武器インスタンスを売却・破棄する.

    装備中の武器は削除できない（409 を返す）。

    Args:
        pw_id: 削除する PlayerWeapon の UUID
        session: データベースセッション
        user_id: 現在のユーザーID

    Raises:
        HTTPException: 武器が見つからない、権限なし、装備中などのエラー
    """
    player_weapon = session.get(PlayerWeapon, pw_id)
    if not player_weapon:
        raise HTTPException(status_code=404, detail="武器インスタンスが見つかりません")

    if player_weapon.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="この武器インスタンスへのアクセス権がありません"
        )

    if player_weapon.equipped_ms_id is not None:
        raise HTTPException(
            status_code=409, detail="装備中の武器は削除できません。先に外してください"
        )

    session.delete(player_weapon)
    session.commit()


@router.post("/{pw_id}/upgrade", response_model=WeaponUpgradeResponse)
def upgrade_player_weapon(
    pw_id: uuid.UUID,
    request: WeaponUpgradeRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> WeaponUpgradeResponse:
    """武器インスタンスの custom_stats（power_bonus / accuracy_bonus）を改造する.

    未装備の武器も改造可能。装備中の武器を改造した場合、バトル開始時に
    再同期される（再装備は不要）。

    Args:
        pw_id: 改造対象の PlayerWeapon の UUID
        request: 改造対象パラメータとステップ数
        session: データベースセッション
        user_id: 現在のユーザーID

    Returns:
        WeaponUpgradeResponse: 更新後の武器インスタンス、残クレジット、消費コスト

    Raises:
        HTTPException: パイロットが見つからない、武器が見つからない、権限なし、
            上限到達、所持金不足などのエラー
    """
    player_weapon = session.get(PlayerWeapon, pw_id)
    if not player_weapon:
        raise HTTPException(status_code=404, detail="武器インスタンスが見つかりません")
    if player_weapon.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="この武器インスタンスへのアクセス権がありません"
        )

    statement = select(Pilot).where(Pilot.user_id == user_id)
    pilot = session.exec(statement).first()
    if not pilot:
        raise HTTPException(status_code=404, detail="パイロット情報が見つかりません")

    service = WeaponEngineeringService(session)

    try:
        updated_pw, updated_pilot, cost = service.upgrade_stat(
            str(pw_id), request.target_stat, pilot, request.steps
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return WeaponUpgradeResponse(
        message="武器を改造しました！",
        player_weapon=PlayerWeaponResponse.model_validate(updated_pw.model_dump()),
        remaining_credits=updated_pilot.credits,
        cost_paid=cost,
    )


@router.get(
    "/{pw_id}/upgrade-preview/{stat_type}",
    response_model=WeaponUpgradePreviewResponse,
)
def get_weapon_upgrade_preview(
    pw_id: uuid.UUID,
    stat_type: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> WeaponUpgradePreviewResponse:
    """次の1ステップ改造した場合のコスト・変化後スペックのプレビューを返す.

    Args:
        pw_id: 対象の PlayerWeapon の UUID
        stat_type: "power_bonus" または "accuracy_bonus"
        session: データベースセッション
        user_id: 現在のユーザーID

    Returns:
        WeaponUpgradePreviewResponse: 現在値・改造後の値・コスト・上限到達フラグ

    Raises:
        HTTPException: 武器が見つからない、権限なし、stat_type不正などのエラー
    """
    player_weapon = session.get(PlayerWeapon, pw_id)
    if not player_weapon:
        raise HTTPException(status_code=404, detail="武器インスタンスが見つかりません")
    if player_weapon.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="この武器インスタンスへのアクセス権がありません"
        )

    service = WeaponEngineeringService(session)

    try:
        preview = service.get_upgrade_preview(str(pw_id), stat_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return WeaponUpgradePreviewResponse(
        player_weapon_id=str(pw_id),
        stat_type=stat_type,
        current_value=preview["current_value"],
        new_value=preview["new_value"],
        cost=preview["cost"],
        at_max_cap=preview["at_max_cap"],
    )

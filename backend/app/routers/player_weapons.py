"""プレイヤー武器インスタンス管理APIルーター."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.auth import get_current_user
from app.db import get_session
from app.models.models import PlayerWeapon, PlayerWeaponResponse
from app.services.weapon_service import WeaponService

router = APIRouter(prefix="/api/player-weapons", tags=["player_weapons"])


@router.get("", response_model=list[PlayerWeaponResponse])
def list_player_weapons(
    unequipped: bool = Query(default=False, description="True の場合、未装備の武器のみ返す"),
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
    weapons = WeaponService.get_player_weapons(session, user_id, unequipped_only=unequipped)
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
        raise HTTPException(status_code=403, detail="この武器インスタンスへのアクセス権がありません")

    if player_weapon.equipped_ms_id is not None:
        raise HTTPException(status_code=409, detail="装備中の武器は削除できません。先に外してください")

    session.delete(player_weapon)
    session.commit()

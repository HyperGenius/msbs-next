"""管理者専用 API ルーター.

マスター機体データおよびマスター武器データの CRUD エンドポイントを提供する。
全エンドポイントは ADMIN_API_KEY ヘッダー (X-API-Key) による認証が必要。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.auth import verify_admin_api_key
from app.db import get_session
from app.models.models import (
    MasterMobileSuitCreate,
    MasterMobileSuitEntry,
    MasterMobileSuitSpec,
    MasterMobileSuitUpdate,
    MasterWeaponCreate,
    MasterWeaponEntry,
    MasterWeaponUpdate,
    Weapon,
)
from app.services.mobile_suit_service import MobileSuitService
from app.services.weapon_service import WeaponService

router = APIRouter(
    prefix="/api/admin/mobile-suits",
    tags=["admin"],
    dependencies=[Depends(verify_admin_api_key)],
)


def _raw_to_entry(raw: dict) -> MasterMobileSuitEntry:
    """生JSON辞書を MasterMobileSuitEntry モデルに変換する."""
    specs_raw = raw["specs"]
    weapons = [
        Weapon(**w) if isinstance(w, dict) else w for w in specs_raw.get("weapons", [])
    ]
    specs = MasterMobileSuitSpec(
        max_hp=specs_raw["max_hp"],
        armor=specs_raw["armor"],
        mobility=specs_raw["mobility"],
        sensor_range=specs_raw.get("sensor_range", 500.0),
        beam_resistance=specs_raw.get("beam_resistance", 0.0),
        physical_resistance=specs_raw.get("physical_resistance", 0.0),
        melee_aptitude=specs_raw.get("melee_aptitude", 1.0),
        shooting_aptitude=specs_raw.get("shooting_aptitude", 1.0),
        accuracy_bonus=specs_raw.get("accuracy_bonus", 0.0),
        evasion_bonus=specs_raw.get("evasion_bonus", 0.0),
        acceleration_bonus=specs_raw.get("acceleration_bonus", 1.0),
        turning_bonus=specs_raw.get("turning_bonus", 1.0),
        weapons=weapons,
    )
    return MasterMobileSuitEntry(
        id=raw["id"],
        name=raw["name"],
        price=raw["price"],
        faction=raw.get("faction", ""),
        description=raw["description"],
        specs=specs,
    )


@router.get("", response_model=list[MasterMobileSuitEntry])
def list_master_mobile_suits() -> list[MasterMobileSuitEntry]:
    """全マスター機体一覧を返す."""
    raw_list = MobileSuitService.get_master_mobile_suits()
    return [_raw_to_entry(r) for r in raw_list]


@router.post(
    "", response_model=MasterMobileSuitEntry, status_code=status.HTTP_201_CREATED
)
def create_master_mobile_suit(data: MasterMobileSuitCreate) -> MasterMobileSuitEntry:
    """新規マスター機体を追加する.

    - 機体 id はスネークケース英数字のみ許可（例: rx_78_2）
    - weapons は最低1件必須
    - id が重複している場合は 409 を返す
    """
    try:
        result = MobileSuitService.create_master_mobile_suit(data)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e
    return _raw_to_entry(result)


@router.put("/{ms_id}", response_model=MasterMobileSuitEntry)
def update_master_mobile_suit(
    ms_id: str, data: MasterMobileSuitUpdate
) -> MasterMobileSuitEntry:
    """既存マスター機体を更新する.

    - weapons を更新する場合は最低1件必須
    """
    try:
        result = MobileSuitService.update_master_mobile_suit(ms_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master mobile suit '{ms_id}' not found.",
        )
    return _raw_to_entry(result)


@router.delete("/{ms_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_master_mobile_suit(
    ms_id: str,
    session: Session = Depends(get_session),
) -> None:
    """マスター機体を削除する.

    - ショップ在庫（購入済み機体）に参照がある場合は 409 を返す
    """
    try:
        deleted = MobileSuitService.delete_master_mobile_suit(ms_id, session)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master mobile suit '{ms_id}' not found.",
        )


# --- 武器マスターデータ CRUD ---

weapon_router = APIRouter(
    prefix="/api/admin/weapons",
    tags=["admin"],
    dependencies=[Depends(verify_admin_api_key)],
)


def _raw_to_weapon_entry(raw: dict) -> MasterWeaponEntry:
    """生JSON辞書を MasterWeaponEntry モデルに変換する."""
    weapon_raw = raw["weapon"]
    weapon = Weapon(**weapon_raw) if isinstance(weapon_raw, dict) else weapon_raw
    return MasterWeaponEntry(
        id=raw["id"],
        name=raw["name"],
        price=raw["price"],
        description=raw["description"],
        weapon=weapon,
    )


@weapon_router.get("", response_model=list[MasterWeaponEntry])
def list_master_weapons() -> list[MasterWeaponEntry]:
    """全マスター武器一覧を返す."""
    raw_list = WeaponService.get_master_weapons()
    return [_raw_to_weapon_entry(r) for r in raw_list]


@weapon_router.post(
    "", response_model=MasterWeaponEntry, status_code=status.HTTP_201_CREATED
)
def create_master_weapon(data: MasterWeaponCreate) -> MasterWeaponEntry:
    """新規マスター武器を追加する.

    - 武器 id はスネークケース英数字のみ許可（例: beam_rifle）
    - id が重複している場合は 409 を返す
    """
    try:
        result = WeaponService.create_master_weapon(data)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e
    return _raw_to_weapon_entry(result)


@weapon_router.put("/{weapon_id}", response_model=MasterWeaponEntry)
def update_master_weapon(
    weapon_id: str, data: MasterWeaponUpdate
) -> MasterWeaponEntry:
    """既存マスター武器を更新する."""
    result = WeaponService.update_master_weapon(weapon_id, data)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master weapon '{weapon_id}' not found.",
        )
    return _raw_to_weapon_entry(result)


@weapon_router.delete("/{weapon_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_master_weapon(
    weapon_id: str,
    session: Session = Depends(get_session),
) -> None:
    """マスター武器を削除する.

    - パイロットのインベントリに参照がある場合は 409 を返す
    """
    try:
        deleted = WeaponService.delete_master_weapon(weapon_id, session)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master weapon '{weapon_id}' not found.",
        )

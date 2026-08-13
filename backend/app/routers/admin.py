"""管理者専用 API ルーター.

マスター機体データ・マスター武器データ・NPC(Pilot)データの CRUD エンドポイントを提供する。
全エンドポイントは ADMIN_API_KEY ヘッダー (X-API-Key) による認証が必要。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.auth import verify_admin_api_key
from app.db import get_session
from app.models.models import (
    CombatSimulationRequest,
    CombatSimulationResponse,
    MasterMobileSuitCreate,
    MasterMobileSuitEntry,
    MasterMobileSuitSpec,
    MasterMobileSuitUpdate,
    MasterWeaponCreate,
    MasterWeaponEntry,
    MasterWeaponSpec,
    MasterWeaponUpdate,
    MobileSuitUpdate,
    NpcMobileSuitEntry,
    NpcPilotDetail,
    NpcPilotEntry,
    NpcPilotUpdate,
    Pilot,
    Weapon,
)
from app.services.combat_simulation_service import CombatSimulationService
from app.services.mobile_suit_service import MobileSuitService
from app.services.pilot_service import PilotService
from app.services.weapon_service import WeaponService

router = APIRouter(
    prefix="/api/admin/mobile-suits",
    tags=["admin"],
    dependencies=[Depends(verify_admin_api_key)],
)

weapon_router = APIRouter(
    prefix="/api/admin/weapons",
    tags=["admin-weapons"],
    dependencies=[Depends(verify_admin_api_key)],
)

simulation_router = APIRouter(
    prefix="/api/admin",
    tags=["admin-simulation"],
    dependencies=[Depends(verify_admin_api_key)],
)

npc_router = APIRouter(
    prefix="/api/admin/npcs",
    tags=["admin-npcs"],
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
        name_ja=raw.get("name_ja", ""),
        model_number=raw.get("model_number", ""),
        price=raw["price"],
        faction=raw.get("faction", ""),
        description=raw["description"],
        weapon_slot_count=raw.get("weapon_slot_count", 1),
        beam_generator_lv=raw.get("beam_generator_lv", 0),
        specs=specs,
    )


@router.get("", response_model=list[MasterMobileSuitEntry])
def list_master_mobile_suits(
    session: Session = Depends(get_session),
) -> list[MasterMobileSuitEntry]:
    """全マスター機体一覧を返す."""
    raw_list = MobileSuitService.get_master_mobile_suits(session)
    return [_raw_to_entry(r) for r in raw_list]


@router.post(
    "", response_model=MasterMobileSuitEntry, status_code=status.HTTP_201_CREATED
)
def create_master_mobile_suit(
    data: MasterMobileSuitCreate,
    session: Session = Depends(get_session),
) -> MasterMobileSuitEntry:
    """新規マスター機体を追加する.

    - 機体 id はスネークケース英数字のみ許可（例: rx_78_2）
    - weapons は最低1件必須
    - id が重複している場合は 409 を返す
    """
    try:
        result = MobileSuitService.create_master_mobile_suit(session, data)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e
    return _raw_to_entry(result)


@router.put("/{ms_id}", response_model=MasterMobileSuitEntry)
def update_master_mobile_suit(
    ms_id: str,
    data: MasterMobileSuitUpdate,
    session: Session = Depends(get_session),
) -> MasterMobileSuitEntry:
    """既存マスター機体を更新する.

    - weapons を更新する場合は最低1件必須
    """
    try:
        result = MobileSuitService.update_master_mobile_suit(session, ms_id, data)
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


# ===========================================================
# マスター武器データ CRUD エンドポイント
# ===========================================================


def _raw_weapon_to_entry(raw: dict) -> MasterWeaponEntry:
    """生JSON辞書を MasterWeaponEntry モデルに変換する."""
    weapon_raw = raw["weapon"]
    weapon = (
        MasterWeaponSpec(**weapon_raw) if isinstance(weapon_raw, dict) else weapon_raw
    )
    return MasterWeaponEntry(
        id=raw["id"],
        name=raw["name"],
        price=raw["price"],
        description=raw["description"],
        weapon=weapon,
    )


@weapon_router.get("", response_model=list[MasterWeaponEntry])
def list_master_weapons(
    session: Session = Depends(get_session),
) -> list[MasterWeaponEntry]:
    """全マスター武器一覧を返す."""
    raw_list = WeaponService.get_master_weapons(session)
    return [_raw_weapon_to_entry(r) for r in raw_list]


@weapon_router.post(
    "", response_model=MasterWeaponEntry, status_code=status.HTTP_201_CREATED
)
def create_master_weapon(
    data: MasterWeaponCreate,
    session: Session = Depends(get_session),
) -> MasterWeaponEntry:
    """新規マスター武器を追加する.

    - 武器 id はスネークケース英数字のみ許可（例: beam_rifle）
    - id が重複している場合は 409 を返す
    """
    try:
        result = WeaponService.create_master_weapon(session, data)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e
    return _raw_weapon_to_entry(result)


@weapon_router.put("/{weapon_id}", response_model=MasterWeaponEntry)
def update_master_weapon(
    weapon_id: str,
    data: MasterWeaponUpdate,
    session: Session = Depends(get_session),
) -> MasterWeaponEntry:
    """既存マスター武器を更新する."""
    result = WeaponService.update_master_weapon(session, weapon_id, data)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master weapon '{weapon_id}' not found.",
        )
    return _raw_weapon_to_entry(result)


@weapon_router.delete("/{weapon_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_master_weapon(
    weapon_id: str,
    session: Session = Depends(get_session),
) -> None:
    """マスター武器を削除する.

    - player_weapons テーブルで master_weapon_id として参照されている場合は 409 を返す
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


# ===========================================================
# 1対1 攻撃シミュレーション エンドポイント (Issue #381)
# ===========================================================


@simulation_router.post("/simulate-combat", response_model=CombatSimulationResponse)
def simulate_combat(data: CombatSimulationRequest) -> CombatSimulationResponse:
    """機体・武器・パイロットステータスから命中率・クリティカル率・ダメージを計算する.

    - `trials` を指定すると、決定論値に加えてモンテカルロ試行の統計値を返す
    - `attacker_weapon_id` が `attacker_spec.weapons` に存在しない場合は 422 を返す
    - `attack_sector` が不正な値の場合は 422 を返す
    """
    try:
        return CombatSimulationService.simulate(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e


# ===========================================================
# NPC(Pilot) データ管理 エンドポイント (Issue #441)
# ===========================================================


def _pilot_to_entry(pilot: Pilot) -> NpcPilotEntry:
    """Pilot モデルを NpcPilotEntry レスポンスに変換する."""
    return NpcPilotEntry(
        id=pilot.id,
        user_id=pilot.user_id,
        name=pilot.name,
        npc_personality=pilot.npc_personality,
        is_ace=PilotService.is_ace_pilot(pilot),
        level=pilot.level,
        exp=pilot.exp,
        credits=pilot.credits,
        skill_points=pilot.skill_points,
        status_points=pilot.status_points,
        sht=pilot.sht,
        mel=pilot.mel,
        intel=pilot.intel,
        ref=pilot.ref,
        tou=pilot.tou,
        luk=pilot.luk,
        awq=pilot.awq,
        mobile_suit_count=0,
        created_at=pilot.created_at,
        updated_at=pilot.updated_at,
    )


@npc_router.get("", response_model=list[NpcPilotEntry])
def list_npcs(
    personality: str | None = None,
    min_level: int | None = None,
    max_level: int | None = None,
    ace_only: bool | None = None,
    session: Session = Depends(get_session),
) -> list[NpcPilotEntry]:
    """NPC(is_npc=True)パイロット一覧を返す.

    - `personality`: 性格タイプで絞り込む (AGGRESSIVE/CAUTIOUS/SNIPER)
    - `min_level` / `max_level`: レベル範囲で絞り込む
    - `ace_only`: True でエース由来のNPCのみ、False で通常NPCのみに絞り込む
    """
    pilots = PilotService.list_npc_pilots(
        session,
        personality=personality,
        min_level=min_level,
        max_level=max_level,
        ace_only=ace_only,
    )
    counts = PilotService.count_owned_mobile_suits_by_user_id(
        session, [pilot.user_id for pilot in pilots]
    )
    entries = []
    for pilot in pilots:
        entry = _pilot_to_entry(pilot)
        entry.mobile_suit_count = counts.get(pilot.user_id, 0)
        entries.append(entry)
    return entries


@npc_router.get("/{pilot_id}", response_model=NpcPilotDetail)
def get_npc(
    pilot_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> NpcPilotDetail:
    """NPCパイロットの詳細（所有機体一覧付き）を返す."""
    pilot = PilotService.get_npc_pilot_by_id(session, pilot_id)
    if pilot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NPC pilot '{pilot_id}' not found.",
        )
    mobile_suits = PilotService.get_npc_owned_mobile_suits(session, pilot.user_id)
    entry = _pilot_to_entry(pilot)
    return NpcPilotDetail(
        **entry.model_dump(exclude={"mobile_suit_count"}),
        mobile_suit_count=len(mobile_suits),
        mobile_suits=[
            NpcMobileSuitEntry(
                id=ms.id,
                name=ms.name,
                max_hp=ms.max_hp,
                current_hp=ms.current_hp,
                armor=ms.armor,
                mobility=ms.mobility,
                personality=ms.personality,
                is_ace=ms.is_ace,
                ace_id=ms.ace_id,
                pilot_name=ms.pilot_name,
                bounty_exp=ms.bounty_exp,
                bounty_credits=ms.bounty_credits,
            )
            for ms in mobile_suits
        ],
    )


@npc_router.put("/{pilot_id}", response_model=NpcPilotDetail)
def update_npc(
    pilot_id: uuid.UUID,
    data: NpcPilotUpdate,
    session: Session = Depends(get_session),
) -> NpcPilotDetail:
    """NPCパイロットのステータス（レベル/exp/credits/各種能力値等）を更新する."""
    updated = PilotService.update_npc_pilot(session, pilot_id, data)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NPC pilot '{pilot_id}' not found.",
        )
    return get_npc(pilot_id, session)


@npc_router.put("/{pilot_id}/mobile-suits/{ms_id}", response_model=NpcMobileSuitEntry)
def update_npc_mobile_suit(
    pilot_id: uuid.UUID,
    ms_id: uuid.UUID,
    data: MobileSuitUpdate,
    session: Session = Depends(get_session),
) -> NpcMobileSuitEntry:
    """NPCパイロットが所有する機体のステータスを更新する.

    - `ms_id` が `pilot_id` の所有機体でない場合は 404 を返す
    """
    pilot = PilotService.get_npc_pilot_by_id(session, pilot_id)
    if pilot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NPC pilot '{pilot_id}' not found.",
        )
    owned_ids = {
        ms.id for ms in PilotService.get_npc_owned_mobile_suits(session, pilot.user_id)
    }
    if ms_id not in owned_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mobile suit '{ms_id}' not owned by NPC pilot '{pilot_id}'.",
        )

    updated = MobileSuitService.update_mobile_suit(session, ms_id, data)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mobile suit '{ms_id}' not found.",
        )
    return NpcMobileSuitEntry(
        id=updated.id,
        name=updated.name,
        max_hp=updated.max_hp,
        current_hp=updated.current_hp,
        armor=updated.armor,
        mobility=updated.mobility,
        personality=updated.personality,
        is_ace=updated.is_ace,
        ace_id=updated.ace_id,
        pilot_name=updated.pilot_name,
        bounty_exp=updated.bounty_exp,
        bounty_credits=updated.bounty_credits,
    )

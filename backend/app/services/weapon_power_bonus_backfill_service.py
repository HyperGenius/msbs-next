"""機体強化（weapon_power）の加算値を、既存の機体の武器から推定して設定する.

加算値は以前は mobile_suits.weapons の power に直接足すだけで、記録が無かった。
そこで各スロットの power と、加算前の power の差から推定する。

- 購入した武器のスロット: base_snapshot + custom_stats の power と比べる
- 初期装備のスロット: 武器マスターの power と比べる

購入した武器のスロットの加算は、バトルエントリー時の resync で消えている場合がある。
そのため差の最大値を加算値とする。武器マスターの power を後から変えた場合は、
初期装備の差がずれる。差がスロット間で揃わない機体は、報告を見て確かめること。
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session, col, select

from app.models.models import MasterWeapon, MobileSuit, PlayerWeapon
from app.services.engineering_service import EngineeringService
from app.services.weapon_service import WeaponService


@dataclass
class WeaponPowerBonusEstimate:
    """1機分の加算値の推定結果."""

    mobile_suit_id: uuid.UUID
    name: str
    user_id: str | None
    bonus: int
    # スロットごとの「power − 加算前の power」。加算前の power が分からないスロットは None。
    slot_diffs: list[int | None]

    @property
    def is_consistent(self) -> bool:
        """正の差がすべてのスロットで同じ値か."""
        return len({d for d in self.slot_diffs if d is not None and d > 0}) <= 1


def _power(weapon: Any) -> int:
    return weapon["power"] if isinstance(weapon, dict) else weapon.power


def _master_weapon_id(weapon: Any) -> str | None:
    if isinstance(weapon, dict):
        return weapon.get("master_weapon_id") or weapon.get("id")
    return getattr(weapon, "master_weapon_id", None) or weapon.id


def _base_power(
    weapon: Any, player_weapon: PlayerWeapon | None, master_powers: dict[str, int]
) -> int | None:
    if player_weapon is not None:
        return WeaponService.apply_effective_spec(
            player_weapon.base_snapshot, player_weapon.custom_stats
        ).power
    return master_powers.get(_master_weapon_id(weapon) or "")


def _slot_diff(weapon: Any, base_power: int | None) -> int | None:
    # 加算前に上限以上だった武器には加算されないため、差から何も分からない。
    if base_power is None or base_power >= EngineeringService.MAX_WEAPON_POWER_CAP:
        return None
    return _power(weapon) - base_power


def _to_bonus(slot_diffs: list[int | None]) -> int:
    largest = max((d for d in slot_diffs if d is not None and d > 0), default=0)
    step = EngineeringService.WEAPON_POWER_INCREASE
    return largest // step * step


def estimate_weapon_power_bonuses(session: Session) -> list[WeaponPowerBonusEstimate]:
    """加算値が未設定のプレイヤー機体について、加算値を推定する.

    推定した加算値が 0 の機体は返さない。
    """
    master_powers = {
        mw.id: mw.weapon["power"] for mw in session.exec(select(MasterWeapon)).all()
    }
    equipped = {
        (pw.equipped_ms_id, pw.equipped_slot): pw
        for pw in session.exec(
            select(PlayerWeapon).where(col(PlayerWeapon.equipped_ms_id).is_not(None))
        ).all()
    }
    suits = session.exec(
        select(MobileSuit)
        .where(col(MobileSuit.user_id).is_not(None))
        .where(MobileSuit.weapon_power_bonus == 0)
    ).all()

    estimates: list[WeaponPowerBonusEstimate] = []
    for ms in suits:
        slot_diffs = [
            _slot_diff(
                weapon,
                _base_power(weapon, equipped.get((ms.id, slot)), master_powers),
            )
            for slot, weapon in enumerate(ms.weapons or [])
        ]
        bonus = _to_bonus(slot_diffs)
        if bonus > 0:
            estimates.append(
                WeaponPowerBonusEstimate(
                    mobile_suit_id=ms.id,
                    name=ms.name,
                    user_id=ms.user_id,
                    bonus=bonus,
                    slot_diffs=slot_diffs,
                )
            )
    return estimates


def apply_weapon_power_bonuses(
    session: Session, estimates: list[WeaponPowerBonusEstimate]
) -> None:
    """推定した加算値を機体に設定し、購入した武器のスロットを作り直す.

    resync で消えていた加算が、購入した武器のスロットに戻る。commit はしない。
    """
    for estimate in estimates:
        ms = session.get(MobileSuit, estimate.mobile_suit_id)
        if ms is None:
            continue
        ms.weapon_power_bonus = estimate.bonus
        WeaponService.resync_mobile_suit_weapons(session, ms)
        session.add(ms)

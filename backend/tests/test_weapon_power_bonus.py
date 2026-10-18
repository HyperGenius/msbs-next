"""機体強化（weapon_power）の加算値が、武器スロットの書き直しで消えないことのテスト."""

import pytest
from sqlmodel import Session

from app.core.gamedata import get_weapon_listing_by_id
from app.models.models import MobileSuit, Pilot, PlayerWeapon
from app.services.engineering_service import EngineeringService
from app.services.weapon_engineering_service import WeaponEngineeringService
from app.services.weapon_power_bonus_backfill_service import (
    apply_weapon_power_bonuses,
    estimate_weapon_power_bonuses,
)
from app.services.weapon_service import WeaponService

USER_ID = "weapon_power_bonus_user"
# シードデータの zaku_mg の power
ZAKU_MG_POWER = 100
INCREASE = EngineeringService.WEAPON_POWER_INCREASE


@pytest.fixture
def pilot(session: Session) -> Pilot:
    """クレジットを十分に持つパイロット."""
    pilot = Pilot(user_id=USER_ID, name="Bonus Pilot", level=1, exp=0, credits=100000)
    session.add(pilot)
    session.commit()
    session.refresh(pilot)
    return pilot


def _zaku_mg_spec() -> dict:
    return get_weapon_listing_by_id("zaku_mg")["weapon"].model_dump()


@pytest.fixture
def mobile_suit(session: Session, pilot: Pilot) -> MobileSuit:
    """スロット0に初期装備、スロット1に購入した武器を持つ機体."""
    ms = MobileSuit(
        user_id=pilot.user_id,
        name="Bonus Zaku",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        weapons=[_zaku_mg_spec(), _zaku_mg_spec()],
        side="PLAYER",
    )
    session.add(ms)
    session.commit()
    session.refresh(ms)
    return ms


@pytest.fixture
def purchased_weapon(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> PlayerWeapon:
    """スロット1に装備した購入済みの武器."""
    pw = PlayerWeapon(
        user_id=pilot.user_id,
        master_weapon_id="zaku_mg",
        base_snapshot=_zaku_mg_spec(),
        custom_stats={},
        equipped_ms_id=mobile_suit.id,
        equipped_slot=1,
    )
    session.add(pw)
    session.commit()
    session.refresh(pw)
    return pw


def _powers(ms: MobileSuit) -> list[int]:
    return [w["power"] if isinstance(w, dict) else w.power for w in ms.weapons]


def _upgrade_weapon_power(
    session: Session, ms: MobileSuit, pilot: Pilot, steps: int
) -> MobileSuit:
    ms, _, _ = EngineeringService(session).upgrade_stat(
        str(ms.id), "weapon_power", pilot, steps=steps
    )
    return ms


def test_upgrade_records_bonus_on_mobile_suit(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """機体強化で weapon_power_bonus が増え、全スロットの威力に足される."""
    ms = _upgrade_weapon_power(session, mobile_suit, pilot, steps=3)

    assert ms.weapon_power_bonus == 3 * INCREASE
    assert _powers(ms) == [ZAKU_MG_POWER + 3 * INCREASE] * 2


def test_resync_keeps_bonus_on_purchased_slot(
    session: Session,
    pilot: Pilot,
    mobile_suit: MobileSuit,
    purchased_weapon: PlayerWeapon,
) -> None:
    """購入した武器のスロットは、resync で作り直しても加算が残る."""
    ms = _upgrade_weapon_power(session, mobile_suit, pilot, steps=2)

    WeaponService.resync_mobile_suit_weapons(session, ms)

    assert _powers(ms) == [ZAKU_MG_POWER + 2 * INCREASE] * 2


def test_weapon_engineering_keeps_bonus(
    session: Session,
    pilot: Pilot,
    mobile_suit: MobileSuit,
    purchased_weapon: PlayerWeapon,
) -> None:
    """武器改造の resync でも、機体強化の加算が残る."""
    _upgrade_weapon_power(session, mobile_suit, pilot, steps=2)

    WeaponEngineeringService(session).upgrade_stat(
        str(purchased_weapon.id), "power_bonus", pilot
    )
    session.refresh(mobile_suit)

    power_bonus = WeaponEngineeringService.POWER_INCREASE
    assert _powers(mobile_suit)[1] == ZAKU_MG_POWER + power_bonus + 2 * INCREASE


def test_equip_applies_bonus_to_new_weapon(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """機体強化のあとに装備した武器にも加算が足される."""
    _upgrade_weapon_power(session, mobile_suit, pilot, steps=2)
    pw = PlayerWeapon(
        user_id=pilot.user_id,
        master_weapon_id="zaku_mg",
        base_snapshot=_zaku_mg_spec(),
        custom_stats={},
    )
    session.add(pw)
    session.commit()
    session.refresh(pw)

    ms = WeaponService.equip_weapon(session, pilot.user_id, pw.id, mobile_suit.id, 1)

    assert _powers(ms)[1] == ZAKU_MG_POWER + 2 * INCREASE


@pytest.mark.parametrize(
    ("power", "bonus", "expected"),
    [
        (100, 10, 110),
        (195, 10, EngineeringService.MAX_WEAPON_POWER_CAP),
        (250, 10, 250),
        (100, 0, 100),
    ],
)
def test_add_weapon_power_bonus_caps(power: int, bonus: int, expected: int) -> None:
    """上限で止める。元の威力が上限以上なら変えない."""
    assert EngineeringService.add_weapon_power_bonus(power, bonus) == expected


def test_backfill_restores_bonus_lost_by_resync(
    session: Session,
    pilot: Pilot,
    mobile_suit: MobileSuit,
    purchased_weapon: PlayerWeapon,
) -> None:
    """初期装備の差から加算値を推定し、購入した武器のスロットに戻す."""
    # 以前の実装の状態: 初期装備にだけ加算が残り、購入した武器は resync で消えている。
    mobile_suit.weapons = [
        {**_zaku_mg_spec(), "power": ZAKU_MG_POWER + 6},
        _zaku_mg_spec(),
    ]
    session.add(mobile_suit)
    session.commit()

    estimates = estimate_weapon_power_bonuses(session)

    assert [(e.mobile_suit_id, e.bonus) for e in estimates] == [(mobile_suit.id, 6)]
    assert estimates[0].slot_diffs == [6, 0]
    assert estimates[0].is_consistent

    apply_weapon_power_bonuses(session, estimates)
    session.commit()
    session.refresh(mobile_suit)

    assert mobile_suit.weapon_power_bonus == 6
    assert _powers(mobile_suit) == [ZAKU_MG_POWER + 6] * 2
    assert estimate_weapon_power_bonuses(session) == []


def test_backfill_flags_inconsistent_diffs(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """スロット間で差が揃わない機体は、最大の差を採り、要確認として返す."""
    mobile_suit.weapons = [
        {**_zaku_mg_spec(), "power": ZAKU_MG_POWER + 4},
        {**_zaku_mg_spec(), "power": ZAKU_MG_POWER + 8},
    ]
    session.add(mobile_suit)
    session.commit()

    (estimate,) = estimate_weapon_power_bonuses(session)

    assert estimate.bonus == 8
    assert not estimate.is_consistent


def test_backfill_skips_suits_without_bonus(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """威力がマスターの値のままの機体は対象にしない."""
    assert estimate_weapon_power_bonuses(session) == []

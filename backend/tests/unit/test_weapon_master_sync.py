"""武器マスターの同期（sync_weapon_master）のテスト."""

import pytest
from sqlalchemy.orm import attributes
from sqlmodel import Session

from app.models.models import (
    AcePilot,
    MasterMobileSuit,
    MasterWeapon,
    MobileSuit,
    Pilot,
    PlayerWeapon,
)
from app.services.weapon_master_sync_service import (
    TARGET_ACE_PILOT,
    TARGET_BASE_SNAPSHOT,
    TARGET_INITIAL_SLOT,
    TARGET_MASTER_MOBILE_SUIT,
    TARGET_PURCHASED_SLOT,
    sync_weapon_master,
)

WEAPON_ID = "giant_bazooka"
# シードデータで Giant Bazooka を初期装備に持つ機体マスター
MASTER_MS_ID = "dom"

OLD_SPEC = {
    "id": WEAPON_ID,
    "name": "Giant Bazooka",
    "power": 180,
    "range": 450,
    "accuracy": 55,
    "type": "PHYSICAL",
    "optimal_range": 350.0,
    "decay_rate": 0.1,
    "is_melee": False,
}


def _update_master(session: Session, **changes: object) -> None:
    master = session.get(MasterWeapon, WEAPON_ID)
    assert master is not None
    master.weapon = {**master.weapon, **changes}
    attributes.flag_modified(master, "weapon")
    session.add(master)
    session.commit()


@pytest.fixture
def setup_data(session: Session) -> tuple[MobileSuit, PlayerWeapon]:
    """初期装備（スロット0）と購入した武器（スロット1）を持つ機体."""
    pilot = Pilot(user_id="sync_test_user", name="Sync Pilot", level=1, exp=0)
    session.add(pilot)
    ms = MobileSuit(
        user_id=pilot.user_id,
        name="Dom",
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.0,
        # 初期装備には機体強化（weapon_power）の加算が乗っている
        weapons=[{**OLD_SPEC, "power": 190}, {**OLD_SPEC, "power": 190}],
    )
    session.add(ms)
    session.commit()
    session.refresh(ms)

    pw = PlayerWeapon(
        user_id=pilot.user_id,
        master_weapon_id=WEAPON_ID,
        base_snapshot=dict(OLD_SPEC),
        custom_stats={"power_bonus": 10},
        equipped_ms_id=ms.id,
        equipped_slot=1,
    )
    session.add(pw)
    session.commit()
    session.refresh(pw)
    return ms, pw


def test_dry_run_reports_changes_without_writing(
    session: Session, setup_data: tuple[MobileSuit, PlayerWeapon]
) -> None:
    """Rollback すれば DB は変わらず、変わる値は報告される."""
    ms, pw = setup_data
    _update_master(session, max_ammo=8)

    report = sync_weapon_master(session, [WEAPON_ID])
    session.rollback()

    assert (
        report.changes[(TARGET_BASE_SNAPSHOT, WEAPON_ID, "max_ammo", "None", "8")] == 1
    )
    assert (
        report.changes[(TARGET_INITIAL_SLOT, WEAPON_ID, "max_ammo", "None", "8")] == 1
    )
    assert report.updated_rows[TARGET_MASTER_MOBILE_SUIT] >= 1

    session.refresh(pw)
    session.refresh(ms)
    assert "max_ammo" not in pw.base_snapshot
    assert all("max_ammo" not in w for w in ms.weapons)


def test_apply_updates_all_copies(
    session: Session, setup_data: tuple[MobileSuit, PlayerWeapon]
) -> None:
    """base_snapshot・両スロット・機体マスターがマスターの値になる."""
    ms, pw = setup_data
    _update_master(session, max_ammo=8)

    sync_weapon_master(session, [WEAPON_ID])
    session.commit()
    session.refresh(pw)
    session.refresh(ms)

    assert pw.base_snapshot["max_ammo"] == 8
    assert pw.custom_stats == {"power_bonus": 10}

    initial, purchased = ms.weapons
    # 初期装備は改造できないものとして、power もマスターの値にする
    assert initial["max_ammo"] == 8
    assert initial["power"] == 180
    # 購入した武器は base_snapshot + custom_stats から作り直す
    assert purchased["max_ammo"] == 8
    assert purchased["power"] == 190

    master_ms = session.get(MasterMobileSuit, MASTER_MS_ID)
    assert master_ms is not None
    bazooka = next(w for w in master_ms.specs["weapons"] if w["id"] == WEAPON_ID)
    assert bazooka["max_ammo"] == 8


def test_second_run_has_no_changes(
    session: Session, setup_data: tuple[MobileSuit, PlayerWeapon]
) -> None:
    """同期後にもう一度流すと、更新する行が無い."""
    _update_master(session, max_ammo=8)
    sync_weapon_master(session, [WEAPON_ID])
    session.commit()

    report = sync_weapon_master(session, [WEAPON_ID])

    assert not report.has_changes


def test_fields_limits_synced_fields(
    session: Session, setup_data: tuple[MobileSuit, PlayerWeapon]
) -> None:
    """指定したフィールドだけを同期する."""
    ms, pw = setup_data
    _update_master(session, max_ammo=8, accuracy=70)

    sync_weapon_master(session, [WEAPON_ID], fields=["max_ammo"])
    session.commit()
    session.refresh(pw)
    session.refresh(ms)

    assert pw.base_snapshot["max_ammo"] == 8
    assert pw.base_snapshot["accuracy"] == 55
    assert ms.weapons[0]["accuracy"] == 55
    assert ms.weapons[0]["power"] == 190


def test_ace_pilot_weapons_are_counted_but_not_updated(session: Session) -> None:
    """エースパイロットの武器は更新せず、差分だけを数える."""
    ace = AcePilot(
        id="ace_sync_test",
        name="テストエース",
        pilot_name="Test Ace",
        personality="AGGRESSIVE",
        mobile_suit={"weapons": [dict(OLD_SPEC)]},
        stats={},
        skills={},
    )
    session.add(ace)
    session.commit()
    _update_master(session, max_ammo=8)

    report = sync_weapon_master(session, [WEAPON_ID])
    session.commit()
    session.refresh(ace)

    assert report.updated_rows[TARGET_ACE_PILOT] == 1
    assert "max_ammo" not in ace.mobile_suit["weapons"][0]


def test_unrelated_weapons_are_untouched(
    session: Session, setup_data: tuple[MobileSuit, PlayerWeapon]
) -> None:
    """対象外の武器IDのコピーは変わらない."""
    ms, _ = setup_data
    _update_master(session, max_ammo=8)

    report = sync_weapon_master(session, ["zaku_mg"])

    assert report.updated_rows[TARGET_INITIAL_SLOT] == 0
    assert report.updated_rows[TARGET_PURCHASED_SLOT] == 0


def test_unknown_weapon_id_raises(session: Session) -> None:
    """武器マスターに無いIDはエラーにする."""
    with pytest.raises(ValueError, match="no_such_weapon"):
        sync_weapon_master(session, ["no_such_weapon"])


def test_unknown_field_raises(session: Session) -> None:
    """同期できないフィールドはエラーにする."""
    with pytest.raises(ValueError, match="master_weapon_id"):
        sync_weapon_master(session, [WEAPON_ID], fields=["master_weapon_id"])

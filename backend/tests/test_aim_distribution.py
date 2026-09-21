"""WeaponService.update_aim_distribution（狙う部位配分設定）のテスト (Issue #505)."""

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.models.models import MobileSuit, Pilot, PlayerWeapon, Vector3
from app.services.weapon_service import WeaponService

VALID_DISTRIBUTION = {
    "HEAD": 0.2,
    "TORSO": 0.4,
    "RIGHT_ARM": 0.1,
    "LEFT_ARM": 0.1,
    "RIGHT_LEG": 0.1,
    "LEFT_LEG": 0.1,
}


@pytest.fixture
def pilot(session: Session) -> Pilot:
    """テスト用パイロット."""
    pilot = Pilot(
        user_id="aim_dist_test_user",
        name="Test Pilot",
        level=1,
        exp=0,
        credits=100000,
    )
    session.add(pilot)
    session.commit()
    session.refresh(pilot)
    return pilot


@pytest.fixture
def player_weapon(session: Session, pilot: Pilot) -> PlayerWeapon:
    """未装備のテスト用武器インスタンス."""
    pw = PlayerWeapon(
        user_id=pilot.user_id,
        master_weapon_id="zaku_mg",
        base_snapshot={
            "id": "zaku_mg",
            "name": "ザク・マシンガン",
            "power": 100,
            "range": 400,
            "accuracy": 60,
            "type": "PHYSICAL",
        },
        custom_stats={},
    )
    session.add(pw)
    session.commit()
    session.refresh(pw)
    return pw


def test_update_aim_distribution_persists_into_custom_stats(
    session: Session, pilot: Pilot, player_weapon: PlayerWeapon
) -> None:
    """有効な配分はcustom_stats.aim_distributionに保存される."""
    updated = WeaponService.update_aim_distribution(
        session, pilot.user_id, player_weapon.id, VALID_DISTRIBUTION
    )
    assert updated.custom_stats["aim_distribution"] == VALID_DISTRIBUTION


def test_update_aim_distribution_rejects_invalid_part_name(
    session: Session, pilot: Pilot, player_weapon: PlayerWeapon
) -> None:
    """未知の部位名はHTTPException(400)."""
    with pytest.raises(HTTPException) as exc_info:
        WeaponService.update_aim_distribution(
            session, pilot.user_id, player_weapon.id, {"UNKNOWN_PART": 1.0}
        )
    assert exc_info.value.status_code == 400


def test_update_aim_distribution_rejects_negative_value(
    session: Session, pilot: Pilot, player_weapon: PlayerWeapon
) -> None:
    """負の配分値はHTTPException(400)."""
    invalid = {**VALID_DISTRIBUTION, "HEAD": -0.1, "TORSO": 0.5}
    with pytest.raises(HTTPException) as exc_info:
        WeaponService.update_aim_distribution(
            session, pilot.user_id, player_weapon.id, invalid
        )
    assert exc_info.value.status_code == 400


def test_update_aim_distribution_rejects_sum_not_100_percent(
    session: Session, pilot: Pilot, player_weapon: PlayerWeapon
) -> None:
    """合計が100%から乖離している場合はHTTPException(400)."""
    invalid = {**VALID_DISTRIBUTION, "HEAD": 0.9}
    with pytest.raises(HTTPException) as exc_info:
        WeaponService.update_aim_distribution(
            session, pilot.user_id, player_weapon.id, invalid
        )
    assert exc_info.value.status_code == 400


def test_update_aim_distribution_rejects_wrong_owner(
    session: Session, pilot: Pilot, player_weapon: PlayerWeapon
) -> None:
    """他人の武器インスタンスは403."""
    with pytest.raises(HTTPException) as exc_info:
        WeaponService.update_aim_distribution(
            session, "someone_else", player_weapon.id, VALID_DISTRIBUTION
        )
    assert exc_info.value.status_code == 403


def test_update_aim_distribution_resyncs_equipped_mobile_suit(
    session: Session, pilot: Pilot, player_weapon: PlayerWeapon
) -> None:
    """装備中の武器を更新すると、MobileSuit.weaponsの実効スペックも再同期される."""
    mobile_suit = MobileSuit(
        user_id=pilot.user_id,
        name="Test MS",
        max_hp=200,
        current_hp=200,
        armor=20,
        mobility=1.0,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            WeaponService.apply_effective_spec(
                player_weapon.base_snapshot, player_weapon.custom_stats
            )
        ],
    )
    session.add(mobile_suit)
    session.commit()
    session.refresh(mobile_suit)

    player_weapon.equipped_ms_id = mobile_suit.id
    player_weapon.equipped_slot = 0
    session.add(player_weapon)
    session.commit()

    WeaponService.update_aim_distribution(
        session, pilot.user_id, player_weapon.id, VALID_DISTRIBUTION
    )

    session.refresh(mobile_suit)
    assert mobile_suit.weapons[0]["aim_distribution"] == VALID_DISTRIBUTION

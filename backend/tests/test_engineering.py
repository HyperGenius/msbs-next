"""Tests for engineering service."""

import uuid

import pytest
from sqlmodel import Session

from app.models.models import MobileSuit, Pilot, Weapon
from app.services.engineering_service import EngineeringService


@pytest.fixture
def pilot(session: Session) -> Pilot:
    """Create a test pilot."""
    pilot = Pilot(
        user_id="test_user_123",
        name="Test Pilot",
        level=1,
        exp=0,
        credits=10000,
    )
    session.add(pilot)
    session.commit()
    session.refresh(pilot)
    return pilot


@pytest.fixture
def mobile_suit(session: Session, pilot: Pilot) -> MobileSuit:
    """Create a test mobile suit."""
    ms = MobileSuit(
        user_id=pilot.user_id,
        name="Test Gundam",
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=1.0,
        weapons=[
            Weapon(
                id="test_beam_rifle",
                name="Test Beam Rifle",
                power=50,
                range=400,
                accuracy=80,
            )
        ],
    )
    session.add(ms)
    session.commit()
    session.refresh(ms)
    return ms


def test_calculate_upgrade_cost_hp(session: Session) -> None:
    """Test HP upgrade cost calculation."""
    cost = EngineeringService.calculate_upgrade_cost("hp", 100)
    assert cost == int(50 * (1 + 100 / 200))  # 75


def test_calculate_upgrade_cost_armor(session: Session) -> None:
    """Test armor upgrade cost calculation."""
    cost = EngineeringService.calculate_upgrade_cost("armor", 10)
    assert cost == int(100 * (1 + 10 / 10))  # 200


def test_upgrade_hp(session: Session, pilot: Pilot, mobile_suit: MobileSuit) -> None:
    """Test upgrading HP."""
    service = EngineeringService(session)
    initial_credits = pilot.credits
    initial_hp = mobile_suit.max_hp

    updated_ms, updated_pilot, cost = service.upgrade_stat(
        str(mobile_suit.id), "hp", pilot
    )

    assert updated_ms.max_hp == initial_hp + EngineeringService.HP_INCREASE
    assert updated_pilot.credits == initial_credits - cost
    assert cost > 0


def test_upgrade_armor(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrading armor."""
    service = EngineeringService(session)
    initial_credits = pilot.credits
    initial_armor = mobile_suit.armor

    updated_ms, updated_pilot, cost = service.upgrade_stat(
        str(mobile_suit.id), "armor", pilot
    )

    assert updated_ms.armor == initial_armor + EngineeringService.ARMOR_INCREASE
    assert updated_pilot.credits == initial_credits - cost
    assert cost > 0


def test_upgrade_mobility(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrading mobility."""
    service = EngineeringService(session)
    initial_credits = pilot.credits
    initial_mobility = mobile_suit.mobility

    updated_ms, updated_pilot, cost = service.upgrade_stat(
        str(mobile_suit.id), "mobility", pilot
    )

    assert updated_ms.mobility == pytest.approx(
        initial_mobility + EngineeringService.MOBILITY_INCREASE
    )
    assert updated_pilot.credits == initial_credits - cost
    assert cost > 0


def test_upgrade_weapon_power(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrading weapon power."""
    service = EngineeringService(session)
    initial_credits = pilot.credits
    # Handle both dict and Weapon object
    first_weapon = mobile_suit.weapons[0]
    initial_power = first_weapon["power"] if isinstance(first_weapon, dict) else first_weapon.power

    updated_ms, updated_pilot, cost = service.upgrade_stat(
        str(mobile_suit.id), "weapon_power", pilot
    )

    # Handle both dict and Weapon object for updated
    updated_weapon = updated_ms.weapons[0]
    updated_power = updated_weapon["power"] if isinstance(updated_weapon, dict) else updated_weapon.power
    
    assert (
        updated_power
        == initial_power + EngineeringService.WEAPON_POWER_INCREASE
    )
    assert updated_pilot.credits == initial_credits - cost
    assert cost > 0


def test_upgrade_insufficient_credits(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrade fails with insufficient credits."""
    pilot.credits = 10  # Very low credits
    session.add(pilot)
    session.commit()

    service = EngineeringService(session)

    with pytest.raises(RuntimeError, match="Insufficient credits"):
        service.upgrade_stat(str(mobile_suit.id), "hp", pilot)


def test_upgrade_at_max_cap(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrade fails when stat is at max cap."""
    mobile_suit.max_hp = EngineeringService.MAX_HP_CAP
    session.add(mobile_suit)
    session.commit()

    service = EngineeringService(session)

    with pytest.raises(ValueError, match="already at maximum"):
        service.upgrade_stat(str(mobile_suit.id), "hp", pilot)


def test_upgrade_invalid_stat_type(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrade fails with invalid stat type."""
    service = EngineeringService(session)

    with pytest.raises(ValueError, match="Invalid stat type"):
        service.upgrade_stat(str(mobile_suit.id), "invalid_stat", pilot)


def test_upgrade_not_owned_mobile_suit(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrade fails when mobile suit is not owned."""
    mobile_suit.user_id = "different_user"
    session.add(mobile_suit)
    session.commit()

    service = EngineeringService(session)

    with pytest.raises(ValueError, match="don't own"):
        service.upgrade_stat(str(mobile_suit.id), "hp", pilot)


def test_upgrade_nonexistent_mobile_suit(session: Session, pilot: Pilot) -> None:
    """Test upgrade fails with nonexistent mobile suit."""
    service = EngineeringService(session)

    with pytest.raises(ValueError, match="not found"):
        service.upgrade_stat(str(uuid.uuid4()), "hp", pilot)


def test_get_upgrade_preview(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test getting upgrade preview."""
    service = EngineeringService(session)

    preview = service.get_upgrade_preview(str(mobile_suit.id), "hp")

    assert preview["current_value"] == mobile_suit.max_hp
    assert (
        preview["new_value"]
        == mobile_suit.max_hp + EngineeringService.HP_INCREASE
    )
    assert preview["cost"] > 0
    assert preview["at_max_cap"] is False


def test_get_upgrade_preview_at_cap(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrade preview when at max cap."""
    mobile_suit.max_hp = EngineeringService.MAX_HP_CAP
    session.add(mobile_suit)
    session.commit()

    service = EngineeringService(session)

    preview = service.get_upgrade_preview(str(mobile_suit.id), "hp")

    assert preview["at_max_cap"] is True
    assert preview["current_value"] == EngineeringService.MAX_HP_CAP
    assert preview["new_value"] == EngineeringService.MAX_HP_CAP

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


def test_upgrade_armor(session: Session, pilot: Pilot, mobile_suit: MobileSuit) -> None:
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
    initial_power = (
        first_weapon["power"] if isinstance(first_weapon, dict) else first_weapon.power
    )

    updated_ms, updated_pilot, cost = service.upgrade_stat(
        str(mobile_suit.id), "weapon_power", pilot
    )

    # Handle both dict and Weapon object for updated
    updated_weapon = updated_ms.weapons[0]
    updated_power = (
        updated_weapon["power"]
        if isinstance(updated_weapon, dict)
        else updated_weapon.power
    )

    assert updated_power == initial_power + EngineeringService.WEAPON_POWER_INCREASE
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
    assert preview["new_value"] == mobile_suit.max_hp + EngineeringService.HP_INCREASE
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


def test_upgrade_melee_aptitude(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrading melee aptitude."""
    service = EngineeringService(session)
    initial_credits = pilot.credits
    initial_value = mobile_suit.melee_aptitude

    updated_ms, updated_pilot, cost = service.upgrade_stat(
        str(mobile_suit.id), "melee_aptitude", pilot
    )

    assert updated_ms.melee_aptitude == pytest.approx(
        initial_value + EngineeringService.MELEE_APTITUDE_INCREASE
    )
    assert updated_pilot.credits == initial_credits - cost
    assert cost > 0


def test_upgrade_shooting_aptitude(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrading shooting aptitude."""
    service = EngineeringService(session)
    initial_credits = pilot.credits
    initial_value = mobile_suit.shooting_aptitude

    updated_ms, updated_pilot, cost = service.upgrade_stat(
        str(mobile_suit.id), "shooting_aptitude", pilot
    )

    assert updated_ms.shooting_aptitude == pytest.approx(
        initial_value + EngineeringService.SHOOTING_APTITUDE_INCREASE
    )
    assert updated_pilot.credits == initial_credits - cost
    assert cost > 0


def test_upgrade_accuracy_bonus(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrading accuracy bonus."""
    service = EngineeringService(session)
    initial_credits = pilot.credits
    initial_value = mobile_suit.accuracy_bonus

    updated_ms, updated_pilot, cost = service.upgrade_stat(
        str(mobile_suit.id), "accuracy_bonus", pilot
    )

    assert updated_ms.accuracy_bonus == pytest.approx(
        initial_value + EngineeringService.ACCURACY_BONUS_INCREASE
    )
    assert updated_pilot.credits == initial_credits - cost
    assert cost > 0


def test_upgrade_evasion_bonus(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrading evasion bonus."""
    service = EngineeringService(session)
    initial_credits = pilot.credits
    initial_value = mobile_suit.evasion_bonus

    updated_ms, updated_pilot, cost = service.upgrade_stat(
        str(mobile_suit.id), "evasion_bonus", pilot
    )

    assert updated_ms.evasion_bonus == pytest.approx(
        initial_value + EngineeringService.EVASION_BONUS_INCREASE
    )
    assert updated_pilot.credits == initial_credits - cost
    assert cost > 0


def test_upgrade_acceleration_bonus(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrading acceleration bonus."""
    service = EngineeringService(session)
    initial_credits = pilot.credits
    initial_value = mobile_suit.acceleration_bonus

    updated_ms, updated_pilot, cost = service.upgrade_stat(
        str(mobile_suit.id), "acceleration_bonus", pilot
    )

    assert updated_ms.acceleration_bonus == pytest.approx(
        initial_value + EngineeringService.ACCELERATION_BONUS_INCREASE
    )
    assert updated_pilot.credits == initial_credits - cost
    assert cost > 0


def test_upgrade_turning_bonus(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrading turning bonus."""
    service = EngineeringService(session)
    initial_credits = pilot.credits
    initial_value = mobile_suit.turning_bonus

    updated_ms, updated_pilot, cost = service.upgrade_stat(
        str(mobile_suit.id), "turning_bonus", pilot
    )

    assert updated_ms.turning_bonus == pytest.approx(
        initial_value + EngineeringService.TURNING_BONUS_INCREASE
    )
    assert updated_pilot.credits == initial_credits - cost
    assert cost > 0


def test_upgrade_melee_aptitude_at_max_cap(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrade fails when melee aptitude is at max cap."""
    mobile_suit.melee_aptitude = EngineeringService.MAX_MELEE_APTITUDE_CAP
    session.add(mobile_suit)
    session.commit()

    service = EngineeringService(session)

    with pytest.raises(ValueError, match="already at maximum"):
        service.upgrade_stat(str(mobile_suit.id), "melee_aptitude", pilot)


def test_upgrade_shooting_aptitude_at_max_cap(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrade fails when shooting aptitude is at max cap."""
    mobile_suit.shooting_aptitude = EngineeringService.MAX_SHOOTING_APTITUDE_CAP
    session.add(mobile_suit)
    session.commit()

    service = EngineeringService(session)

    with pytest.raises(ValueError, match="already at maximum"):
        service.upgrade_stat(str(mobile_suit.id), "shooting_aptitude", pilot)


def test_upgrade_accuracy_bonus_at_max_cap(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrade fails when accuracy bonus is at max cap."""
    mobile_suit.accuracy_bonus = EngineeringService.MAX_ACCURACY_BONUS_CAP
    session.add(mobile_suit)
    session.commit()

    service = EngineeringService(session)

    with pytest.raises(ValueError, match="already at maximum"):
        service.upgrade_stat(str(mobile_suit.id), "accuracy_bonus", pilot)


def test_upgrade_preview_melee_aptitude(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test getting upgrade preview for melee aptitude."""
    service = EngineeringService(session)

    preview = service.get_upgrade_preview(str(mobile_suit.id), "melee_aptitude")

    assert preview["current_value"] == pytest.approx(mobile_suit.melee_aptitude)
    assert preview["new_value"] == pytest.approx(
        mobile_suit.melee_aptitude + EngineeringService.MELEE_APTITUDE_INCREASE
    )
    assert preview["cost"] > 0
    assert preview["at_max_cap"] is False


def test_upgrade_preview_evasion_bonus_at_cap(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrade preview when evasion bonus is at max cap."""
    mobile_suit.evasion_bonus = EngineeringService.MAX_EVASION_BONUS_CAP
    session.add(mobile_suit)
    session.commit()

    service = EngineeringService(session)

    preview = service.get_upgrade_preview(str(mobile_suit.id), "evasion_bonus")

    assert preview["at_max_cap"] is True
    assert preview["current_value"] == pytest.approx(
        EngineeringService.MAX_EVASION_BONUS_CAP
    )
    assert preview["new_value"] == pytest.approx(
        EngineeringService.MAX_EVASION_BONUS_CAP
    )


def test_upgrade_multiple_steps(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test upgrading HP with multiple steps at once."""
    service = EngineeringService(session)
    initial_credits = pilot.credits
    initial_hp = mobile_suit.max_hp
    steps = 3

    updated_ms, updated_pilot, total_cost = service.upgrade_stat(
        str(mobile_suit.id), "hp", pilot, steps=steps
    )

    assert updated_ms.max_hp == initial_hp + EngineeringService.HP_INCREASE * steps
    assert updated_pilot.credits == initial_credits - total_cost
    assert total_cost > 0


def test_upgrade_multiple_steps_cumulative_cost(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test that multi-step cost equals sum of individual step costs."""
    service = EngineeringService(session)
    initial_hp = mobile_suit.max_hp

    # Calculate expected cost for each step
    expected_total = sum(
        EngineeringService.calculate_upgrade_cost(
            "hp", initial_hp + i * EngineeringService.HP_INCREASE
        )
        for i in range(3)
    )

    _, _, total_cost = service.upgrade_stat(str(mobile_suit.id), "hp", pilot, steps=3)

    assert total_cost == expected_total


def test_upgrade_steps_invalid_zero(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test that steps=0 raises ValueError."""
    service = EngineeringService(session)

    with pytest.raises(ValueError, match="steps must be at least 1"):
        service.upgrade_stat(str(mobile_suit.id), "hp", pilot, steps=0)


def test_upgrade_steps_insufficient_credits_midway(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test that insufficient credits mid-loop raises RuntimeError."""
    # Give pilot only enough credits for 1 upgrade but request 2
    cost_step1 = EngineeringService.calculate_upgrade_cost("hp", mobile_suit.max_hp)
    pilot.credits = cost_step1  # Exactly enough for first step only
    session.add(pilot)
    session.commit()

    service = EngineeringService(session)

    with pytest.raises(RuntimeError, match="Insufficient credits"):
        service.upgrade_stat(str(mobile_suit.id), "hp", pilot, steps=2)


def test_upgrade_steps_hits_cap(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test that steps hitting the cap raises ValueError."""
    # Set HP one step below cap
    mobile_suit.max_hp = EngineeringService.MAX_HP_CAP - EngineeringService.HP_INCREASE
    session.add(mobile_suit)
    session.commit()

    service = EngineeringService(session)

    # Requesting 2 steps when only 1 is possible should raise on the 2nd step
    with pytest.raises(ValueError, match="already at maximum"):
        service.upgrade_stat(str(mobile_suit.id), "hp", pilot, steps=2)


def test_bulk_upgrade_stats(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test bulk upgrading multiple stats at once."""
    service = EngineeringService(session)
    initial_credits = pilot.credits
    initial_hp = mobile_suit.max_hp
    initial_armor = mobile_suit.armor

    updated_ms, updated_pilot, total_cost = service.bulk_upgrade_stats(
        str(mobile_suit.id), pilot, {"hp": 2, "armor": 1}
    )

    assert updated_ms.max_hp == initial_hp + EngineeringService.HP_INCREASE * 2
    assert updated_ms.armor == initial_armor + EngineeringService.ARMOR_INCREASE
    assert updated_pilot.credits == initial_credits - total_cost
    assert total_cost > 0


def test_bulk_upgrade_stats_skip_zero_steps(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test that steps=0 entries are silently skipped."""
    service = EngineeringService(session)
    initial_hp = mobile_suit.max_hp

    updated_ms, _, total_cost = service.bulk_upgrade_stats(
        str(mobile_suit.id), pilot, {"hp": 1, "armor": 0}
    )

    assert updated_ms.max_hp == initial_hp + EngineeringService.HP_INCREASE
    assert total_cost > 0


def test_bulk_upgrade_stats_insufficient_credits(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test bulk upgrade fails with insufficient credits."""
    pilot.credits = 10
    session.add(pilot)
    session.commit()

    service = EngineeringService(session)

    with pytest.raises(RuntimeError, match="Insufficient credits"):
        service.bulk_upgrade_stats(str(mobile_suit.id), pilot, {"hp": 1})


def test_bulk_upgrade_stats_not_owned(
    session: Session, pilot: Pilot, mobile_suit: MobileSuit
) -> None:
    """Test bulk upgrade fails when mobile suit is not owned by pilot."""
    mobile_suit.user_id = "other_user"
    session.add(mobile_suit)
    session.commit()

    service = EngineeringService(session)

    with pytest.raises(ValueError, match="don't own"):
        service.bulk_upgrade_stats(str(mobile_suit.id), pilot, {"hp": 1})


def test_bulk_upgrade_stats_not_found(session: Session, pilot: Pilot) -> None:
    """Test bulk upgrade fails when mobile suit does not exist."""
    service = EngineeringService(session)

    with pytest.raises(ValueError, match="not found"):
        service.bulk_upgrade_stats(str(uuid.uuid4()), pilot, {"hp": 1})

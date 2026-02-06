"""Engineering service for mobile suit upgrades."""

import uuid

from sqlalchemy.orm import attributes
from sqlmodel import Session

from app.models.models import MobileSuit, Pilot


class EngineeringService:
    """Service for upgrading mobile suit stats using Credits."""

    # Upgrade cost multipliers
    BASE_HP_COST = 50
    BASE_ARMOR_COST = 100
    BASE_MOBILITY_COST = 150
    BASE_WEAPON_POWER_COST = 80

    # Stat increase per upgrade
    HP_INCREASE = 10
    ARMOR_INCREASE = 1
    MOBILITY_INCREASE = 0.05
    WEAPON_POWER_INCREASE = 2

    # Maximum caps to prevent game balance issues
    MAX_HP_CAP = 500
    MAX_ARMOR_CAP = 50
    MAX_MOBILITY_CAP = 3.0
    MAX_WEAPON_POWER_CAP = 200

    def __init__(self, session: Session):
        """Initialize the engineering service.

        Args:
            session: Database session
        """
        self.session = session

    @staticmethod
    def calculate_upgrade_cost(stat_type: str, current_value: int | float) -> int:
        """Calculate upgrade cost based on current stat value.

        Higher stat values cost more to upgrade.

        Args:
            stat_type: Type of stat ("hp", "armor", "mobility", "weapon_power")
            current_value: Current value of the stat

        Returns:
            Cost in Credits for the upgrade
        """
        base_costs = {
            "hp": EngineeringService.BASE_HP_COST,
            "armor": EngineeringService.BASE_ARMOR_COST,
            "mobility": EngineeringService.BASE_MOBILITY_COST,
            "weapon_power": EngineeringService.BASE_WEAPON_POWER_COST,
        }

        base_cost = base_costs.get(stat_type, 100)

        # Cost increases with current value
        # Formula: base_cost * (1 + current_value / 100)
        if stat_type == "hp":
            multiplier = 1 + (current_value / 200)
        elif stat_type == "armor":
            multiplier = 1 + (current_value / 10)
        elif stat_type == "mobility":
            multiplier = 1 + (current_value / 2)
        elif stat_type == "weapon_power":
            multiplier = 1 + (current_value / 50)
        else:
            multiplier = 1

        return int(base_cost * multiplier)

    def _validate_and_get_cost(
        self, ms: MobileSuit, stat_type: str
    ) -> tuple[int | float, int]:
        """Validate stat and get upgrade cost.

        Args:
            ms: Mobile suit to validate
            stat_type: Type of stat to upgrade

        Returns:
            tuple[int | float, int]: Current value and cost

        Raises:
            ValueError: If stat is at max cap or invalid
        """
        current_value: int | float
        if stat_type == "hp":
            current_value = ms.max_hp
            if current_value >= self.MAX_HP_CAP:
                raise ValueError(f"HP is already at maximum ({self.MAX_HP_CAP})")
        elif stat_type == "armor":
            current_value = ms.armor
            if current_value >= self.MAX_ARMOR_CAP:
                raise ValueError(f"Armor is already at maximum ({self.MAX_ARMOR_CAP})")
        elif stat_type == "mobility":
            current_value = ms.mobility
            if current_value >= self.MAX_MOBILITY_CAP:
                raise ValueError(
                    f"Mobility is already at maximum ({self.MAX_MOBILITY_CAP})"
                )
        elif stat_type == "weapon_power":
            if not ms.weapons or len(ms.weapons) == 0:
                raise ValueError("No weapons to upgrade")
            # Handle if weapons are returned as dicts
            first_weapon = ms.weapons[0]
            current_value = (
                first_weapon["power"]
                if isinstance(first_weapon, dict)
                else first_weapon.power
            )
            if current_value >= self.MAX_WEAPON_POWER_CAP:
                raise ValueError(
                    f"Weapon power is already at maximum ({self.MAX_WEAPON_POWER_CAP})"
                )
        else:
            raise ValueError(
                f"Invalid stat type: {stat_type}. "
                "Must be one of: hp, armor, mobility, weapon_power"
            )

        cost = self.calculate_upgrade_cost(stat_type, current_value)
        return current_value, cost

    def _apply_upgrade(self, ms: MobileSuit, stat_type: str) -> None:
        """Apply the stat upgrade to the mobile suit.

        Args:
            ms: Mobile suit to upgrade
            stat_type: Type of stat to upgrade
        """
        # Declare variable with union type for different stat types
        new_value: int | float

        if stat_type == "hp":
            old_max_hp = ms.max_hp
            new_value = ms.max_hp + self.HP_INCREASE
            ms.max_hp = int(min(new_value, self.MAX_HP_CAP))
            # Also increase current HP proportionally
            if old_max_hp > 0:
                hp_ratio = ms.current_hp / old_max_hp
                ms.current_hp = int(ms.max_hp * hp_ratio)
            else:
                ms.current_hp = ms.max_hp
        elif stat_type == "armor":
            new_value = ms.armor + self.ARMOR_INCREASE
            ms.armor = int(min(new_value, self.MAX_ARMOR_CAP))
        elif stat_type == "mobility":
            new_value = ms.mobility + self.MOBILITY_INCREASE
            ms.mobility = min(new_value, self.MAX_MOBILITY_CAP)
        elif stat_type == "weapon_power":
            # Upgrade all weapons - handle both dict and Weapon objects
            weapons = list(ms.weapons)
            updated_weapons = []
            for weapon in weapons:
                if isinstance(weapon, dict):
                    new_power = weapon["power"] + self.WEAPON_POWER_INCREASE
                    weapon["power"] = int(min(new_power, self.MAX_WEAPON_POWER_CAP))
                    updated_weapons.append(weapon)
                else:
                    new_power = weapon.power + self.WEAPON_POWER_INCREASE
                    weapon.power = int(min(new_power, self.MAX_WEAPON_POWER_CAP))
                    updated_weapons.append(weapon)
            ms.weapons = (
                updated_weapons  # Reassign to trigger SQLAlchemy change detection
            )
            # Mark the column as modified to ensure persistence
            attributes.flag_modified(ms, "weapons")

    def upgrade_stat(
        self, mobile_suit_id: str, stat_type: str, pilot: Pilot
    ) -> tuple[MobileSuit, Pilot, int]:
        """Upgrade a specific stat of a mobile suit.

        Args:
            mobile_suit_id: ID of the mobile suit to upgrade
            stat_type: Type of stat to upgrade
            pilot: Pilot who owns the mobile suit

        Returns:
            tuple[MobileSuit, Pilot, int]: Updated mobile suit, pilot, and upgrade cost

        Raises:
            ValueError: If stat is at max cap or invalid parameters
            RuntimeError: If insufficient credits
        """
        # Convert string ID to UUID if necessary
        ms_id = (
            uuid.UUID(mobile_suit_id)
            if isinstance(mobile_suit_id, str)
            else mobile_suit_id
        )

        # Get mobile suit
        ms = self.session.get(MobileSuit, ms_id)
        if not ms:
            raise ValueError("Mobile suit not found")

        # Verify ownership
        if ms.user_id != pilot.user_id:
            raise ValueError("You don't own this mobile suit")

        # Validate and get cost
        _, cost = self._validate_and_get_cost(ms, stat_type)

        # Check if pilot has enough credits
        if pilot.credits < cost:
            raise RuntimeError(
                f"Insufficient credits. Required: {cost}, Available: {pilot.credits}"
            )

        # Deduct credits
        pilot.credits -= cost

        # Apply upgrade
        self._apply_upgrade(ms, stat_type)

        # Save changes
        self.session.add(ms)
        self.session.add(pilot)
        self.session.commit()
        self.session.refresh(ms)
        self.session.refresh(pilot)

        return ms, pilot, cost

    def get_upgrade_preview(self, mobile_suit_id: str, stat_type: str) -> dict:
        """Get preview of what an upgrade would do.

        Args:
            mobile_suit_id: ID of the mobile suit
            stat_type: Type of stat to preview

        Returns:
            dict with current_value, new_value, cost, and at_max_cap
        """
        # Convert string ID to UUID if necessary
        ms_id = (
            uuid.UUID(mobile_suit_id)
            if isinstance(mobile_suit_id, str)
            else mobile_suit_id
        )

        ms = self.session.get(MobileSuit, ms_id)
        if not ms:
            raise ValueError("Mobile suit not found")

        # Declare variables with union types for different stat types
        current: int | float
        new_value: int | float
        cost: int
        at_max: bool

        if stat_type == "hp":
            current = ms.max_hp
            new_value = min(current + self.HP_INCREASE, self.MAX_HP_CAP)
            cost = self.calculate_upgrade_cost(stat_type, current)
            at_max = current >= self.MAX_HP_CAP
        elif stat_type == "armor":
            current = ms.armor
            new_value = min(current + self.ARMOR_INCREASE, self.MAX_ARMOR_CAP)
            cost = self.calculate_upgrade_cost(stat_type, current)
            at_max = current >= self.MAX_ARMOR_CAP
        elif stat_type == "mobility":
            current = ms.mobility
            new_value = min(current + self.MOBILITY_INCREASE, self.MAX_MOBILITY_CAP)
            cost = self.calculate_upgrade_cost(stat_type, current)
            at_max = current >= self.MAX_MOBILITY_CAP
        elif stat_type == "weapon_power":
            if not ms.weapons or len(ms.weapons) == 0:
                raise ValueError("No weapons to upgrade")
            # Handle both dict and Weapon object
            first_weapon = ms.weapons[0]
            current = (
                first_weapon["power"]
                if isinstance(first_weapon, dict)
                else first_weapon.power
            )
            new_value = min(
                current + self.WEAPON_POWER_INCREASE, self.MAX_WEAPON_POWER_CAP
            )
            cost = self.calculate_upgrade_cost(stat_type, current)
            at_max = current >= self.MAX_WEAPON_POWER_CAP
        else:
            raise ValueError(f"Invalid stat type: {stat_type}")

        return {
            "current_value": current,
            "new_value": new_value,
            "cost": cost,
            "at_max_cap": at_max,
        }

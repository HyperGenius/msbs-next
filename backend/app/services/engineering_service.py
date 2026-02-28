"""Engineering service for mobile suit upgrades."""

import uuid
from typing import NamedTuple

from sqlalchemy.orm import attributes
from sqlmodel import Session

from app.models.models import MobileSuit, Pilot


class _FloatStatConfig(NamedTuple):
    """Configuration for a float-based stat upgrade."""

    attr: str
    increment: float
    cap: float
    label: str


class EngineeringService:
    """Service for upgrading mobile suit stats using Credits."""

    # Upgrade cost multipliers
    BASE_HP_COST = 50
    BASE_ARMOR_COST = 100
    BASE_MOBILITY_COST = 150
    BASE_WEAPON_POWER_COST = 80
    BASE_MELEE_APTITUDE_COST = 200
    BASE_SHOOTING_APTITUDE_COST = 200
    BASE_ACCURACY_BONUS_COST = 120
    BASE_EVASION_BONUS_COST = 120
    BASE_ACCELERATION_BONUS_COST = 130
    BASE_TURNING_BONUS_COST = 130

    # Stat increase per upgrade
    HP_INCREASE = 10
    ARMOR_INCREASE = 1
    MOBILITY_INCREASE = 0.05
    WEAPON_POWER_INCREASE = 2
    MELEE_APTITUDE_INCREASE = 0.05
    SHOOTING_APTITUDE_INCREASE = 0.05
    ACCURACY_BONUS_INCREASE = 0.5
    EVASION_BONUS_INCREASE = 0.5
    ACCELERATION_BONUS_INCREASE = 0.05
    TURNING_BONUS_INCREASE = 0.05

    # Maximum caps to prevent game balance issues
    MAX_HP_CAP = 500
    MAX_ARMOR_CAP = 50
    MAX_MOBILITY_CAP = 3.0
    MAX_WEAPON_POWER_CAP = 200
    MAX_MELEE_APTITUDE_CAP = 2.0
    MAX_SHOOTING_APTITUDE_CAP = 2.0
    MAX_ACCURACY_BONUS_CAP = 10.0
    MAX_EVASION_BONUS_CAP = 10.0
    MAX_ACCELERATION_BONUS_CAP = 2.0
    MAX_TURNING_BONUS_CAP = 2.0

    # Base costs per stat type (populated as class attribute for static access)
    _BASE_COSTS: dict[str, int] = {
        "hp": 50,
        "armor": 100,
        "mobility": 150,
        "weapon_power": 80,
        "melee_aptitude": 200,
        "shooting_aptitude": 200,
        "accuracy_bonus": 120,
        "evasion_bonus": 120,
        "acceleration_bonus": 130,
        "turning_bonus": 130,
    }

    # Cost divisors: cost multiplier = 1 + current_value / divisor
    _COST_DIVISORS: dict[str, float] = {
        "hp": 200.0,
        "armor": 10.0,
        "mobility": 2.0,
        "weapon_power": 50.0,
        "melee_aptitude": 2.0,
        "shooting_aptitude": 2.0,
        "acceleration_bonus": 2.0,
        "turning_bonus": 2.0,
        "accuracy_bonus": 10.0,
        "evasion_bonus": 10.0,
    }

    def __init__(self, session: Session):
        """Initialize the engineering service.

        Args:
            session: Database session
        """
        self.session = session
        self._FLOAT_STAT_CONFIGS: dict[str, _FloatStatConfig] = {
            "mobility": _FloatStatConfig(
                "mobility", self.MOBILITY_INCREASE, self.MAX_MOBILITY_CAP, "Mobility"
            ),
            "melee_aptitude": _FloatStatConfig(
                "melee_aptitude",
                self.MELEE_APTITUDE_INCREASE,
                self.MAX_MELEE_APTITUDE_CAP,
                "Melee aptitude",
            ),
            "shooting_aptitude": _FloatStatConfig(
                "shooting_aptitude",
                self.SHOOTING_APTITUDE_INCREASE,
                self.MAX_SHOOTING_APTITUDE_CAP,
                "Shooting aptitude",
            ),
            "accuracy_bonus": _FloatStatConfig(
                "accuracy_bonus",
                self.ACCURACY_BONUS_INCREASE,
                self.MAX_ACCURACY_BONUS_CAP,
                "Accuracy bonus",
            ),
            "evasion_bonus": _FloatStatConfig(
                "evasion_bonus",
                self.EVASION_BONUS_INCREASE,
                self.MAX_EVASION_BONUS_CAP,
                "Evasion bonus",
            ),
            "acceleration_bonus": _FloatStatConfig(
                "acceleration_bonus",
                self.ACCELERATION_BONUS_INCREASE,
                self.MAX_ACCELERATION_BONUS_CAP,
                "Acceleration bonus",
            ),
            "turning_bonus": _FloatStatConfig(
                "turning_bonus",
                self.TURNING_BONUS_INCREASE,
                self.MAX_TURNING_BONUS_CAP,
                "Turning bonus",
            ),
        }

    @staticmethod
    def _get_weapon_power(ms: MobileSuit) -> int | float:
        """Get the power of the first weapon on the mobile suit.

        Args:
            ms: Mobile suit to get weapon power from

        Returns:
            Power of the first weapon

        Raises:
            ValueError: If no weapons are equipped
        """
        if not ms.weapons or len(ms.weapons) == 0:
            raise ValueError("No weapons to upgrade")
        first_weapon = ms.weapons[0]
        return (
            first_weapon["power"]
            if isinstance(first_weapon, dict)
            else first_weapon.power
        )

    @classmethod
    def calculate_upgrade_cost(cls, stat_type: str, current_value: int | float) -> int:
        """Calculate upgrade cost based on current stat value.

        Higher stat values cost more to upgrade.

        Args:
            stat_type: Type of stat to upgrade
            current_value: Current value of the stat

        Returns:
            Cost in Credits for the upgrade
        """
        base_cost = cls._BASE_COSTS.get(stat_type, 100)
        divisor = cls._COST_DIVISORS.get(stat_type)
        multiplier = 1 + (current_value / divisor) if divisor is not None else 1
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
        elif stat_type == "weapon_power":
            current_value = self._get_weapon_power(ms)
            if current_value >= self.MAX_WEAPON_POWER_CAP:
                raise ValueError(
                    f"Weapon power is already at maximum ({self.MAX_WEAPON_POWER_CAP})"
                )
        elif stat_type in self._FLOAT_STAT_CONFIGS:
            cfg = self._FLOAT_STAT_CONFIGS[stat_type]
            current_value = getattr(ms, cfg.attr)
            if current_value >= cfg.cap:
                raise ValueError(f"{cfg.label} is already at maximum ({cfg.cap})")
        else:
            raise ValueError(
                f"Invalid stat type: {stat_type}. "
                "Must be one of: hp, armor, mobility, weapon_power, "
                "melee_aptitude, shooting_aptitude, accuracy_bonus, "
                "evasion_bonus, acceleration_bonus, turning_bonus"
            )

        cost = self.calculate_upgrade_cost(stat_type, current_value)
        return current_value, cost

    def _apply_upgrade(self, ms: MobileSuit, stat_type: str) -> None:
        """Apply the stat upgrade to the mobile suit.

        Args:
            ms: Mobile suit to upgrade
            stat_type: Type of stat to upgrade
        """
        if stat_type == "hp":
            self._apply_hp_upgrade(ms)
        elif stat_type == "armor":
            new_value = ms.armor + self.ARMOR_INCREASE
            ms.armor = int(min(new_value, self.MAX_ARMOR_CAP))
        elif stat_type == "weapon_power":
            self._apply_weapon_power_upgrade(ms)
        elif stat_type in self._FLOAT_STAT_CONFIGS:
            cfg = self._FLOAT_STAT_CONFIGS[stat_type]
            current: float = getattr(ms, cfg.attr)
            setattr(ms, cfg.attr, min(current + cfg.increment, cfg.cap))

    def _apply_hp_upgrade(self, ms: MobileSuit) -> None:
        """Apply HP upgrade to the mobile suit.

        Args:
            ms: Mobile suit to upgrade
        """
        old_max_hp = ms.max_hp
        ms.max_hp = int(min(ms.max_hp + self.HP_INCREASE, self.MAX_HP_CAP))
        if old_max_hp > 0:
            hp_ratio = ms.current_hp / old_max_hp
            ms.current_hp = int(ms.max_hp * hp_ratio)
        else:
            ms.current_hp = ms.max_hp

    def _apply_weapon_power_upgrade(self, ms: MobileSuit) -> None:
        """Apply weapon power upgrade to all weapons.

        Args:
            ms: Mobile suit to upgrade
        """
        weapons = list(ms.weapons)
        updated_weapons = []
        for weapon in weapons:
            if isinstance(weapon, dict):
                weapon["power"] = int(
                    min(
                        weapon["power"] + self.WEAPON_POWER_INCREASE,
                        self.MAX_WEAPON_POWER_CAP,
                    )
                )
            else:
                weapon.power = int(
                    min(
                        weapon.power + self.WEAPON_POWER_INCREASE,
                        self.MAX_WEAPON_POWER_CAP,
                    )
                )
            updated_weapons.append(weapon)
        ms.weapons = updated_weapons  # Reassign to trigger SQLAlchemy change detection
        attributes.flag_modified(ms, "weapons")

    def upgrade_stat(
        self, mobile_suit_id: str, stat_type: str, pilot: Pilot, steps: int = 1
    ) -> tuple[MobileSuit, Pilot, int]:
        """Upgrade a specific stat of a mobile suit one or more steps.

        All cost calculation and cap validation is performed server-side for each
        step so that client-supplied values are never trusted.

        Args:
            mobile_suit_id: ID of the mobile suit to upgrade
            stat_type: Type of stat to upgrade
            pilot: Pilot who owns the mobile suit
            steps: Number of upgrade steps to apply (default 1)

        Returns:
            tuple[MobileSuit, Pilot, int]: Updated mobile suit, pilot, and total cost

        Raises:
            ValueError: If stat is at max cap, invalid parameters, or steps < 1
            RuntimeError: If insufficient credits
        """
        if steps < 1:
            raise ValueError("steps must be at least 1")

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

        total_cost = 0
        for _ in range(steps):
            # Validate cap and compute cost for the current stat value
            _, cost = self._validate_and_get_cost(ms, stat_type)

            # Check if pilot has enough credits for this step
            if pilot.credits < cost:
                raise RuntimeError(
                    f"Insufficient credits. Required: {cost}, Available: {pilot.credits}"
                )

            # Deduct credits and apply upgrade
            pilot.credits -= cost
            total_cost += cost
            self._apply_upgrade(ms, stat_type)

        # Save changes
        self.session.add(ms)
        self.session.add(pilot)
        self.session.commit()
        self.session.refresh(ms)
        self.session.refresh(pilot)

        return ms, pilot, total_cost

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

        current: int | float
        new_value: int | float
        cap: int | float

        if stat_type == "hp":
            current, new_value, cap = (
                ms.max_hp,
                min(ms.max_hp + self.HP_INCREASE, self.MAX_HP_CAP),
                self.MAX_HP_CAP,
            )
        elif stat_type == "armor":
            current, new_value, cap = (
                ms.armor,
                min(ms.armor + self.ARMOR_INCREASE, self.MAX_ARMOR_CAP),
                self.MAX_ARMOR_CAP,
            )
        elif stat_type == "weapon_power":
            current = self._get_weapon_power(ms)
            new_value = min(
                current + self.WEAPON_POWER_INCREASE, self.MAX_WEAPON_POWER_CAP
            )
            cap = self.MAX_WEAPON_POWER_CAP
        elif stat_type in self._FLOAT_STAT_CONFIGS:
            cfg = self._FLOAT_STAT_CONFIGS[stat_type]
            current = getattr(ms, cfg.attr)
            new_value = min(current + cfg.increment, cfg.cap)
            cap = cfg.cap
        else:
            raise ValueError(f"Invalid stat type: {stat_type}")

        return {
            "current_value": current,
            "new_value": new_value,
            "cost": self.calculate_upgrade_cost(stat_type, current),
            "at_max_cap": current >= cap,
        }

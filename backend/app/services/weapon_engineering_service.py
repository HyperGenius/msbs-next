"""Engineering service for player weapon instance upgrades (custom_stats)."""

import uuid
from typing import NamedTuple

from sqlalchemy.orm import attributes
from sqlmodel import Session

from app.models.models import Pilot, PlayerWeapon, WeaponCustomStats


class _WeaponStatConfig(NamedTuple):
    """Configuration for a custom_stats upgrade target."""

    key: str
    base_field: str
    increment: int | float
    cap_multiplier: float
    base_cost: int
    divisor: float
    label: str


class WeaponEngineeringService:
    """Service for upgrading PlayerWeapon.custom_stats using Credits.

    NOTE (Issue #411): ``weapon_power``（機体側のパイロット/システム補正、
    ``EngineeringService`` 管理）とは別軸の、武器インスタンス単位の改造
    （``PlayerWeapon.custom_stats``）を扱う。武器を外す・付け替えても改造投資は
    失われない（PlayerWeapon に紐づくため）。未装備の武器も改造可能。
    """

    POWER_INCREASE = 5
    ACCURACY_INCREASE = 1.0

    # 上限キャップは base値（base_snapshot）に対する倍率
    # 例: power_bonus は実効値(base + bonus)が base の 200% に達するまで、
    #     accuracy_bonus は 130% に達するまで改造可能
    POWER_CAP_MULTIPLIER = 2.0
    ACCURACY_CAP_MULTIPLIER = 1.3

    BASE_POWER_COST = 60
    BASE_ACCURACY_COST = 100

    _STAT_CONFIGS: dict[str, _WeaponStatConfig] = {
        "power_bonus": _WeaponStatConfig(
            key="power_bonus",
            base_field="power",
            increment=POWER_INCREASE,
            cap_multiplier=POWER_CAP_MULTIPLIER,
            base_cost=BASE_POWER_COST,
            divisor=30.0,
            label="威力",
        ),
        "accuracy_bonus": _WeaponStatConfig(
            key="accuracy_bonus",
            base_field="accuracy",
            increment=ACCURACY_INCREASE,
            cap_multiplier=ACCURACY_CAP_MULTIPLIER,
            base_cost=BASE_ACCURACY_COST,
            divisor=5.0,
            label="命中率",
        ),
    }

    def __init__(self, session: Session):
        """Initialize the weapon engineering service.

        Args:
            session: Database session
        """
        self.session = session

    @classmethod
    def calculate_upgrade_cost(cls, stat_type: str, current_bonus: int | float) -> int:
        """Calculate upgrade cost based on the current bonus value.

        Args:
            stat_type: "power_bonus" or "accuracy_bonus"
            current_bonus: Current bonus value for the stat

        Returns:
            Cost in Credits for the next upgrade step

        Raises:
            ValueError: If stat_type is invalid
        """
        cfg = cls._STAT_CONFIGS.get(stat_type)
        if cfg is None:
            raise ValueError(
                f"Invalid stat type: {stat_type}. "
                "Must be one of: power_bonus, accuracy_bonus"
            )
        multiplier = 1 + (current_bonus / cfg.divisor)
        return int(cfg.base_cost * multiplier)

    @staticmethod
    def _get_player_weapon(session: Session, player_weapon_id: str) -> PlayerWeapon:
        pw_id = (
            uuid.UUID(player_weapon_id)
            if isinstance(player_weapon_id, str)
            else player_weapon_id
        )
        player_weapon = session.get(PlayerWeapon, pw_id)
        if not player_weapon:
            raise ValueError("武器インスタンスが見つかりません")
        return player_weapon

    def _validate_and_get_cost(
        self, player_weapon: PlayerWeapon, stat_type: str
    ) -> tuple[int | float, int]:
        """Validate cap and compute the cost for the next upgrade step.

        Args:
            player_weapon: Target weapon instance
            stat_type: "power_bonus" or "accuracy_bonus"

        Returns:
            tuple[int | float, int]: Current bonus value and cost

        Raises:
            ValueError: If stat is at max cap or invalid
        """
        cfg = self._STAT_CONFIGS.get(stat_type)
        if cfg is None:
            raise ValueError(
                f"Invalid stat type: {stat_type}. "
                "Must be one of: power_bonus, accuracy_bonus"
            )

        base_value = player_weapon.base_snapshot.get(cfg.base_field, 0)
        current_stats = WeaponCustomStats(**(player_weapon.custom_stats or {}))
        current_bonus = getattr(current_stats, stat_type)

        cap = base_value * cfg.cap_multiplier
        if base_value + current_bonus >= cap:
            raise ValueError(f"{cfg.label}は既に上限に達しています（上限: {cap}）")

        cost = self.calculate_upgrade_cost(stat_type, current_bonus)
        return current_bonus, cost

    def _apply_upgrade(self, player_weapon: PlayerWeapon, stat_type: str) -> None:
        """Apply one upgrade step to the weapon's custom_stats.

        Args:
            player_weapon: Target weapon instance
            stat_type: "power_bonus" or "accuracy_bonus"
        """
        cfg = self._STAT_CONFIGS[stat_type]
        base_value = player_weapon.base_snapshot.get(cfg.base_field, 0)
        cap = base_value * cfg.cap_multiplier

        current_stats = dict(player_weapon.custom_stats or {})
        current_bonus = getattr(WeaponCustomStats(**current_stats), stat_type)
        # 実効値(base + bonus)がキャップを超えないよう bonus 側で丸める
        new_bonus = min(current_bonus + cfg.increment, cap - base_value)

        current_stats[stat_type] = new_bonus
        player_weapon.custom_stats = current_stats
        attributes.flag_modified(player_weapon, "custom_stats")

    def upgrade_stat(
        self,
        player_weapon_id: str,
        stat_type: str,
        pilot: Pilot,
        steps: int = 1,
    ) -> tuple[PlayerWeapon, Pilot, int]:
        """Upgrade a specific custom_stats field of a player weapon.

        All cost calculation and cap validation is performed server-side for each
        step so that client-supplied values are never trusted. Unequipped weapons
        can be upgraded as well.

        Args:
            player_weapon_id: ID of the PlayerWeapon to upgrade
            stat_type: "power_bonus" or "accuracy_bonus"
            pilot: Pilot who owns the weapon
            steps: Number of upgrade steps to apply (default 1)

        Returns:
            tuple[PlayerWeapon, Pilot, int]: Updated weapon, pilot, and total cost

        Raises:
            ValueError: If stat is at max cap, invalid parameters, or steps < 1
            RuntimeError: If insufficient credits
        """
        if steps < 1:
            raise ValueError("steps must be at least 1")

        player_weapon = self._get_player_weapon(self.session, player_weapon_id)

        if player_weapon.user_id != pilot.user_id:
            raise ValueError("この武器インスタンスへのアクセス権がありません")

        total_cost = 0
        for _ in range(steps):
            _, cost = self._validate_and_get_cost(player_weapon, stat_type)

            if pilot.credits < cost:
                raise RuntimeError(
                    f"Insufficient credits. Required: {cost}, Available: {pilot.credits}"
                )

            pilot.credits -= cost
            total_cost += cost
            self._apply_upgrade(player_weapon, stat_type)

        self.session.add(player_weapon)
        self.session.add(pilot)
        self.session.commit()
        self.session.refresh(player_weapon)
        self.session.refresh(pilot)

        return player_weapon, pilot, total_cost

    def get_upgrade_preview(self, player_weapon_id: str, stat_type: str) -> dict:
        """Get a preview of what the next upgrade step would do.

        Args:
            player_weapon_id: ID of the PlayerWeapon
            stat_type: "power_bonus" or "accuracy_bonus"

        Returns:
            dict with current_value, new_value, cost, and at_max_cap

        Raises:
            ValueError: If the weapon is not found or stat_type is invalid
        """
        player_weapon = self._get_player_weapon(self.session, player_weapon_id)

        cfg = self._STAT_CONFIGS.get(stat_type)
        if cfg is None:
            raise ValueError(f"Invalid stat type: {stat_type}")

        base_value = player_weapon.base_snapshot.get(cfg.base_field, 0)
        current_stats = WeaponCustomStats(**(player_weapon.custom_stats or {}))
        current_bonus = getattr(current_stats, stat_type)
        cap = base_value * cfg.cap_multiplier

        new_bonus = min(current_bonus + cfg.increment, cap - base_value)

        return {
            "current_value": current_bonus,
            "new_value": new_bonus,
            "cost": self.calculate_upgrade_cost(stat_type, current_bonus),
            "at_max_cap": base_value + current_bonus >= cap,
        }

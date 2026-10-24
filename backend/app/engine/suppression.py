# backend/app/engine/suppression.py
"""射撃の制圧（撃たれた機体の足止め）の計算と、シミュレータへの組み込み.

制圧値は `unit_resources` の `suppression` に持つ。値は 0〜`max_value`。
"""

import math
import uuid
from dataclasses import dataclass

from app.engine.battle_utils import is_melee_weapon
from app.engine.constants import (
    SUPPRESSION_ADVANCE_ONLY,
    SUPPRESSION_DECAY_RATE,
    SUPPRESSION_HIT_MULTIPLIER,
    SUPPRESSION_LOG_ENTER_VALUE,
    SUPPRESSION_LOG_EXIT_VALUE,
    SUPPRESSION_MAX_SPEED_PENALTY,
    SUPPRESSION_MAX_VALUE,
    SUPPRESSION_MIN_COOLDOWN_SEC,
    SUPPRESSION_PER_COOLDOWN_SEC,
    SUPPRESSION_SPARED_ACTIONS,
)
from app.engine.facing import is_backpedaling
from app.models.models import BattleLog, MobileSuit, Vector3, Weapon

# 指数で減らすと 0 にならない。ログに出す最小単位（整数）より小さくなったら 0 にする。
_SUPPRESSION_ZERO_BELOW = 0.5


@dataclass(frozen=True)
class SuppressionConfig:
    """制圧の係数. `BattleSimulator` に渡すと制圧が有効になる."""

    per_cooldown_sec: float = SUPPRESSION_PER_COOLDOWN_SEC
    """外れた 1 発が加える量。武器の再使用待ち 1 秒あたり。"""
    hit_multiplier: float = SUPPRESSION_HIT_MULTIPLIER
    max_value: float = SUPPRESSION_MAX_VALUE
    decay_rate: float = SUPPRESSION_DECAY_RATE
    """1 秒あたりに減る割合。撃たれ続けると、毎秒の加算量 ÷ この値で釣り合う。"""
    max_speed_penalty: float = SUPPRESSION_MAX_SPEED_PENALTY
    """制圧値が上限のときに最高速度から引く割合。"""
    advance_only: bool = SUPPRESSION_ADVANCE_ONLY
    """真なら、後退・逃走中（`is_falling_back()`）は減速しない。"""


def shot_suppression(config: SuppressionConfig, weapon: Weapon, is_hit: bool) -> float:
    """射撃 1 発で狙われた機体に加える制圧値を返す.

    再使用待ちに比例させる。連射武器は 1 発が小さく、毎秒の量は武器によらずそろう。
    """
    cooldown = max(
        float(getattr(weapon, "cooldown_sec", 0.0)), SUPPRESSION_MIN_COOLDOWN_SEC
    )
    amount = config.per_cooldown_sec * cooldown
    return amount * config.hit_multiplier if is_hit else amount


def add_suppression(config: SuppressionConfig, resources: dict, amount: float) -> float:
    """制圧値を加える. 加えた後の制圧値を返す."""
    value = min(config.max_value, resources.get("suppression", 0.0) + amount)
    resources["suppression"] = value
    return value


def decay_suppression(config: SuppressionConfig, resources: dict, dt: float) -> float:
    """制圧値を `dt` 秒ぶん減らす. 減らした後の制圧値を返す."""
    value = resources.get("suppression", 0.0)
    if value <= 0.0:
        return 0.0
    value *= math.exp(-config.decay_rate * dt)
    if value < _SUPPRESSION_ZERO_BELOW:
        value = 0.0
    resources["suppression"] = value
    return value


def suppression_speed_multiplier(config: SuppressionConfig, value: float) -> float:
    """制圧値から、最高速度に掛ける倍率を返す（向きは考えない）."""
    ratio = min(1.0, max(0.0, value / config.max_value))
    return 1.0 - config.max_speed_penalty * ratio


def is_falling_back(resources: dict, movement_heading_deg: float) -> bool:
    """後退・逃走中かを返す.

    撤退・仕切り直し・ヒットアンドアウェイの行動、逃走中、胴体と逆へ動く後退のどれか。
    """
    return (
        resources.get("current_action") in SUPPRESSION_SPARED_ACTIONS
        or bool(resources.get("fleeing", False))
        or is_backpedaling(
            resources.get("body_heading_deg", movement_heading_deg),
            movement_heading_deg,
        )
    )


class SuppressionMixin:
    """制圧の蓄積・減衰・減速のミックスイン.

    `self.suppression` が None のときは何もしない。
    """

    def _apply_shot_suppression(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        weapon: Weapon,
        is_hit: bool,
        log_details: dict | None,
    ) -> dict | None:
        """射撃 1 発ぶんの制圧値を狙われた機体に加える.

        Returns:
            ATTACK / MISS ログの `details`。加えた後の制圧値を `target_suppression` に足す。
            制圧が無効か格闘武器のときは `log_details` をそのまま返す。
        """
        config: SuppressionConfig | None = self.suppression  # type: ignore[attr-defined]
        if config is None or is_melee_weapon(weapon):
            return log_details
        resources = self.unit_resources[str(target.id)]  # type: ignore[attr-defined]
        value = add_suppression(
            config, resources, shot_suppression(config, weapon, is_hit)
        )
        return {**(log_details or {}), "target_suppression": round(value)}

    def _log_suppression_start(self, actor: MobileSuit, target: MobileSuit) -> None:
        """狙われた機体の制圧値が閾値を超えたら SUPPRESSED を出す.

        射撃の ATTACK / MISS の後に呼ぶ。ログの順を「撃った → 押さえ込まれた」にするため。
        """
        if self.suppression is None or target.current_hp <= 0:  # type: ignore[attr-defined]
            return
        resources = self.unit_resources[str(target.id)]  # type: ignore[attr-defined]
        value = resources.get("suppression", 0.0)
        if resources.get("suppression_logged") or value < SUPPRESSION_LOG_ENTER_VALUE:
            return
        resources["suppression_logged"] = True
        self._log_suppression(target, "SUPPRESSED", value, actor.id)

    def _suppression_decay_phase(self, dt: float) -> None:
        """生存している全機の制圧値を `dt` 秒ぶん減らす."""
        config: SuppressionConfig | None = self.suppression  # type: ignore[attr-defined]
        if config is None:
            return
        for unit in self.units:  # type: ignore[attr-defined]
            if unit.current_hp <= 0:
                continue
            resources = self.unit_resources[str(unit.id)]  # type: ignore[attr-defined]
            value = decay_suppression(config, resources, dt)
            if (
                resources.get("suppression_logged")
                and value < SUPPRESSION_LOG_EXIT_VALUE
            ):
                resources["suppression_logged"] = False
                self._log_suppression(unit, "SUPPRESSION_END", value, None)

    def _suppression_speed_multiplier(
        self, resources: dict, movement_heading_deg: float
    ) -> float:
        """制圧による最高速度の倍率を返す."""
        config: SuppressionConfig | None = self.suppression  # type: ignore[attr-defined]
        value = resources.get("suppression", 0.0)
        if config is None or value <= 0.0:
            return 1.0
        if config.advance_only and is_falling_back(resources, movement_heading_deg):
            return 1.0
        return suppression_speed_multiplier(config, value)

    def _log_suppression(
        self,
        unit: MobileSuit,
        action_type: str,
        value: float,
        source_id: uuid.UUID | None,
    ) -> None:
        """制圧の始まり（SUPPRESSED）と終わり（SUPPRESSION_END）をログに出す."""
        config: SuppressionConfig = self.suppression  # type: ignore[attr-defined]
        resources = self.unit_resources[str(unit.id)]  # type: ignore[attr-defined]
        name = self._format_actor_name(unit)  # type: ignore[attr-defined]
        message = (
            f"{name}が弾幕に押さえ込まれた"
            if action_type == "SUPPRESSED"
            else f"{name}への制圧が解けた"
        )
        self.logs.append(  # type: ignore[attr-defined]
            BattleLog(
                timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                actor_id=unit.id,
                action_type=action_type,
                target_id=source_id,
                message=message,
                position_snapshot=unit.position,
                velocity_snapshot=Vector3.from_numpy(resources["velocity_vec"]),
                heading=resources.get("body_heading_deg"),
                details={
                    "suppression": round(value),
                    "speed_multiplier": round(
                        suppression_speed_multiplier(config, value), 2
                    ),
                },
            )
        )

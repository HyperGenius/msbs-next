# backend/app/engine/melee_clash.py
"""鍔迫り合い（正面同士の同時格闘）の判定と押し離しのミックスイン."""

import random
from dataclasses import dataclass

import numpy as np

from app.engine.battle_utils import is_melee_weapon
from app.engine.calculator import PilotStats
from app.engine.combat import calculate_attack_sector
from app.engine.constants import (
    MELEE_BOOST_ARRIVAL_RANGE,
    MELEE_CLASH_CHANCE,
    MELEE_CLASH_COOLDOWN_SEC,
    MELEE_CLASH_KNOCKBACK_SEC,
    MELEE_CLASH_MEL_WEIGHT,
    MELEE_CLASH_PUSH_SHARE_MAX,
    MELEE_CLASH_SEPARATION_MAX,
    MELEE_CLASH_SEPARATION_MIN,
    MELEE_CLASH_WINDOW_SEC,
)
from app.models.models import BattleLog, MobileSuit, Weapon


@dataclass
class Knockback:
    """押し離しで受けている速度. 機体自身の速度（`velocity_vec`）とは別に持つ."""

    velocity: np.ndarray
    deceleration: float


def start_knockback(
    direction: np.ndarray, distance: float, duration: float
) -> Knockback:
    """`duration` 秒で止まり、合計 `distance` だけ進む押し離しを作る."""
    speed = 2.0 * distance / duration
    return Knockback(velocity=direction * speed, deceleration=speed / duration)


def advance_knockback(
    knockback: Knockback, dt: float
) -> tuple[np.ndarray, Knockback | None]:
    """押し離しを `dt` 秒進める.

    速度の平均で進めるため、合計の移動量は作ったときの距離に一致する。

    Returns:
        この間の移動量と、残りの押し離し。止まったら残りは None。
    """
    speed = float(np.linalg.norm(knockback.velocity))
    if speed < 1e-6:
        return np.zeros(3), None
    direction = knockback.velocity / speed
    moving_sec = min(dt, speed / knockback.deceleration)
    new_speed = max(0.0, speed - knockback.deceleration * dt)
    displacement = direction * (speed + new_speed) / 2.0 * moving_sec
    if new_speed <= 0.0:
        return displacement, None
    return displacement, Knockback(direction * new_speed, knockback.deceleration)


def push_shares(power_a: float, power_b: float) -> tuple[float, float]:
    """押し離しで広がる間隔のうち、A と B がそれぞれ受け持つ割合を返す.

    押す力の弱い側が大きく飛ばされる。割合は `MELEE_CLASH_PUSH_SHARE_MAX` で抑える。
    """
    total = power_a + power_b
    share_a = 0.5 if total <= 0.0 else power_b / total
    share_a = max(
        1.0 - MELEE_CLASH_PUSH_SHARE_MAX, min(MELEE_CLASH_PUSH_SHARE_MAX, share_a)
    )
    return share_a, 1.0 - share_a


class MeleeClashMixin:
    """鍔迫り合いの判定と押し離しのミックスイン."""

    def _try_melee_clash(
        self, actor: MobileSuit, target: MobileSuit, weapon: Weapon, distance: float
    ) -> bool:
        """正面同士の同時格闘なら鍔迫り合いにする.

        先に行動した側が判定する。相手の攻撃が先に解決されて撃破される、
        といった処理順の偏りを避けるため。乱数は条件がそろったときだけ引く。

        Returns:
            鍔迫り合いにした場合 True。呼び出し元は通常の命中判定をしない。
        """
        if not is_melee_weapon(weapon) or not (
            self._can_clash(actor) and self._can_clash(target)
        ):
            return False
        opponent_weapon = self._pending_melee_weapon(target, actor, distance)
        if opponent_weapon is None or not self._faces_each_other(actor, target):
            return False
        if random.random() >= MELEE_CLASH_CHANCE:
            return False
        self._resolve_melee_clash(actor, target, weapon, opponent_weapon)
        return True

    def _can_clash(self, unit: MobileSuit) -> bool:
        """前回の鍔迫り合いから `MELEE_CLASH_COOLDOWN_SEC` 以上たったかを返す."""
        last = self.unit_resources[str(unit.id)].get("last_melee_clash_at")  # type: ignore[attr-defined]
        return last is None or self.elapsed_time - last >= MELEE_CLASH_COOLDOWN_SEC  # type: ignore[attr-defined]

    def _pending_melee_weapon(
        self, unit: MobileSuit, target: MobileSuit, distance: float
    ) -> Weapon | None:
        """`unit` が `MELEE_CLASH_WINDOW_SEC` 以内に `target` へ出す格闘武器を返す.

        行動フェーズでの武器の選び方に合わせる。ENGAGE_MELEE は先頭の格闘武器で、
        ATTACK と HIT_AND_AWAY は手持ちの武器で攻撃する。

        Returns:
            格闘を出さない（ターゲットが違う・持ち替え中・射程外など）場合は None。
        """
        unit_id = str(unit.id)
        resources = self.unit_resources[unit_id]  # type: ignore[attr-defined]
        if (
            unit.current_hp <= 0
            or resources.get("status") == "RETREATED"
            or resources.get("weapon_switch_lock_remaining_sec", 0.0) > 0.0
            or self._select_target_fuzzy(unit) is not target  # type: ignore[attr-defined]
        ):
            return None

        action = resources.get("current_action")
        weapon: Weapon | None
        if action == "ENGAGE_MELEE":
            if distance > MELEE_BOOST_ARRIVAL_RANGE:
                return None
            weapon = next((w for w in unit.weapons if is_melee_weapon(w)), None)
        elif action in ("ATTACK", "HIT_AND_AWAY"):
            weapon = self._resolve_fallback_weapon(unit, unit_id)  # type: ignore[attr-defined]
        else:
            return None
        if weapon is None or not is_melee_weapon(weapon) or distance > weapon.range:
            return None

        weapon_state = resources["weapon_states"].get(weapon.id) or {}
        if weapon_state.get("cooldown_remaining_sec", 0.0) > MELEE_CLASH_WINDOW_SEC:
            return None
        return weapon

    def _faces_each_other(self, a: MobileSuit, b: MobileSuit) -> bool:
        """互いの攻撃セクタがどちらも FRONT かを返す."""
        pos_a = a.position.to_numpy()
        pos_b = b.position.to_numpy()
        heading_a = self.unit_resources[str(a.id)].get("body_heading_deg", 0.0)  # type: ignore[attr-defined]
        heading_b = self.unit_resources[str(b.id)].get("body_heading_deg", 0.0)  # type: ignore[attr-defined]
        return (
            calculate_attack_sector(pos_a, pos_b, heading_b) == "FRONT"
            and calculate_attack_sector(pos_b, pos_a, heading_a) == "FRONT"
        )

    def _clash_power(self, unit: MobileSuit, weapon: Weapon) -> float:
        """鍔迫り合いで押す力を返す. 武器の威力・格闘適性・パイロットの MEL で決まる."""
        stats = self.unit_pilot_stats.get(str(unit.id), PilotStats())  # type: ignore[attr-defined]
        return (
            float(weapon.power)
            * float(getattr(unit, "melee_aptitude", 1.0))
            * (1.0 + stats.mel * MELEE_CLASH_MEL_WEIGHT)
        )

    def _resolve_melee_clash(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        actor_weapon: Weapon,
        target_weapon: Weapon,
    ) -> None:
        """両機の格闘を鍔迫り合いとして解決し、反対方向へ押し離す.

        ダメージは無い。両機の武器は攻撃したものとして再使用待ちに入る。
        両機の速度を 0 にする。突進の速度が残ると、押し離しを打ち消すため。
        """
        actor_resources = self.unit_resources[str(actor.id)]  # type: ignore[attr-defined]
        target_resources = self.unit_resources[str(target.id)]  # type: ignore[attr-defined]
        for unit_weapon, resources in (
            (actor_weapon, actor_resources),
            (target_weapon, target_resources),
        ):
            weapon_state = self._get_or_init_weapon_state(unit_weapon, resources)  # type: ignore[attr-defined]
            self._consume_attack_resources(unit_weapon, weapon_state, resources)  # type: ignore[attr-defined]

        pos_actor = actor.position.to_numpy()
        away = pos_actor - target.position.to_numpy()
        away[1] = 0.0
        away_dist = float(np.linalg.norm(away))
        away = away / away_dist if away_dist > 1e-6 else np.array([1.0, 0.0, 0.0])

        separation = random.uniform(
            MELEE_CLASH_SEPARATION_MIN, MELEE_CLASH_SEPARATION_MAX
        )
        actor_share, target_share = push_shares(
            self._clash_power(actor, actor_weapon),
            self._clash_power(target, target_weapon),
        )
        actor_push = separation * actor_share
        target_push = separation * target_share
        actor_resources["knockback"] = start_knockback(
            away, actor_push, MELEE_CLASH_KNOCKBACK_SEC
        )
        target_resources["knockback"] = start_knockback(
            -away, target_push, MELEE_CLASH_KNOCKBACK_SEC
        )
        for resources in (actor_resources, target_resources):
            resources["velocity_vec"] = np.zeros(3)
            resources["last_melee_clash_at"] = self.elapsed_time  # type: ignore[attr-defined]

        # 交戦記録には、両機が互いに 1 回ずつ外した攻撃として残す。
        self._record_attack_exchange(actor, target, 0)  # type: ignore[attr-defined]
        self._record_attack_exchange(target, actor, 0)  # type: ignore[attr-defined]

        self._log_melee_clash(
            actor, target, actor_weapon, target_weapon, actor_push, target_push
        )

    def _log_melee_clash(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        actor_weapon: Weapon,
        target_weapon: Weapon,
        actor_push: float,
        target_push: float,
    ) -> None:
        """鍔迫り合いのログを追記する."""
        actor_name = self._format_actor_name(actor)  # type: ignore[attr-defined]
        target_name = self._format_actor_name(target)  # type: ignore[attr-defined]
        message = (
            f"{actor_name}の[{actor_weapon.name}]と{target_name}の"
            f"[{target_weapon.name}]が鍔迫り合い！"
        )
        if actor_push > target_push * 1.2:
            message += f" {actor_name}が押し負けて弾き飛ばされる"
        elif target_push > actor_push * 1.2:
            message += f" {target_name}が押し負けて弾き飛ばされる"
        else:
            message += " 両機が弾かれて間合いが開く"
        self.logs.append(  # type: ignore[attr-defined]
            BattleLog(
                timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                actor_id=actor.id,
                action_type="MELEE_CLASH",
                target_id=target.id,
                message=message,
                position_snapshot=actor.position,
                chatter=self._generate_chatter(actor, "clash"),  # type: ignore[attr-defined]
                weapon_name=actor_weapon.name,
                weapon_id=actor_weapon.id,
                damage=0,
                details={
                    "target_weapon_name": target_weapon.name,
                    "target_weapon_id": target_weapon.id,
                    "actor_push_m": round(actor_push, 1),
                    "target_push_m": round(target_push, 1),
                },
            )
        )

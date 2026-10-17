# backend/app/engine/flee.py
"""機体が逃げるべき度合い（逃走度）を計算する.

戦闘エンジンの状態には依存しない。命中率は呼び出し側が計算して渡す。
逃走度は 0〜1 で、攻撃手段の有無と戦力差から決める。
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass

from app.engine.battle_utils import is_melee_weapon
from app.engine.constants import (
    FLEE_EN_WAIT_SEC,
    FLEE_ENTER_THRESHOLD,
    FLEE_EXIT_THRESHOLD,
    FLEE_MIN_COOLDOWN_SEC,
    FLEE_POWER_RATIO_HIGH,
    FLEE_POWER_RATIO_LOW,
    FLEE_POWER_WEIGHTS,
)
from app.models.models import Weapon


@dataclass(frozen=True)
class FleeAssessment:
    """逃走度とその内訳."""

    score: float
    # 攻撃手段が無い度合い。使える武器があれば 0、無ければ 1。
    means: float
    # 戦力差の度合い（重み掛け前）。
    power: float
    # 戦力比（自機が倒す時間 ÷ 倒される時間）。脅威になる敵がいなければ None。
    ratio: float | None
    threat_count: int
    # 自機が脅威の敵をすべて倒すまでの見込み時間 (s)。倒せなければ None。
    kill_sec: float | None
    # 脅威の敵が自機を倒すまでの見込み時間 (s)。脅威が無ければ None。
    killed_sec: float | None

    def to_details(self) -> dict[str, float | int | None]:
        """AI_DECISION ログの `details` に載せる辞書を返す."""
        return {
            "flee_score": round(self.score, 3),
            "flee_means": round(self.means, 3),
            "flee_power": round(self.power, 3),
            "flee_ratio": (
                None
                if self.ratio is None or math.isinf(self.ratio)
                else round(self.ratio, 3)
            ),
            "flee_threat_count": self.threat_count,
        }


def expected_dps(weapon: Weapon, hit_percent: float) -> float:
    """武器の期待 DPS を返す. 威力 × 見込み命中率 ÷ 再使用待ち時間."""
    cooldown = max(weapon.cooldown_sec, FLEE_MIN_COOLDOWN_SEC)
    return weapon.power * (hit_percent / 100.0) / cooldown


def attack_wait_sec(
    weapon: Weapon, ammo: int | None, current_en: float, en_recovery: float
) -> float | None:
    """再使用待ちを除いて、武器が使えるようになるまでの秒数を返す.

    弾切れと、待っても EN が足りない場合は None。格闘武器は常に 0。
    """
    if is_melee_weapon(weapon):
        return 0.0
    if weapon.max_ammo and weapon.max_ammo > 0 and (ammo is None or ammo <= 0):
        return None
    shortage = weapon.en_cost - current_en
    if weapon.en_cost <= 0 or shortage <= 0:
        return 0.0
    if en_recovery <= 0:
        return None
    wait = shortage / en_recovery
    return wait if wait <= FLEE_EN_WAIT_SEC else None


def means_score(waits: Iterable[float | None]) -> float:
    """攻撃手段が無い度合いを返す. どの武器も使えるようにならなければ 1.0.

    EN の回復を待てば撃てる武器があれば、待ち時間に応じて 0〜1 の値にする。
    """
    feasible = [w for w in waits if w is not None]
    if not feasible:
        return 1.0
    return min(feasible) / FLEE_EN_WAIT_SEC


def power_score(ratio: float | None) -> float:
    """戦力比を 0〜1 に直す. 比は対数で見て、下限で 0、上限で 1 になる."""
    if ratio is None:
        return 0.0
    if ratio >= FLEE_POWER_RATIO_HIGH:
        return 1.0
    if ratio <= FLEE_POWER_RATIO_LOW:
        return 0.0
    low, high = math.log(FLEE_POWER_RATIO_LOW), math.log(FLEE_POWER_RATIO_HIGH)
    return (math.log(ratio) - low) / (high - low)


def assess_flee(
    *,
    strategy_mode: str,
    my_hp: float,
    waits: Iterable[float | None],
    my_dps_by_enemy: list[tuple[float, float]],
    enemy_dps: list[float],
) -> FleeAssessment:
    """逃走度を計算する.

    Args:
        strategy_mode: 戦略モード。戦力差の重みを決める。
        my_hp: 自機の残り HP。
        waits: 自機の各武器の `attack_wait_sec()`。
        my_dps_by_enemy: 脅威の敵ごとの (残り HP, 自機の最良の期待 DPS)。
        enemy_dps: 脅威の敵ごとの、敵の最良の期待 DPS。
    """
    means = means_score(waits)
    threat_count = len(my_dps_by_enemy)
    if threat_count == 0:
        return FleeAssessment(means, means, 0.0, None, 0, None, None)

    total_enemy_dps = sum(enemy_dps)
    killed_sec = my_hp / total_enemy_dps if total_enemy_dps > 0 else None
    if any(dps <= 0 for _, dps in my_dps_by_enemy):
        kill_sec = None
    else:
        kill_sec = sum(hp / dps for hp, dps in my_dps_by_enemy)

    if killed_sec is None:
        ratio: float | None = None
    elif kill_sec is None:
        ratio = math.inf
    else:
        ratio = kill_sec / killed_sec
    power = power_score(ratio)
    weighted = min(1.0, power * FLEE_POWER_WEIGHTS.get(strategy_mode, 1.0))
    score = 1.0 if means >= 1.0 else max(means, weighted)
    return FleeAssessment(
        score, means, power, ratio, threat_count, kill_sec, killed_sec
    )


def next_flee_state(fleeing: bool, score: float) -> bool:
    """ヒステリシスを掛けて、逃走中かどうかを返す.

    入るしきい値と抜けるしきい値を分け、毎ステップの揺れで切り替わらないようにする。
    """
    if fleeing:
        return score >= FLEE_EXIT_THRESHOLD
    return score >= FLEE_ENTER_THRESHOLD

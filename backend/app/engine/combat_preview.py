# backend/app/engine/combat_preview.py
"""管理画面向け 1対1 攻撃シミュレーション（Issue #381）.

`BattleSimulator` インスタンス状態（player_skills / unit_resources / special_effects）に
依存せず、機体スペック・武器・パイロットステータスのみから命中率・クリティカル率・
ダメージを計算する。`combat.py` / `calculator.py` の計算式と完全に一致させ、実戦との
乖離が生じないようにする。

決定論モード: 乱数を振らず、命中率・クリティカル率・理論ダメージ値を返す。
モンテカルロモード: 決定論値をもとに実際に random 判定を N 回試行し、統計値を返す。
"""

import random
from dataclasses import dataclass

from app.engine.calculator import (
    PilotStats,
    calculate_critical_chance,
    calculate_damage_variance,
    calculate_hit_chance,
)
from app.engine.combat import CombatMixin, _sigmoid_attack, _sigmoid_defense
from app.engine.constants import SECTOR_ACCURACY_MODIFIERS, SECTOR_DAMAGE_MODIFIERS
from app.models.models import MasterMobileSuitSpec, Weapon

BASE_CRIT_RATE = 0.05


@dataclass
class DeterministicCombatResult:
    """乱数を振らない理論値."""

    hit_chance: float
    crit_chance: float
    base_damage: int
    crit_damage: int
    resistance_applied_damage: int


@dataclass
class MonteCarloCombatResult:
    """N回試行した実測統計値."""

    trials: int
    actual_hit_rate: float
    actual_crit_rate: float
    avg_damage: float
    min_damage: int
    max_damage: int
    perfect_evade_rate: float


def _is_melee_weapon(weapon: Weapon) -> bool:
    return weapon.weapon_type == "MELEE" or weapon.is_melee


def calculate_deterministic_combat_stats(
    attacker_spec: MasterMobileSuitSpec,
    attacker_pilot: PilotStats,
    weapon: Weapon,
    defender_spec: MasterMobileSuitSpec,
    defender_pilot: PilotStats,
    distance: float,
    attack_sector: str,
) -> DeterministicCombatResult:
    """命中率・クリティカル率・ダメージの理論値（乱数なし）を計算する.

    `combat.py` の `_calculate_hit_chance` / `_calculate_hit_base_damage` /
    `_apply_hit_damage_modifiers` と同一の計算式を使用する（スキル補正・障害物補正・
    プレイヤー限定スキルは対象外。機体パラメータとパイロットステータスのみで完結する）。
    """
    is_melee = _is_melee_weapon(weapon)

    # --- 命中率 ---
    distance_from_optimal = abs(distance - weapon.optimal_range)
    dist_penalty = distance_from_optimal * weapon.decay_rate
    evasion_bonus = defender_spec.mobility * 10
    hit_chance = float(weapon.accuracy - dist_penalty - evasion_bonus)

    attacker_dex = attacker_pilot.mel if is_melee else attacker_pilot.sht
    defender_int = defender_pilot.intel
    hit_chance = calculate_hit_chance(
        hit_chance,
        distance_from_optimal=distance_from_optimal,
        decay_rate=weapon.decay_rate,
        attacker_dex=attacker_dex,
        defender_int=defender_int,
    )

    weapon_type = "MELEE" if is_melee else weapon.weapon_type
    accuracy_modifier = CombatMixin._get_accuracy_modifier(distance, weapon_type)
    hit_chance *= accuracy_modifier
    hit_chance *= SECTOR_ACCURACY_MODIFIERS[attack_sector]
    hit_chance += attacker_spec.accuracy_bonus
    hit_chance -= defender_spec.evasion_bonus
    hit_chance = max(0.0, min(100.0, hit_chance))

    # --- クリティカル率 ---
    crit_chance = calculate_critical_chance(
        BASE_CRIT_RATE,
        attacker_int=attacker_pilot.intel,
        defender_tou=defender_pilot.tou,
    )

    # --- 基礎ダメージ（シグモイド式） ---
    total_atk = attacker_pilot.mel if is_melee else attacker_pilot.sht
    attack_bonus = _sigmoid_attack(float(total_atk))
    total_def = defender_spec.armor + defender_pilot.tou
    defense_reduction = _sigmoid_defense(float(total_def))
    base_damage = max(
        1, int(weapon.power * (1.0 + attack_bonus) * (1.0 - defense_reduction))
    )
    base_damage = max(1, int(base_damage * SECTOR_DAMAGE_MODIFIERS[attack_sector]))

    crit_damage = int(weapon.power * 1.2)

    # --- 適性・耐性補正（クリティカル/非クリティカル共通） ---
    aptitude = (
        attacker_spec.melee_aptitude if is_melee else attacker_spec.shooting_aptitude
    )
    resistance_applied_damage = int(base_damage * aptitude)
    if not is_melee:
        if weapon.type == "BEAM":
            resistance_applied_damage = int(
                resistance_applied_damage * (1.0 - defender_spec.beam_resistance)
            )
        elif weapon.type == "PHYSICAL":
            resistance_applied_damage = int(
                resistance_applied_damage * (1.0 - defender_spec.physical_resistance)
            )

    return DeterministicCombatResult(
        hit_chance=hit_chance,
        crit_chance=crit_chance * 100.0,
        base_damage=base_damage,
        crit_damage=crit_damage,
        resistance_applied_damage=resistance_applied_damage,
    )


def run_monte_carlo_combat_stats(
    deterministic: DeterministicCombatResult,
    attacker_pilot: PilotStats,
    defender_pilot: PilotStats,
    trials: int,
) -> MonteCarloCombatResult:
    """決定論値をもとに実際の乱数判定をN回試行し、統計を集計する.

    `combat.py` の `_process_attack` / `_process_hit` と同一の判定順序
    （命中判定 → クリティカル判定 → ダメージ乱数変動）で乱数を消費する。
    """
    hit_count = 0
    crit_count = 0
    perfect_evade_count = 0
    damages: list[int] = []

    for _ in range(trials):
        roll = random.uniform(0, 100)
        if roll > deterministic.hit_chance:
            continue
        hit_count += 1

        is_crit = random.random() < (deterministic.crit_chance / 100.0)
        base_damage = (
            deterministic.crit_damage
            if is_crit
            else deterministic.resistance_applied_damage
        )
        if is_crit:
            crit_count += 1

        final_damage, perfect_evade = calculate_damage_variance(
            base_damage,
            attacker_luk=attacker_pilot.luk,
            attacker_tou=attacker_pilot.tou,
            defender_dex=0,
            defender_tou=defender_pilot.tou,
            defender_luk=defender_pilot.luk,
        )
        if perfect_evade:
            perfect_evade_count += 1
        damages.append(final_damage)

    actual_hit_rate = (hit_count / trials * 100.0) if trials else 0.0
    actual_crit_rate = (crit_count / hit_count * 100.0) if hit_count else 0.0
    perfect_evade_rate = (perfect_evade_count / hit_count * 100.0) if hit_count else 0.0
    avg_damage = (sum(damages) / len(damages)) if damages else 0.0
    min_damage = min(damages) if damages else 0
    max_damage = max(damages) if damages else 0

    return MonteCarloCombatResult(
        trials=trials,
        actual_hit_rate=actual_hit_rate,
        actual_crit_rate=actual_crit_rate,
        avg_damage=avg_damage,
        min_damage=min_damage,
        max_damage=max_damage,
        perfect_evade_rate=perfect_evade_rate,
    )

# backend/app/services/combat_simulation_service.py
"""管理画面向け 1対1 攻撃シミュレーションサービス（Issue #381）."""

from app.engine.calculator import PilotStats
from app.engine.combat_preview import (
    calculate_deterministic_combat_stats,
    run_monte_carlo_combat_stats,
)
from app.engine.constants import SECTOR_ACCURACY_MODIFIERS
from app.models.models import (
    CombatSimulationRequest,
    CombatSimulationResponse,
    MonteCarloCombatStats,
    PilotStatsInput,
)


def _to_pilot_stats(pilot_input: PilotStatsInput) -> PilotStats:
    return PilotStats(
        sht=pilot_input.sht,
        mel=pilot_input.mel,
        intel=pilot_input.intel,
        ref=pilot_input.ref,
        tou=pilot_input.tou,
        luk=pilot_input.luk,
    )


class CombatSimulationService:
    """1対1 攻撃シミュレーションを実行するサービス."""

    @staticmethod
    def simulate(request: CombatSimulationRequest) -> CombatSimulationResponse:
        """機体・武器・パイロットステータスから命中率・ダメージを計算する.

        Raises:
            ValueError: 武器IDが見つからない、または attack_sector が不正な場合
        """
        if request.attack_sector not in SECTOR_ACCURACY_MODIFIERS:
            valid_sectors = ", ".join(SECTOR_ACCURACY_MODIFIERS.keys())
            raise ValueError(
                f"Invalid attack_sector '{request.attack_sector}'. "
                f"Valid values: {valid_sectors}"
            )

        weapon = next(
            (
                w
                for w in request.attacker_spec.weapons
                if w.id == request.attacker_weapon_id
            ),
            None,
        )
        if weapon is None:
            raise ValueError(
                f"Weapon '{request.attacker_weapon_id}' not found in attacker_spec.weapons"
            )

        distance = (
            request.distance if request.distance is not None else weapon.optimal_range
        )

        deterministic = calculate_deterministic_combat_stats(
            attacker_spec=request.attacker_spec,
            attacker_pilot=_to_pilot_stats(request.attacker_pilot),
            weapon=weapon,
            defender_spec=request.defender_spec,
            defender_pilot=_to_pilot_stats(request.defender_pilot),
            distance=distance,
            attack_sector=request.attack_sector,
        )

        monte_carlo: MonteCarloCombatStats | None = None
        if request.trials:
            mc_result = run_monte_carlo_combat_stats(
                deterministic,
                attacker_pilot=_to_pilot_stats(request.attacker_pilot),
                defender_pilot=_to_pilot_stats(request.defender_pilot),
                trials=request.trials,
            )
            monte_carlo = MonteCarloCombatStats(
                trials=mc_result.trials,
                actual_hit_rate=mc_result.actual_hit_rate,
                actual_crit_rate=mc_result.actual_crit_rate,
                avg_damage=mc_result.avg_damage,
                min_damage=mc_result.min_damage,
                max_damage=mc_result.max_damage,
                perfect_evade_rate=mc_result.perfect_evade_rate,
            )

        return CombatSimulationResponse(
            hit_chance=deterministic.hit_chance,
            crit_chance=deterministic.crit_chance,
            base_damage=deterministic.base_damage,
            crit_damage=deterministic.crit_damage,
            resistance_applied_damage=deterministic.resistance_applied_damage,
            monte_carlo=monte_carlo,
        )

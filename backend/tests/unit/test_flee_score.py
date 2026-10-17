"""逃走度の計算のテスト.

検証項目:
    1. 武器が使えないときに最大になる（弾切れ・EN 不足・EN の回復待ち）
    2. 戦力差が大きいほど高くなる
    3. 索敵できていない敵と、射程に収めない敵を数えない
    4. 戦略モードで重みが変わる
    5. ヒステリシス
    6. AI_DECISION ログに出る。行動は変えない
"""

from __future__ import annotations

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.engine.constants import (
    FLEE_EN_WAIT_SEC,
    FLEE_ENTER_THRESHOLD,
    FLEE_EXIT_THRESHOLD,
    FLEE_POWER_RATIO_HIGH,
    FLEE_POWER_WEIGHTS,
)
from app.engine.flee import (
    assess_flee,
    attack_wait_sec,
    expected_dps,
    means_score,
    next_flee_state,
    power_score,
)
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon

_CENTER = 1000.0


def _rifle(**kwargs) -> Weapon:
    spec = dict(
        id="rifle",
        name="Rifle",
        power=100,
        range=600,
        accuracy=80,
        optimal_range=400.0,
        cooldown_sec=1.0,
        max_ammo=10,
        en_cost=0,
    )
    spec.update(kwargs)
    return Weapon(**spec)


def _unit(
    name: str, side: str, x: float, weapons: list[Weapon], hp: int = 1000, **kwargs
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=hp,
        current_hp=hp,
        armor=0,
        mobility=1.0,
        position=Vector3(x=x, y=0, z=_CENTER),
        weapons=weapons,
        side=side,
        team_id=f"{side}_TEAM",
        max_en=1000,
        en_recovery=0,
        sensor_range=2000,
        **kwargs,
    )


def _sim(
    player_weapons: list[Weapon] | None = None,
    enemy_weapons: list[Weapon] | None = None,
    enemy_hp: int = 1000,
    distance: float = 400.0,
    detected: bool = True,
    **player_kwargs,
) -> tuple[BattleSimulator, MobileSuit, MobileSuit]:
    player = _unit(
        "Player",
        "PLAYER",
        _CENTER,
        player_weapons if player_weapons is not None else [_rifle(id="p")],
        **player_kwargs,
    )
    enemy = _unit(
        "Enemy",
        "ENEMY",
        _CENTER + distance,
        enemy_weapons if enemy_weapons is not None else [_rifle(id="e")],
        hp=enemy_hp,
    )
    sim = BattleSimulator(player, [enemy])
    sim.team_detected_units[player.team_id] = {enemy.id} if detected else set()
    sim.team_detected_units[enemy.team_id] = {player.id}
    return sim, player, enemy


def _assess(sim: BattleSimulator, unit: MobileSuit, enemies: list[MobileSuit]):
    return sim._compute_flee_score(unit, enemies)


class TestPureFunctions:
    """純粋関数の単体テスト."""

    def test_expected_dps_uses_hit_chance_and_cooldown(self) -> None:
        """期待 DPS は威力×命中率÷再使用待ち時間になる."""
        assert expected_dps(_rifle(power=100, cooldown_sec=2.0), 50.0) == pytest.approx(
            25.0
        )

    def test_expected_dps_handles_zero_cooldown(self) -> None:
        """再使用待ちが 0 でも有限の値になる."""
        assert math.isfinite(expected_dps(_rifle(cooldown_sec=0.0), 100.0))

    def test_empty_ammo_is_unusable(self) -> None:
        """弾切れの武器は使えない."""
        assert attack_wait_sec(_rifle(max_ammo=5), 0, 1000.0, 0.0) is None

    def test_unlimited_ammo_is_usable(self) -> None:
        """弾数が無制限の武器は使える."""
        assert attack_wait_sec(_rifle(max_ammo=None), None, 1000.0, 0.0) == 0.0

    def test_en_shortage_without_recovery_is_unusable(self) -> None:
        """EN が足りず回復もしなければ使えない."""
        weapon = _rifle(en_cost=100, max_ammo=None)
        assert attack_wait_sec(weapon, None, 10.0, 0.0) is None

    def test_en_shortage_waits_for_recovery(self) -> None:
        """EN の回復を待てば撃てる武器は、待ち時間を返す."""
        weapon = _rifle(en_cost=100, max_ammo=None)
        assert attack_wait_sec(weapon, None, 50.0, 25.0) == pytest.approx(2.0)

    def test_en_wait_beyond_limit_is_unusable(self) -> None:
        """待ち時間が上限を超える武器は使えない."""
        weapon = _rifle(en_cost=1000, max_ammo=None)
        assert attack_wait_sec(weapon, None, 0.0, 1000 / (FLEE_EN_WAIT_SEC + 1)) is None

    def test_melee_is_always_usable(self) -> None:
        """格闘武器は常に使える."""
        saber = _rifle(is_melee=True, weapon_type="MELEE", en_cost=500, max_ammo=1)
        assert attack_wait_sec(saber, 0, 0.0, 0.0) == 0.0

    def test_means_score(self) -> None:
        """攻撃手段が無いと 1、待てば撃てると待ち時間に応じた値になる."""
        assert means_score([None, None]) == 1.0
        assert means_score([]) == 1.0
        assert means_score([None, 0.0]) == 0.0
        assert means_score([FLEE_EN_WAIT_SEC / 2]) == pytest.approx(0.5)

    def test_power_score_is_monotonic_and_bounded(self) -> None:
        """戦力比が大きいほど高く、0〜1 に収まる."""
        ratios = [None, 0.5, 1.0, 1.5, 2.0, 3.0, FLEE_POWER_RATIO_HIGH, math.inf]
        scores = [power_score(r) for r in ratios]
        assert scores == sorted(scores)
        assert scores[0] == 0.0
        assert scores[-1] == 1.0
        assert all(0.0 <= s <= 1.0 for s in scores)

    def test_hysteresis(self) -> None:
        """入るしきい値と抜けるしきい値の間では状態を保つ."""
        between = (FLEE_ENTER_THRESHOLD + FLEE_EXIT_THRESHOLD) / 2
        assert next_flee_state(False, between) is False
        assert next_flee_state(True, between) is True
        assert next_flee_state(False, FLEE_ENTER_THRESHOLD) is True
        assert next_flee_state(True, FLEE_EXIT_THRESHOLD - 0.01) is False


class TestAssessFlee:
    """`assess_flee()` の単体テスト."""

    def _assess(self, mode: str, my_dps: float, enemy_dps: float):
        return assess_flee(
            strategy_mode=mode,
            my_hp=1000,
            waits=[0.0],
            my_dps_by_enemy=[(1000, my_dps)],
            enemy_dps=[enemy_dps],
        )

    def test_no_threat_gives_zero(self) -> None:
        """脅威の敵がいなければ 0 になる."""
        result = assess_flee(
            strategy_mode="AGGRESSIVE",
            my_hp=1000,
            waits=[0.0],
            my_dps_by_enemy=[],
            enemy_dps=[],
        )
        assert result.score == 0.0
        assert result.ratio is None

    def test_no_means_is_max_whatever_the_mode(self) -> None:
        """攻撃手段が無いと、戦略モードによらず最大になる."""
        for mode in FLEE_POWER_WEIGHTS:
            result = assess_flee(
                strategy_mode=mode,
                my_hp=1000,
                waits=[None],
                my_dps_by_enemy=[(1000, 0.0)],
                enemy_dps=[1.0],
            )
            assert result.score == 1.0

    def test_score_grows_with_power_gap(self) -> None:
        """戦力差が大きいほど高くなる."""
        scores = [self._assess("SNIPER", 10.0, e).score for e in (5, 10, 20, 30, 40)]
        assert scores == sorted(scores)
        assert scores[0] == 0.0
        assert scores[-1] == 1.0

    def test_more_enemies_raise_the_score(self) -> None:
        """敵が増えると高くなる."""
        one = assess_flee(
            strategy_mode="SNIPER",
            my_hp=1000,
            waits=[0.0],
            my_dps_by_enemy=[(1000, 10.0)],
            enemy_dps=[15.0],
        )
        two = assess_flee(
            strategy_mode="SNIPER",
            my_hp=1000,
            waits=[0.0],
            my_dps_by_enemy=[(1000, 10.0), (1000, 10.0)],
            enemy_dps=[15.0, 15.0],
        )
        assert two.score > one.score
        assert two.threat_count == 2

    def test_strategy_mode_changes_weight(self) -> None:
        """戦略モードで重みが変わる."""
        defensive = self._assess("DEFENSIVE", 10.0, 25.0).score
        aggressive = self._assess("AGGRESSIVE", 10.0, 25.0).score
        assault = self._assess("ASSAULT", 10.0, 25.0).score
        assert defensive > aggressive > assault

    def test_score_stays_in_unit_range(self) -> None:
        """どの戦略モードでも 0〜1 に収まる."""
        for mode in FLEE_POWER_WEIGHTS:
            assert 0.0 <= self._assess(mode, 1.0, 1000.0).score <= 1.0

    def test_unknown_mode_uses_weight_one(self) -> None:
        """重みの表に無いモードは 1.0 倍にする."""
        assert self._assess("UNKNOWN", 10.0, 25.0).score == pytest.approx(
            self._assess("SNIPER", 10.0, 25.0).score
        )

    def test_details_are_json_safe(self) -> None:
        """無限大の戦力比は JSON に出せる値にする."""
        result = assess_flee(
            strategy_mode="SNIPER",
            my_hp=1000,
            waits=[0.0],
            my_dps_by_enemy=[(1000, 0.0)],
            enemy_dps=[10.0],
        )
        assert result.ratio == math.inf
        assert result.to_details()["flee_ratio"] is None


class TestSimulatorFleeScore:
    """シミュレータの状態から逃走度を求めるテスト."""

    def test_empty_ammo_gives_max(self) -> None:
        """弾切れで使える武器が無いと最大になる."""
        sim, player, enemy = _sim(player_weapons=[_rifle(id="p", max_ammo=5)])
        sim.unit_resources[str(player.id)]["weapon_states"]["p"]["current_ammo"] = 0
        assert _assess(sim, player, [enemy]).score == 1.0

    def test_cooldown_alone_does_not_count_as_no_means(self) -> None:
        """再使用待ちだけなら攻撃手段はある."""
        sim, player, enemy = _sim()
        sim.unit_resources[str(player.id)]["weapon_states"]["p"][
            "cooldown_remaining_sec"
        ] = 5.0
        assert _assess(sim, player, [enemy]).means == 0.0

    def test_en_shortage_without_recovery_gives_max(self) -> None:
        """EN が足りず回復もしなければ最大になる."""
        sim, player, enemy = _sim(
            player_weapons=[_rifle(id="p", en_cost=100, max_ammo=None)]
        )
        sim.unit_resources[str(player.id)]["current_en"] = 10.0
        assert _assess(sim, player, [enemy]).score == 1.0

    def test_stronger_enemy_raises_score(self) -> None:
        """敵の武器が強いほど高くなる."""
        strong = _rifle(id="e", power=400)
        weak = _rifle(id="e", power=50)
        sim_weak, p1, e1 = _sim(enemy_weapons=[weak])
        sim_strong, p2, e2 = _sim(enemy_weapons=[strong])
        assert _assess(sim_strong, p2, [e2]).score > _assess(sim_weak, p1, [e1]).score

    def test_enemy_hp_lowers_score(self) -> None:
        """敵の残り HP が少ないほど低くなる."""
        strong = _rifle(id="e", power=1000)
        sim_full, p1, e1 = _sim(enemy_weapons=[strong], enemy_hp=1000)
        sim_low, p2, e2 = _sim(enemy_weapons=[strong], enemy_hp=500)
        assert _assess(sim_low, p2, [e2]).score < _assess(sim_full, p1, [e1]).score

    def test_enemy_out_of_reach_is_not_counted(self) -> None:
        """自機を射程に収めない敵は数えない."""
        sim, player, enemy = _sim(distance=5000.0)
        result = _assess(sim, player, [enemy])
        assert result.threat_count == 0
        assert result.score == 0.0

    def test_undetected_enemy_is_not_counted_in_decision_phase(self) -> None:
        """索敵できていない敵だけなら計算しない."""
        sim, player, _ = _sim(detected=False)
        sim._ai_decision_phase(player)
        assert "flee" not in sim.unit_resources[str(player.id)]

    def test_strategy_mode_changes_score(self) -> None:
        """戦略モードで逃走度が変わる."""
        enemy_weapon = [_rifle(id="e", power=1000)]
        scores = {}
        for mode in ("DEFENSIVE", "AGGRESSIVE", "ASSAULT"):
            sim, player, enemy = _sim(enemy_weapons=enemy_weapon, strategy_mode=mode)
            scores[mode] = _assess(sim, player, [enemy]).score
        assert scores["DEFENSIVE"] > scores["AGGRESSIVE"] > scores["ASSAULT"]

    def test_assessment_does_not_touch_rng_or_logs(self) -> None:
        """計算は乱数を引かず、ログも出さない."""
        import random

        sim, player, enemy = _sim()
        state = random.getstate()
        log_count = len(sim.logs)
        _assess(sim, player, [enemy])
        assert random.getstate() == state
        assert len(sim.logs) == log_count


class TestAiDecisionLog:
    """AI_DECISION フェーズでの記録のテスト."""

    def test_ai_decision_log_carries_flee_details(self) -> None:
        """AI_DECISION ログの details に逃走度が載る."""
        sim, player, _ = _sim()
        sim._ai_decision_phase(player)
        log = next(entry for entry in sim.logs if entry.action_type == "AI_DECISION")
        assert log.details is not None
        assert set(log.details) >= {"flee_score", "flee_means", "flee_power"}
        resources = sim.unit_resources[str(player.id)]
        assert resources["flee"].score == log.details["flee_score"] or (
            resources["flee"].score
            == pytest.approx(log.details["flee_score"], abs=1e-3)
        )

    def test_flee_score_does_not_change_action(self) -> None:
        """逃走度の有無で、決定する行動が変わらない."""
        actions = []
        for no_means in (False, True):
            sim, player, _ = _sim(player_weapons=[_rifle(id="p", max_ammo=5)])
            if no_means:
                states = sim.unit_resources[str(player.id)]["weapon_states"]
                states["p"]["current_ammo"] = 0
            sim._ai_decision_phase(player)
            actions.append(sim.unit_resources[str(player.id)]["current_action"])
        sim, player, _ = _sim(player_weapons=[_rifle(id="p", max_ammo=5)])
        sim._compute_flee_score = lambda *_: assess_flee(  # type: ignore[method-assign]
            strategy_mode="AGGRESSIVE",
            my_hp=1,
            waits=[None],
            my_dps_by_enemy=[(1, 0.0)],
            enemy_dps=[1.0],
        )
        sim._ai_decision_phase(player)
        assert sim.unit_resources[str(player.id)]["current_action"] == actions[0]

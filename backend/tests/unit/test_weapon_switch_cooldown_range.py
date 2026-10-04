"""再使用待ちでの持ち替え抑制と、最適距離比を使った武器選択のテスト.

検証項目:
    1. 再使用待ちの残りが持ち替え時間以下なら、持ち替えずに待つ（AGGRESSIVE を含む）
    2. 再使用待ちの残りが持ち替え時間より長ければ、従来どおり持ち替える
    3. 弾切れ・EN 不足のときは、再使用待ちが短くても持ち替える
    4. 武器選択のファジィ推論が、距離 ÷ 最適距離の比でスコアを変える
    5. 50m 未満では、サーベルとライフルを持つ機体がライフルに持ち替えない
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.engine.calculator import PilotStats, calculate_weapon_switch_lock_sec
from app.engine.constants import WEAPON_SWITCH_LOCK_BASE_SEC
from app.engine.simulation import BattleSimulator
from app.engine.targeting import TargetingMixin
from app.models.models import MobileSuit, Vector3, Weapon

_STRATEGIES = ("AGGRESSIVE", "DEFENSIVE", "SNIPER", "ASSAULT", "RETREAT")


def _beam_saber() -> Weapon:
    return Weapon(
        id="saber",
        name="Beam Saber",
        power=200,
        range=150,
        accuracy=85,
        type="BEAM",
        optimal_range=100.0,
        decay_rate=0.15,
        en_cost=50,
        is_melee=True,
        weapon_type="MELEE",
    )


def _beam_rifle(max_ammo: int | None = None, en_cost: int = 0) -> Weapon:
    return Weapon(
        id="rifle",
        name="Beam Rifle",
        power=300,
        range=600,
        accuracy=80,
        type="BEAM",
        optimal_range=400.0,
        decay_rate=0.05,
        max_ammo=max_ammo,
        en_cost=en_cost,
    )


def _make_player(
    weapons: list[Weapon],
    policy: str = "BALANCED",
    strategy_mode: str | None = None,
) -> MobileSuit:
    return MobileSuit(
        name="Player MS",
        max_hp=500,
        current_hp=500,
        armor=0,
        mobility=1.0,
        position=Vector3(x=0, y=0, z=0),
        weapons=weapons,
        side="PLAYER",
        team_id="PLAYER_TEAM",
        max_en=1000,
        en_recovery=100,
        max_propellant=1000,
        sensor_range=1000,
        tactics={"priority": "CLOSEST", "weapon_switch_policy": policy},
        strategy_mode=strategy_mode,
    )


def _make_enemy(distance: float) -> MobileSuit:
    return MobileSuit(
        name="Enemy MS",
        max_hp=500,
        current_hp=500,
        armor=0,
        mobility=0.5,
        position=Vector3(x=distance, y=0, z=0),
        weapons=[_beam_rifle()],
        side="ENEMY",
        team_id="ENEMY_TEAM",
        max_en=1000,
        en_recovery=100,
        max_propellant=1000,
        sensor_range=1000,
    )


def _setup(
    weapons: list[Weapon],
    distance: float = 10.0,
    policy: str = "BALANCED",
    strategy_mode: str | None = None,
    pilot_stats: PilotStats | None = None,
) -> tuple[BattleSimulator, MobileSuit, MobileSuit, dict]:
    player = _make_player(weapons, policy=policy, strategy_mode=strategy_mode)
    enemy = _make_enemy(distance)
    sim = BattleSimulator(player, [enemy], player_pilot_stats=pilot_stats)
    resources = sim.unit_resources[str(player.id)]
    return sim, player, enemy, resources


def _set_weapon_state(
    resources: dict,
    weapon_id: str,
    cooldown_sec: float = 0.0,
    current_ammo: int | None = None,
) -> None:
    resources["weapon_states"][weapon_id] = {
        "current_ammo": current_ammo,
        "cooldown_remaining_sec": cooldown_sec,
    }


# ---------------------------------------------------------------------------
# 1/2. 再使用待ちと持ち替え時間の比較
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("policy", ["RACK_ONLY", "BALANCED", "AGGRESSIVE"])
def test_waits_when_cooldown_ends_within_switch_lock(policy: str) -> None:
    """再使用待ちの残りが持ち替え時間以下なら、持ち替えずに待つこと."""
    sim, player, enemy, resources = _setup(
        [_beam_saber(), _beam_rifle()], policy=policy
    )
    resources["active_weapon_id"] = "saber"
    _set_weapon_state(resources, "saber", cooldown_sec=1.0)

    selected = sim._select_weapon_with_switch_policy(player, enemy)

    assert selected is None, "再使用待ちの間は攻撃しない"
    assert resources["active_weapon_id"] == "saber"
    assert resources["weapon_switch_lock_remaining_sec"] == 0.0
    assert not any(log.action_type == "WEAPON_SWITCH_START" for log in sim.logs)


def test_waits_when_cooldown_equals_switch_lock() -> None:
    """残り時間が持ち替え時間と等しいときも待つこと."""
    sim, player, enemy, resources = _setup([_beam_saber(), _beam_rifle()])
    resources["active_weapon_id"] = "saber"
    _set_weapon_state(resources, "saber", cooldown_sec=WEAPON_SWITCH_LOCK_BASE_SEC)

    sim._select_weapon_with_switch_policy(player, enemy)

    assert resources["active_weapon_id"] == "saber"
    assert resources["weapon_switch_lock_remaining_sec"] == 0.0


def test_switches_when_cooldown_exceeds_switch_lock() -> None:
    """再使用待ちの残りが持ち替え時間より長ければ持ち替えること."""
    sim, player, enemy, resources = _setup([_beam_saber(), _beam_rifle()])
    resources["active_weapon_id"] = "saber"
    _set_weapon_state(
        resources, "saber", cooldown_sec=WEAPON_SWITCH_LOCK_BASE_SEC + 0.1
    )

    selected = sim._select_weapon_with_switch_policy(player, enemy)

    assert selected is None, "持ち替え開始ステップは攻撃不可"
    assert resources["active_weapon_id"] == "rifle"
    assert resources["weapon_switch_lock_remaining_sec"] > 0.0


def test_ref_shortened_lock_is_used_for_cooldown_comparison() -> None:
    """REF で短くなった持ち替え時間と比べること."""
    pilot_stats = PilotStats(ref=30)
    lock_sec = calculate_weapon_switch_lock_sec(WEAPON_SWITCH_LOCK_BASE_SEC, 30)
    sim, player, enemy, resources = _setup(
        [_beam_saber(), _beam_rifle()], pilot_stats=pilot_stats
    )
    resources["active_weapon_id"] = "saber"
    # 基礎値（1.5s）以下だが、REF で短縮された持ち替え時間より長い。
    _set_weapon_state(resources, "saber", cooldown_sec=lock_sec + 0.1)
    assert lock_sec + 0.1 < WEAPON_SWITCH_LOCK_BASE_SEC

    sim._select_weapon_with_switch_policy(player, enemy)

    assert resources["active_weapon_id"] == "rifle"


def test_resumes_active_weapon_after_cooldown() -> None:
    """再使用待ちが明けたら、同じ武器でそのまま攻撃できること."""
    sim, player, enemy, resources = _setup([_beam_saber(), _beam_rifle()])
    resources["active_weapon_id"] = "saber"
    _set_weapon_state(resources, "saber", cooldown_sec=1.0)
    sim._select_weapon_with_switch_policy(player, enemy)

    resources["weapon_states"]["saber"]["cooldown_remaining_sec"] = 0.0
    selected = sim._select_weapon_with_switch_policy(player, enemy)

    assert selected is not None and selected.id == "saber"
    assert resources["weapon_switch_lock_remaining_sec"] == 0.0


# ---------------------------------------------------------------------------
# 3. 弾切れ・EN 不足は従来どおり持ち替える
# ---------------------------------------------------------------------------


def test_switches_when_out_of_ammo_even_if_cooldown_is_short() -> None:
    """弾切れなら、再使用待ちが短くても持ち替えること."""
    sim, player, enemy, resources = _setup(
        [_beam_rifle(max_ammo=5), _beam_saber()], distance=300.0
    )
    resources["active_weapon_id"] = "rifle"
    _set_weapon_state(resources, "rifle", cooldown_sec=0.5, current_ammo=0)

    selected = sim._select_weapon_with_switch_policy(player, enemy)

    assert selected is None
    assert resources["active_weapon_id"] == "saber"
    assert resources["weapon_switch_lock_remaining_sec"] > 0.0


def test_switches_when_en_is_short_even_if_cooldown_is_short() -> None:
    """EN 不足なら、再使用待ちが短くても持ち替えること."""
    sim, player, enemy, resources = _setup(
        [_beam_rifle(en_cost=200), _beam_saber()], distance=300.0
    )
    resources["active_weapon_id"] = "rifle"
    resources["current_en"] = 100.0
    _set_weapon_state(resources, "rifle", cooldown_sec=0.5)

    sim._select_weapon_with_switch_policy(player, enemy)

    assert resources["active_weapon_id"] == "saber"
    assert resources["weapon_switch_lock_remaining_sec"] > 0.0


def test_cooldown_only_remaining_sec_reports_reason() -> None:
    """再使用待ちだけが理由のときだけ残り時間を返すこと."""
    rifle = _beam_rifle(max_ammo=5)
    sim, player, _enemy, resources = _setup([rifle])

    _set_weapon_state(resources, "rifle", cooldown_sec=0.7, current_ammo=3)
    assert sim._cooldown_only_remaining_sec(player, rifle) == pytest.approx(0.7)

    _set_weapon_state(resources, "rifle", cooldown_sec=0.7, current_ammo=0)
    assert sim._cooldown_only_remaining_sec(player, rifle) is None

    _set_weapon_state(resources, "rifle", cooldown_sec=0.0, current_ammo=3)
    assert sim._cooldown_only_remaining_sec(player, rifle) is None


# ---------------------------------------------------------------------------
# 4/5. 最適距離比による武器スコア
# ---------------------------------------------------------------------------


def test_optimal_range_ratio() -> None:
    """距離 ÷ 最適距離を返し、上限でクランプすること."""
    rifle = _beam_rifle()
    assert TargetingMixin._optimal_range_ratio(200.0, rifle) == pytest.approx(0.5)
    assert TargetingMixin._optimal_range_ratio(5000.0, rifle) == pytest.approx(3.0)


def _scores(
    distance: float, strategy_mode: str, weapons: list[Weapon] | None = None
) -> dict[str, float]:
    sim, player, enemy, _ = _setup(
        weapons or [_beam_saber(), _beam_rifle()],
        distance=distance,
        strategy_mode=strategy_mode,
    )
    sim._select_weapon_fuzzy(player, enemy)
    return sim._weapon_score_cache[str(player.id)]


@pytest.mark.parametrize("strategy_mode", _STRATEGIES)
@pytest.mark.parametrize("distance", [0.1, 10.0, 40.0])
def test_melee_weapon_scores_higher_than_rifle_at_close_range(
    strategy_mode: str, distance: float
) -> None:
    """50m 未満では、全戦略でサーベルがライフルより高いスコアになること."""
    scores = _scores(distance, strategy_mode)
    assert scores["saber"] > scores["rifle"]


@pytest.mark.parametrize("strategy_mode", _STRATEGIES)
def test_rifle_scores_lower_at_close_range_than_at_optimal(
    strategy_mode: str,
) -> None:
    """ライフルは至近距離の方が最適距離よりスコアが低いこと."""
    close = _scores(10.0, strategy_mode, [_beam_rifle()])["rifle"]
    optimal = _scores(400.0, strategy_mode, [_beam_rifle()])["rifle"]
    assert close < optimal


@pytest.mark.parametrize("strategy_mode", _STRATEGIES)
def test_out_of_range_weapon_scores_lower(strategy_mode: str) -> None:
    """射程外（サーベル 250m）では、射程内（50m）よりスコアが低いこと."""
    in_range = _scores(50.0, strategy_mode, [_beam_saber()])["saber"]
    out_of_range = _scores(250.0, strategy_mode, [_beam_saber()])["saber"]
    assert out_of_range < in_range


def test_does_not_switch_to_rifle_within_melee_range() -> None:
    """50m 未満でサーベルを持つ機体が、ライフルへ持ち替えないこと."""
    sim, player, enemy, resources = _setup(
        [_beam_saber(), _beam_rifle()], distance=10.0
    )

    first = sim._select_weapon_with_switch_policy(player, enemy)
    assert first is not None and first.id == "saber"

    # 斬った直後の再使用待ちでも、ライフルへ持ち替えない。
    _set_weapon_state(resources, "saber", cooldown_sec=1.0)
    sim._select_weapon_with_switch_policy(player, enemy)
    assert resources["active_weapon_id"] == "saber"
    assert resources["weapon_switch_lock_remaining_sec"] == 0.0


def test_switches_from_rifle_to_saber_within_melee_range() -> None:
    """50m 未満でライフルを持っていれば、サーベルへ持ち替えること."""
    sim, player, enemy, resources = _setup(
        [_beam_saber(), _beam_rifle()], distance=10.0
    )
    resources["active_weapon_id"] = "rifle"

    sim._select_weapon_with_switch_policy(player, enemy)

    assert resources["active_weapon_id"] == "saber"

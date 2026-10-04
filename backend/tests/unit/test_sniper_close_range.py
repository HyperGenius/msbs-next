"""SNIPER の近距離行動と、射撃機同士の膠着が起きないことを検証する."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "simulation")
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import engagement_bench as eb  # noqa: E402

from app.engine.fuzzy_engine import FuzzyEngine  # noqa: E402

_SNIPER_RULES = (
    Path(__file__).parent.parent.parent / "data" / "fuzzy_rules" / "sniper.json"
)


def _select_action(engine: FuzzyEngine, **inputs: float) -> str:
    """`_ai_decision_phase()` と同じく活性化度が最大の行動を返す."""
    base = {
        "enemy_count_near": 1.0,
        "ally_count_near": 0.0,
        "distance_to_nearest_enemy": 5.0,
        "hp_ratio": 1.0,
        "angle_to_target": 0.0,
    }
    _, debug = engine.infer_with_debug({**base, **inputs})
    activations: dict[str, float] = debug["activations"]["action"]
    return max(activations, key=lambda k: activations[k])


@pytest.fixture()
def sniper_engine() -> FuzzyEngine:
    """sniper.json の行動選択エンジン."""
    return FuzzyEngine.from_json(_SNIPER_RULES)


@pytest.mark.parametrize("hp_ratio", [1.0, 0.5])
def test_sniper_attacks_frontal_enemy_at_close_range(
    sniper_engine: FuzzyEngine, hp_ratio: float
) -> None:
    """近距離でも正面の敵には ATTACK を選ぶこと."""
    assert _select_action(sniper_engine, hp_ratio=hp_ratio) == "ATTACK"


def test_sniper_moves_when_close_enemy_is_on_flank(
    sniper_engine: FuzzyEngine,
) -> None:
    """近距離の敵が側面にいるときは MOVE を選ぶこと."""
    assert _select_action(sniper_engine, angle_to_target=60.0) == "MOVE"


def test_sniper_retreats_at_low_hp_even_if_enemy_is_frontal(
    sniper_engine: FuzzyEngine,
) -> None:
    """体力 LOW なら正面の近距離の敵がいても RETREAT を選ぶこと."""
    assert _select_action(sniper_engine, hp_ratio=0.1) == "RETREAT"


@pytest.mark.parametrize("scenario_key", ["ranged_gelgoog_gundam", "melee_vs_ranged"])
def test_sniper_duel_does_not_time_out(scenario_key: str) -> None:
    """SNIPER 同士の 1 対 1 が時間切れにならず決着すること."""
    condition = eb.Condition("SNIPER", "BALANCED", "BALANCED")

    metrics = eb.run_battle(scenario_key, condition, seed=595, max_steps=5000)

    assert not metrics.timed_out

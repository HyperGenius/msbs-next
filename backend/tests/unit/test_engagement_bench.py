"""Tests for engagement_bench (交戦距離・膠着の計測ツール)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "simulation")
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import engagement_bench as eb  # noqa: E402

from app.engine.simulation import BattleSimulator  # noqa: E402

_STEPS = 400


def _record(unit: str, time: float, *, melee: bool, hit: bool) -> eb.AttackRecord:
    return eb.AttackRecord(
        unit=unit,
        time=time,
        distance=10.0,
        optimal_range=100.0,
        is_melee=melee,
        sector="FRONT",
        is_hit=hit,
    )


def test_longest_melee_miss_is_broken_by_own_hit_only() -> None:
    """格闘ミスの連続は自機の命中で途切れ、射撃ミスや敵の命中では途切れない."""
    records = [
        _record("a", 1.0, melee=True, hit=False),
        _record("a", 2.0, melee=False, hit=False),
        _record("b", 2.5, melee=True, hit=True),
        _record("a", 4.0, melee=True, hit=False),
        _record("a", 5.0, melee=True, hit=True),
        _record("a", 6.0, melee=True, hit=False),
    ]
    assert eb._longest_melee_miss(records) == (3.0, 2)


def test_longest_melee_miss_without_melee_misses() -> None:
    """格闘ミスが無ければ 0 を返す."""
    records = [_record("a", 1.0, melee=False, hit=False)]
    assert eb._longest_melee_miss(records) == (0.0, 0)


def test_run_battle_is_reproducible_with_same_seed() -> None:
    """同じシードなら同じ計測値になる."""
    cond = eb.Condition("AGGRESSIVE", "BALANCED", "BALANCED")
    first = eb.run_battle("melee_duel", cond, seed=10, max_steps=_STEPS)
    second = eb.run_battle("melee_duel", cond, seed=10, max_steps=_STEPS)
    assert first == second
    assert sum(first.sector_counts.values()) > 0


def _logs_of(seed: int, *, hooked: bool) -> list[tuple]:
    scenario = eb.SCENARIOS["melee_duel"]
    eb._seed_all(seed)
    a = eb._build_unit(
        scenario.a,
        eb._UNIT_A_ID,
        "PLAYER",
        eb.Vector3(x=850.0, y=0, z=1000.0),
        "AGGRESSIVE",
        "BALANCED",
    )
    b = eb._build_unit(
        scenario.b,
        eb._UNIT_B_ID,
        "ENEMY",
        eb.Vector3(x=1150.0, y=0, z=1000.0),
        "AGGRESSIVE",
        "BALANCED",
    )
    sim = BattleSimulator(a, [b])
    if hooked:
        eb._record_attacks(sim, [])
    for _ in range(_STEPS):
        if sim.is_finished:
            break
        sim.step()
    return [(log.timestamp, log.action_type, log.damage) for log in sim.logs]


def test_attack_hook_does_not_change_battle() -> None:
    """計測用のフックを付けても戦闘ログは変わらない."""
    assert _logs_of(3, hooked=True) == _logs_of(3, hooked=False)


def test_summarize_rates() -> None:
    """距離の割合・勝率・時間切れ率を集計する."""
    battles = [
        eb.BattleMetrics(
            seed=1,
            duration=60.0,
            timed_out=False,
            winner="A",
            engaged_distances=[10.0, 100.0, 200.0, 300.0],
            melee_ratios=[0.1],
            ranged_ratios=[],
            sector_counts={"FRONT": 3, "FRONT_SIDE": 1, "REAR_SIDE": 0, "REAR": 0},
            weapon_switches=4,
            longest_melee_miss_sec=5.0,
            longest_melee_miss_count=3,
            melee_clashes=1,
            disengages=6,
        ),
        eb.BattleMetrics(
            seed=2,
            duration=60.0,
            timed_out=True,
            winner="",
            engaged_distances=[],
            melee_ratios=[],
            ranged_ratios=[],
            sector_counts={"FRONT": 0, "FRONT_SIDE": 0, "REAR_SIDE": 0, "REAR": 0},
            weapon_switches=0,
            longest_melee_miss_sec=0.0,
            longest_melee_miss_count=0,
            melee_clashes=0,
        ),
    ]
    summary = eb.summarize(battles)
    assert summary["under_melee_range_rate"] == 0.25
    assert summary["under_close_range_rate"] == 0.5
    assert summary["sector_rates"]["FRONT"] == 0.75
    assert summary["timeout_rate"] == 0.5
    assert summary["a_win_rate"] == 0.5
    # 4 回 / 2 分 / 2 機。
    assert summary["weapon_switches_per_min"] == 1.0
    # 鍔迫り合い 1 回 / 2 分。格闘 1 回と、鍔迫り合いの格闘 2 回のうち 2 回。
    assert summary["melee_clashes_per_min"] == 0.5
    assert abs(summary["melee_clash_rate"] - 2 / 3) < 1e-9
    # 6 回 / 2 分 / 2 機。
    assert summary["disengages_per_min"] == 1.5
    assert summary["longest_melee_miss_seed"] == 1
    assert summary["ranged_optimal_ratio"]["p50"] is None


def test_diff_cell_formats_rate_delta_in_points() -> None:
    """割合の差はパーセントポイントで表示する."""
    assert eb._diff_cell(0.5, 0.75, ".0%") == "50% → 75% (+25pt)"
    assert eb._diff_cell(None, 1.0, ".1f") == "- → 1.0"


def test_parse_pilot_sets_only_given_stats() -> None:
    """書いた能力だけを設定し、書かない能力は 0 にする."""
    pilot = eb.parse_pilot("mel=20, ref=5")
    assert (pilot.mel, pilot.ref, pilot.intel, pilot.sht) == (20, 5, 0, 0)
    assert eb.parse_pilot("") == eb.PilotStats()


@pytest.mark.parametrize("value", ["dex=1", "mel", "mel=x"])
def test_parse_pilot_rejects_invalid_items(value: str) -> None:
    """未知の能力名・値の無い項目・数でない値は拒否する."""
    with pytest.raises(ValueError):
        eb.parse_pilot(value)

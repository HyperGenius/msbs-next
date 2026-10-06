"""戦術設定（tactics.range）とパイロット能力の交戦挙動への反映のテスト.

検証項目:
    1. 補正値の計算（粘り・劣勢の見積もり・仕切り直しの時間と旋回）
    2. 膠着度・優勢度への反映
    3. 目標交戦距離と間合いの基準武器
    4. 武器選択と格闘突入の制約
    5. 仕切り直しの後の射撃優先の長さと、REF による仕切り直しの短縮
    6. 装備と矛盾する設定と、NPC の戦術設定
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.core.npc_data import build_npc_tactics
from app.engine.calculator import PilotStats
from app.engine.constants import (
    DISENGAGE_MAX_SEC,
    DISENGAGE_RANGED_PREFERENCE_SEC,
    ENGAGEMENT_RANGE_TOLERANCE_RATIO,
    PILOT_INT_CAUTION_MAX,
    PILOT_MEL_PATIENCE_MAX,
    PILOT_REF_DISENGAGE_SEC_REDUCTION_MAX,
    PILOT_REF_DISENGAGE_TURN_MAX,
    STALEMATE_FULL_ATTACKS,
    STALEMATE_FULL_ELAPSED_SEC,
    TACTICS_MELEE_WEAPON_SCORE_BIAS,
    TACTICS_RANGED_PREFERENCE_MULTIPLIERS,
    TACTICS_STALEMATE_PATIENCE,
)
from app.engine.engagement import EngagementRecord, stalemate
from app.engine.engagement_style import (
    disengage_max_sec,
    disengage_turn_multiplier,
    perceived_dominance,
    stalemate_patience,
    tactics_range,
)
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon

_CENTER = 1000.0


def _beam_saber() -> Weapon:
    return Weapon(
        id="saber",
        name="Beam Saber",
        power=200,
        range=150,
        accuracy=85,
        type="BEAM",
        optimal_range=100.0,
        is_melee=True,
        weapon_type="MELEE",
    )


def _beam_rifle() -> Weapon:
    return Weapon(
        id="rifle",
        name="Beam Rifle",
        power=300,
        range=600,
        accuracy=80,
        type="BEAM",
        optimal_range=400.0,
    )


def _make_unit(
    name: str, side: str, weapons: list[Weapon], x: float, range_setting: str
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=0,
        mobility=1.0,
        position=Vector3(x=x, y=0, z=_CENTER),
        weapons=weapons,
        side=side,
        team_id=f"{side}_TEAM",
        max_en=1000,
        en_recovery=0,
        sensor_range=2000,
        tactics={"priority": "CLOSEST", "range": range_setting},
    )


def _setup(
    range_setting: str = "BALANCED",
    distance: float = 100.0,
    weapons: list[Weapon] | None = None,
    pilot: PilotStats | None = None,
) -> tuple[BattleSimulator, MobileSuit, MobileSuit]:
    player = _make_unit(
        "Player",
        "PLAYER",
        weapons if weapons is not None else [_beam_saber(), _beam_rifle()],
        _CENTER,
        range_setting,
    )
    enemy = _make_unit(
        "Enemy", "ENEMY", [_beam_saber(), _beam_rifle()], _CENTER + distance, "BALANCED"
    )
    sim = BattleSimulator(player, [enemy], player_pilot_stats=pilot)
    sim.team_detected_units[player.team_id] = {enemy.id}
    sim.team_detected_units[enemy.team_id] = {player.id}
    return sim, player, enemy


def _record(opponent_id: str, now: float, damage_taken: int = 0) -> EngagementRecord:
    """膠着の数えが基準値ちょうどになる交戦記録を返す."""
    return EngagementRecord(
        opponent_id=opponent_id,
        started_at=now - STALEMATE_FULL_ELAPSED_SEC,
        last_in_range_at=now,
        attacks=STALEMATE_FULL_ATTACKS,
        attacks_since_hit=STALEMATE_FULL_ATTACKS,
        damage_taken=damage_taken,
    )


def _engagement_inputs(
    range_setting: str = "BALANCED",
    pilot: PilotStats | None = None,
    damage_taken: int = 0,
) -> dict[str, float]:
    sim, player, enemy = _setup(range_setting, pilot=pilot)
    sim.elapsed_time = 20.0
    sim.unit_resources[str(player.id)]["engagement"] = _record(
        str(enemy.id), sim.elapsed_time, damage_taken
    )
    return sim._compute_engagement_inputs(player, enemy)


# ---------------------------------------------------------------------------
# 1. 補正値の計算
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tactics", "expected"),
    [
        ({"range": "MELEE"}, "MELEE"),
        ({"range": "FLEE"}, "FLEE"),
        ({"priority": "CLOSEST"}, "BALANCED"),
        ({"range": "UNKNOWN"}, "BALANCED"),
    ],
)
def test_tactics_range_defaults_to_balanced(tactics: dict, expected: str) -> None:
    """未設定と許容値外の range は BALANCED として扱うこと."""
    sim, player, _ = _setup()
    player.tactics = tactics
    assert tactics_range(player) == expected


def test_stalemate_patience_order_by_tactics() -> None:
    """MELEE は最も粘り、RANGED と FLEE は粘らないこと."""
    zero = PilotStats()
    melee = stalemate_patience("MELEE", zero)
    balanced = stalemate_patience("BALANCED", zero)
    assert melee == TACTICS_STALEMATE_PATIENCE["MELEE"]
    assert balanced == 1.0
    assert stalemate_patience("RANGED", zero) < balanced < melee
    assert stalemate_patience("FLEE", zero) < balanced


def test_mel_increases_patience_up_to_limit() -> None:
    """MEL が高いほど粘り、上限で止まること."""
    low = stalemate_patience("BALANCED", PilotStats(mel=0))
    high = stalemate_patience("BALANCED", PilotStats(mel=10))
    capped = stalemate_patience("BALANCED", PilotStats(mel=1000))
    assert low < high < capped
    assert capped == pytest.approx(1.0 + PILOT_MEL_PATIENCE_MAX)


def test_int_amplifies_only_disadvantage() -> None:
    """INT は劣勢だけを大きく見積もり、優勢と互角は変えないこと."""
    pilot = PilotStats(intel=1000)
    assert perceived_dominance(-0.2, pilot) == pytest.approx(
        -0.2 * (1.0 + PILOT_INT_CAUTION_MAX)
    )
    assert perceived_dominance(-0.9, pilot) == -1.0
    assert perceived_dominance(0.0, pilot) == 0.0
    assert perceived_dominance(0.3, pilot) == 0.3
    assert perceived_dominance(-0.2, PilotStats()) == -0.2


def test_ref_shortens_disengage_and_speeds_up_turn() -> None:
    """REF が高いほど仕切り直しを早く終え、速く向きを変えること."""
    assert disengage_max_sec(3.0, PilotStats()) == 3.0
    assert disengage_max_sec(3.0, PilotStats(ref=10)) < 3.0
    assert disengage_max_sec(3.0, PilotStats(ref=1000)) == pytest.approx(
        3.0 * (1.0 - PILOT_REF_DISENGAGE_SEC_REDUCTION_MAX)
    )
    assert disengage_turn_multiplier(PilotStats()) == 1.0
    assert disengage_turn_multiplier(PilotStats(ref=1000)) == pytest.approx(
        1.0 + PILOT_REF_DISENGAGE_TURN_MAX
    )


def test_stalemate_patience_delays_full_stalemate() -> None:
    """粘りの倍率だけ、膠着度が最大になるまでの攻撃回数と時間が延びること."""
    record = _record("enemy", 10.0)
    assert stalemate(record, 10.0, 1000, 1000) == 1.0
    assert stalemate(record, 10.0, 1000, 1000, patience=1.5) == pytest.approx(1 / 1.5)
    assert stalemate(record, 10.0, 1000, 1000, patience=0.5) == 1.0


# ---------------------------------------------------------------------------
# 2. 膠着度・優勢度への反映
# ---------------------------------------------------------------------------


def test_stalemate_input_depends_on_tactics_range() -> None:
    """同じ攻防でも MELEE は膠着度が低く、RANGED は高いこと."""
    melee = _engagement_inputs("MELEE")["stalemate"]
    balanced = _engagement_inputs("BALANCED")["stalemate"]
    ranged = _engagement_inputs("RANGED")["stalemate"]
    assert melee < balanced
    assert ranged == balanced == 1.0


def test_stalemate_input_depends_on_mel() -> None:
    """MEL が高いパイロットほど、同じ攻防での膠着度が低いこと."""
    low = _engagement_inputs(pilot=PilotStats(mel=0))["stalemate"]
    high = _engagement_inputs(pilot=PilotStats(mel=20))["stalemate"]
    assert high < low


def test_dominance_input_depends_on_int() -> None:
    """INT が高いパイロットほど、同じ被弾を劣勢と見積もること."""
    low = _engagement_inputs(pilot=PilotStats(intel=0), damage_taken=200)["dominance"]
    high = _engagement_inputs(pilot=PilotStats(intel=20), damage_taken=200)["dominance"]
    assert low == pytest.approx(-0.2)
    assert high < low


# ---------------------------------------------------------------------------
# 3. 目標交戦距離と間合いの基準武器
# ---------------------------------------------------------------------------


def test_flee_keeps_ranged_weapon_at_range_limit() -> None:
    """FLEE は射撃武器の射程ぎりぎりを目標にし、格闘武器は変えないこと."""
    rifle = _beam_rifle()
    saber = _beam_saber()
    sim_b, balanced, _ = _setup("BALANCED")
    sim_f, flee, _ = _setup("FLEE")

    assert sim_b._engagement_range(balanced, rifle).distance == pytest.approx(400.0)
    assert sim_f._engagement_range(flee, rifle).distance == pytest.approx(
        600.0 / (1.0 + ENGAGEMENT_RANGE_TOLERANCE_RATIO)
    )
    assert (
        sim_f._engagement_range(flee, saber).distance
        == sim_b._engagement_range(balanced, saber).distance
    )


def test_melee_uses_melee_weapon_as_reference_at_long_range() -> None:
    """MELEE は遠くでも格闘武器の間合いを基準にすること."""
    sim_b, balanced, enemy_b = _setup("BALANCED", distance=500.0)
    sim_m, melee, enemy_m = _setup("MELEE", distance=500.0)

    assert sim_b._get_reference_weapon(balanced, enemy_b).id == "rifle"
    assert sim_m._get_reference_weapon(melee, enemy_m).id == "saber"


@pytest.mark.parametrize("range_setting", ["RANGED", "FLEE"])
def test_ranged_settings_use_ranged_weapon_as_reference_at_close_range(
    range_setting: str,
) -> None:
    """RANGED と FLEE は近づかれても射撃武器の間合いを基準にすること."""
    sim, unit, enemy = _setup(range_setting, distance=30.0)
    assert sim._get_reference_weapon(unit, enemy).id == "rifle"


def test_ranged_moves_away_when_approached() -> None:
    """格闘の間合いの手前で、RANGED は離れ、BALANCED は詰めること."""

    def radial(range_setting: str) -> float:
        sim, unit, enemy = _setup(range_setting, distance=130.0)
        sim.unit_resources[str(unit.id)]["current_action"] = "ATTACK"
        direction = sim._calculate_potential_field(unit, enemy)
        to_enemy = enemy.position.to_numpy() - unit.position.to_numpy()
        return float(np.dot(direction, to_enemy / np.linalg.norm(to_enemy)))

    assert radial("RANGED") < 0.0
    assert radial("BALANCED") > 0.0


# ---------------------------------------------------------------------------
# 4. 武器選択と格闘突入の制約
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("range_setting", ["MELEE", "RANGED", "FLEE"])
def test_melee_weapon_score_is_biased_by_tactics(range_setting: str) -> None:
    """格闘武器のスコアにだけ、設定ごとの値が足されること."""
    sim_b, balanced, enemy_b = _setup("BALANCED", distance=80.0)
    sim_t, unit, enemy_t = _setup(range_setting, distance=80.0)
    sim_b._select_weapon_fuzzy(balanced, enemy_b)
    sim_t._select_weapon_fuzzy(unit, enemy_t)

    base = sim_b._weapon_score_cache[str(balanced.id)]
    biased = sim_t._weapon_score_cache[str(unit.id)]
    assert biased["saber"] - base["saber"] == pytest.approx(
        TACTICS_MELEE_WEAPON_SCORE_BIAS[range_setting]
    )
    assert biased["rifle"] == pytest.approx(base["rifle"])


@pytest.mark.parametrize("range_setting", ["RANGED", "FLEE"])
def test_ranged_settings_do_not_charge_into_melee(range_setting: str) -> None:
    """RANGED と FLEE は格闘突入を射撃に変えること."""
    sim, unit, enemy = _setup(range_setting)
    action = sim._decide_action(unit, {"ENGAGE_MELEE": 1.0}, "AGGRESSIVE", enemy, {})
    assert action == "ATTACK"


@pytest.mark.parametrize("range_setting", ["BALANCED", "MELEE"])
def test_other_settings_keep_melee_charge(range_setting: str) -> None:
    """BALANCED と MELEE は格闘突入をそのまま選ぶこと."""
    sim, unit, enemy = _setup(range_setting)
    action = sim._decide_action(unit, {"ENGAGE_MELEE": 1.0}, "AGGRESSIVE", enemy, {})
    assert action == "ENGAGE_MELEE"


# ---------------------------------------------------------------------------
# 5. 仕切り直しの後の射撃優先と、REF による短縮
# ---------------------------------------------------------------------------


def _disengage_and_finish(
    range_setting: str, pilot: PilotStats | None = None
) -> tuple[BattleSimulator, MobileSuit, MobileSuit]:
    sim, unit, enemy = _setup(range_setting, pilot=pilot)
    sim.unit_resources[str(unit.id)]["engagement"] = _record(
        str(enemy.id), sim.elapsed_time
    )
    action = sim._decide_action(
        unit,
        {"DISENGAGE": 1.0},
        "AGGRESSIVE",
        enemy,
        {"stalemate": 1.0, "dominance": 0.0},
    )
    assert action == "DISENGAGE"
    return sim, unit, enemy


@pytest.mark.parametrize("range_setting", ["MELEE", "RANGED", "FLEE", "BALANCED"])
def test_ranged_preference_after_disengage_depends_on_tactics(
    range_setting: str,
) -> None:
    """仕切り直しの後の射撃優先は、MELEE で短く、RANGED と FLEE で長いこと."""
    sim, unit, enemy = _disengage_and_finish(range_setting)
    sim.elapsed_time = DISENGAGE_MAX_SEC
    sim._decide_action(unit, {"ATTACK": 1.0}, "AGGRESSIVE", enemy, {})

    expected = (
        DISENGAGE_RANGED_PREFERENCE_SEC
        * TACTICS_RANGED_PREFERENCE_MULTIPLIERS.get(range_setting, 1.0)
    )
    resources = sim.unit_resources[str(unit.id)]
    assert resources["ranged_preference_until"] == pytest.approx(
        DISENGAGE_MAX_SEC + expected
    )


def test_high_ref_finishes_disengage_earlier() -> None:
    """REF が高いと、同じ時刻でも仕切り直しを終えていること."""
    now = DISENGAGE_MAX_SEC * (1.0 - PILOT_REF_DISENGAGE_SEC_REDUCTION_MAX / 2)
    results = {}
    for ref in (0, 1000):
        sim, unit, enemy = _disengage_and_finish("BALANCED", PilotStats(ref=ref))
        sim.elapsed_time = now
        results[ref] = sim._decide_action(
            unit, {"ATTACK": 1.0}, "AGGRESSIVE", enemy, {}
        )
    assert results == {0: "DISENGAGE", 1000: "ATTACK"}


def test_high_ref_turns_faster_during_disengage() -> None:
    """仕切り直し中は、REF が高いほど 1 ステップで大きく向きを変えること."""

    def rotation(ref: int, action: str) -> float:
        sim, unit, _ = _setup(pilot=PilotStats(ref=ref))
        resources = sim.unit_resources[str(unit.id)]
        resources["current_action"] = action
        resources["movement_heading_deg"] = 0.0
        sim._apply_inertia(unit, np.array([-1.0, 0.0, 0.0]), 0.1)
        return abs(resources["movement_heading_deg"])

    assert rotation(1000, "DISENGAGE") == pytest.approx(
        rotation(0, "DISENGAGE") * (1.0 + PILOT_REF_DISENGAGE_TURN_MAX)
    )
    assert rotation(1000, "ATTACK") == pytest.approx(rotation(0, "ATTACK"))
    assert not math.isclose(rotation(0, "DISENGAGE"), 180.0)


# ---------------------------------------------------------------------------
# 6. 装備と矛盾する設定と、NPC の戦術設定
# ---------------------------------------------------------------------------


def test_melee_setting_without_melee_weapon_uses_ranged_weapon() -> None:
    """格闘武器が無い MELEE は、射撃武器の間合いで戦うこと."""
    sim, unit, enemy = _setup("MELEE", distance=500.0, weapons=[_beam_rifle()])
    assert sim._get_reference_weapon(unit, enemy).id == "rifle"
    assert sim._engagement_range(unit, unit.weapons[0]).distance == pytest.approx(400.0)


@pytest.mark.parametrize("range_setting", ["RANGED", "FLEE"])
def test_ranged_setting_without_ranged_weapon_still_fights_in_melee(
    range_setting: str,
) -> None:
    """射撃武器が無い RANGED と FLEE は、格闘武器で突入すること."""
    sim, unit, enemy = _setup(range_setting, distance=30.0, weapons=[_beam_saber()])
    assert sim._get_reference_weapon(unit, enemy).id == "saber"
    action = sim._decide_action(unit, {"ENGAGE_MELEE": 1.0}, "AGGRESSIVE", enemy, {})
    assert action == "ENGAGE_MELEE"


@pytest.mark.parametrize("range_setting", ["MELEE", "RANGED", "BALANCED", "FLEE"])
@pytest.mark.parametrize(
    "weapons", [[_beam_saber()], [_beam_rifle()]], ids=["saber", "rifle"]
)
def test_battle_runs_with_any_setting_and_loadout(
    range_setting: str, weapons: list[Weapon]
) -> None:
    """どの設定と装備の組でも、戦闘がエラーなく進むこと."""
    sim, _, _ = _setup(range_setting, distance=400.0, weapons=weapons)
    for _ in range(200):
        if sim.is_finished:
            break
        sim.step()


def test_aggressive_npc_approaches_with_melee_weapon() -> None:
    """性格が AGGRESSIVE の NPC（range=MELEE）は、格闘武器の間合いを基準にすること."""
    sim, _, enemy = _setup(distance=500.0)
    enemy.tactics = build_npc_tactics("AGGRESSIVE")
    player = sim.player
    assert sim._get_reference_weapon(enemy, player).id == "saber"

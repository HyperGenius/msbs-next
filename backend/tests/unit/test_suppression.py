"""射撃の制圧（蓄積・減衰・減速・ログ）のテスト."""

import math
from dataclasses import replace
from unittest.mock import patch

import numpy as np
import pytest

from app.engine.calculator import PilotStats
from app.engine.constants import (
    SUPPRESSION_LOG_ENTER_VALUE,
    SUPPRESSION_LOG_EXIT_VALUE,
)
from app.engine.simulation import BattleSimulator
from app.engine.suppression import (
    SuppressionConfig,
    add_suppression,
    decay_suppression,
    is_falling_back,
    shot_suppression,
    suppression_speed_multiplier,
)
from app.models.models import MobileSuit, Vector3, Weapon
from app.services.mission_battle import build_mission_battle
from app.services.retreat_support_mission import build_retreat_support_mission
from app.services.theater_service import BattleConditions

_CONFIG = SuppressionConfig(
    per_cooldown_sec=20.0,
    hit_multiplier=2.0,
    max_value=100.0,
    decay_rate=0.3,
    max_speed_penalty=0.5,
    advance_only=True,
)
_MAX_SPEED = 80.0
_DT = 0.1


def _rifle(cooldown_sec: float = 1.0) -> Weapon:
    return Weapon(
        id="rifle",
        name="Rifle",
        power=1,
        range=1000,
        accuracy=80,
        cooldown_sec=cooldown_sec,
    )


def _saber() -> Weapon:
    return Weapon(
        id="saber",
        name="Saber",
        power=1,
        range=1000,
        accuracy=80,
        weapon_type="MELEE",
        is_melee=True,
        fire_arc_deg=360,
    )


def _unit(name: str, side: str, x: float, weapon: Weapon) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=100000,
        current_hp=100000,
        side=side,
        team_id=f"{side}_TEAM",
        position=Vector3(x=x, y=0, z=0),
        weapons=[weapon],
        sensor_range=5000,
        max_speed=_MAX_SPEED,
        acceleration=300.0,
        deceleration=50.0,
        max_turn_rate=360.0,
    )


def _setup(
    weapon: Weapon | None = None, suppression: SuppressionConfig | None = _CONFIG
) -> tuple[BattleSimulator, MobileSuit, MobileSuit]:
    """x=0 の射撃機（PLAYER）と、x=300 の標的（ENEMY）を作る."""
    shooter = _unit("Shooter", "PLAYER", 0.0, weapon or _rifle())
    target = _unit("Target", "ENEMY", 300.0, _rifle())
    sim = BattleSimulator(shooter, [target], suppression=suppression)
    sim.obstacles = []
    sim.unit_resources[str(shooter.id)]["body_heading_deg"] = 0.0
    # 命中のロールだけで結果を決めるため、LUK による完全回避をなくす。
    sim.unit_pilot_stats[str(target.id)] = PilotStats()
    return sim, shooter, target


def _shoot(sim: BattleSimulator, shooter: MobileSuit, target: MobileSuit, hit: bool):
    roll = 0.0 if hit else 1000.0
    with patch("app.engine.combat.random.uniform", return_value=roll):
        sim._process_attack(
            shooter, target, 300.0, shooter.position.to_numpy(), shooter.weapons[0]
        )
    # 次の射撃が再使用待ちで止まらないようにする。
    for state in sim.unit_resources[str(shooter.id)]["weapon_states"].values():
        state["cooldown_remaining_sec"] = 0.0


def _suppression(sim: BattleSimulator, unit: MobileSuit) -> float:
    return sim.unit_resources[str(unit.id)]["suppression"]


def _actions(sim: BattleSimulator, unit: MobileSuit) -> list[str]:
    return [log.action_type for log in sim.logs if log.actor_id == unit.id]


def _direction(heading_deg: float) -> np.ndarray:
    rad = np.radians(heading_deg)
    return np.array([np.cos(rad), 0.0, np.sin(rad)])


def _top_speed(sim: BattleSimulator, unit: MobileSuit, heading: float) -> float:
    """胴体と移動の向きを heading にそろえて動かし、上限付近の速さを返す."""
    resources = sim.unit_resources[str(unit.id)]
    resources["body_heading_deg"] = heading
    resources["movement_heading_deg"] = heading
    speeds = []
    for _ in range(30):
        sim._apply_inertia(unit, _direction(heading), _DT)
        speeds.append(float(np.linalg.norm(resources["velocity_vec"])))
    return max(speeds[-2:])


# ---------------------------------------------------------------------------
# 計算
# ---------------------------------------------------------------------------


def test_shot_suppression_scales_with_cooldown() -> None:
    """1 発の量は再使用待ちに比例し、命中は倍率を掛ける."""
    assert shot_suppression(_CONFIG, _rifle(1.0), is_hit=False) == pytest.approx(20.0)
    assert shot_suppression(_CONFIG, _rifle(0.5), is_hit=False) == pytest.approx(10.0)
    assert shot_suppression(_CONFIG, _rifle(1.0), is_hit=True) == pytest.approx(40.0)


def test_shot_suppression_floors_zero_cooldown() -> None:
    """再使用待ち 0 の武器でも 0 にはならない."""
    assert shot_suppression(_CONFIG, _rifle(0.0), is_hit=False) > 0.0


def test_add_suppression_caps_at_max() -> None:
    """上限で止める."""
    resources: dict = {}
    assert add_suppression(_CONFIG, resources, 80.0) == 80.0
    assert add_suppression(_CONFIG, resources, 80.0) == 100.0


def test_decay_is_exponential_and_reaches_zero() -> None:
    """毎秒一定の割合で減り、小さくなると 0 になる."""
    resources = {"suppression": 50.0}
    value = decay_suppression(_CONFIG, resources, 1.0)
    assert value == pytest.approx(50.0 * math.exp(-0.3))

    for _ in range(200):
        value = decay_suppression(_CONFIG, resources, 0.1)
    assert value == 0.0


def test_speed_multiplier_is_linear_up_to_max() -> None:
    """制圧値に比例して下がり、上限より上では変わらない."""
    assert suppression_speed_multiplier(_CONFIG, 0.0) == pytest.approx(1.0)
    assert suppression_speed_multiplier(_CONFIG, 50.0) == pytest.approx(0.75)
    assert suppression_speed_multiplier(_CONFIG, 100.0) == pytest.approx(0.5)
    assert suppression_speed_multiplier(_CONFIG, 150.0) == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("resources", "heading", "expected"),
    [
        ({"current_action": "ATTACK", "body_heading_deg": 0.0}, 0.0, False),
        ({"current_action": "MOVE", "body_heading_deg": 0.0}, 90.0, False),
        ({"current_action": "RETREAT", "body_heading_deg": 0.0}, 0.0, True),
        ({"current_action": "DISENGAGE", "body_heading_deg": 0.0}, 0.0, True),
        ({"current_action": "HIT_AND_AWAY", "body_heading_deg": 0.0}, 0.0, True),
        ({"current_action": "ATTACK", "fleeing": True}, 0.0, True),
        ({"current_action": "ATTACK", "body_heading_deg": 0.0}, 180.0, True),
    ],
)
def test_is_falling_back(resources: dict, heading: float, expected: bool) -> None:
    """撤退・仕切り直し・ヒットアンドアウェイ・逃走・後退を、後退・逃走とみなす."""
    assert is_falling_back(resources, heading) is expected


# ---------------------------------------------------------------------------
# 蓄積
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("hit", "expected"), [(False, 20.0), (True, 40.0)])
def test_ranged_shot_suppresses_target_hit_or_miss(hit: bool, expected: float) -> None:
    """射撃は命中・外れにかかわらず制圧値を加え、ログの details に載せる."""
    sim, shooter, target = _setup()

    _shoot(sim, shooter, target, hit)

    assert _suppression(sim, target) == pytest.approx(expected)
    log = next(log for log in sim.logs if log.action_type in ("ATTACK", "MISS"))
    assert log.action_type == ("ATTACK" if hit else "MISS")
    assert log.details == {"target_suppression": round(expected)}


def test_melee_attack_does_not_suppress() -> None:
    """格闘武器では制圧値をためない."""
    sim, shooter, target = _setup(_saber())

    _shoot(sim, shooter, target, hit=False)

    assert _suppression(sim, target) == 0.0
    assert "SUPPRESSED" not in _actions(sim, target)


def test_disabled_suppression_changes_nothing() -> None:
    """制圧を渡さないシミュレータ（バトルロイヤル）は、値もログも変えない."""
    sim, shooter, target = _setup(suppression=None)

    _shoot(sim, shooter, target, hit=True)
    sim._suppression_decay_phase(_DT)

    assert _suppression(sim, target) == 0.0
    assert all(not log.action_type.startswith("SUPPRESS") for log in sim.logs)
    assert all(
        log.details is None or "target_suppression" not in log.details
        for log in sim.logs
    )


def test_suppressed_log_follows_the_shot() -> None:
    """閾値を超えた射撃の後に SUPPRESSED を 1 回だけ出す."""
    sim, shooter, target = _setup()
    shots = math.ceil(SUPPRESSION_LOG_ENTER_VALUE / 20.0)

    for _ in range(shots + 2):
        _shoot(sim, shooter, target, hit=False)

    types = [log.action_type for log in sim.logs]
    assert types.count("SUPPRESSED") == 1
    first = types.index("SUPPRESSED")
    assert types[first - 1] == "MISS"
    suppressed = sim.logs[first]
    assert suppressed.actor_id == target.id
    assert suppressed.target_id == shooter.id
    assert suppressed.details is not None
    assert suppressed.details["suppression"] >= SUPPRESSION_LOG_ENTER_VALUE


def test_suppression_end_logged_after_decay() -> None:
    """減衰で終わりの閾値を下回ると SUPPRESSION_END を 1 回出す."""
    sim, shooter, target = _setup()
    for _ in range(3):
        _shoot(sim, shooter, target, hit=False)

    for _ in range(100):
        sim._suppression_decay_phase(_DT)

    assert _actions(sim, target).count("SUPPRESSION_END") == 1
    end = next(log for log in sim.logs if log.action_type == "SUPPRESSION_END")
    assert end.details is not None
    assert end.details["suppression"] <= SUPPRESSION_LOG_EXIT_VALUE


# ---------------------------------------------------------------------------
# 減速
# ---------------------------------------------------------------------------


def _suppress(sim: BattleSimulator, unit: MobileSuit, action: str = "ATTACK") -> dict:
    resources = sim.unit_resources[str(unit.id)]
    resources.update(suppression=100.0, current_action=action)
    return resources


def test_suppression_slows_advance() -> None:
    """前進する機体は、制圧値に応じて最高速度が下がる."""
    sim, _, target = _setup()
    _suppress(sim, target)

    assert _top_speed(sim, target, 180.0) == pytest.approx(_MAX_SPEED * 0.5, rel=0.05)


@pytest.mark.parametrize("action", ["RETREAT", "DISENGAGE", "HIT_AND_AWAY"])
def test_advance_only_spares_falling_back(action: str) -> None:
    """後退・逃走の行動では遅くならない."""
    sim, _, target = _setup()
    _suppress(sim, target, action)

    assert _top_speed(sim, target, 0.0) == pytest.approx(_MAX_SPEED, rel=0.05)


def test_all_directions_slows_falling_back() -> None:
    """後退・逃走にも効かせる設定では、撤退中も遅くなる."""
    sim, _, target = _setup(suppression=replace(_CONFIG, advance_only=False))
    _suppress(sim, target, "RETREAT")

    assert _top_speed(sim, target, 0.0) == pytest.approx(_MAX_SPEED * 0.5, rel=0.05)


def test_suppression_also_slows_boost() -> None:
    """ブースト中の速度にも倍率を掛ける."""
    sim, _, target = _setup()
    resources = sim.unit_resources[str(target.id)]
    resources["is_boosting"] = True
    boosted = _top_speed(sim, target, 180.0)
    _suppress(sim, target)

    assert _top_speed(sim, target, 180.0) == pytest.approx(boosted * 0.5, rel=0.05)


# ---------------------------------------------------------------------------
# 有効にする範囲
# ---------------------------------------------------------------------------


def test_mission_battle_enables_suppression() -> None:
    """作戦の戦闘は既定の係数で制圧を有効にする."""
    player = _unit("Player", "PLAYER", 0.0, _rifle())
    setup = build_mission_battle(
        build_retreat_support_mission(), [player], BattleConditions()
    )

    assert setup.suppression == SuppressionConfig()

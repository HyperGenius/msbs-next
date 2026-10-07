"""Tests for 胴体の向きと移動の向きのずれによる速度の割引と、後退中のブースト禁止."""

import numpy as np
import pytest

from app.engine.constants import (
    BACKPEDAL_ANGLE_DEG,
    DEFAULT_BOOST_SPEED_MULTIPLIER,
    FACING_SPEED_MODIFIER_BACK,
    FACING_SPEED_MODIFIER_FRONT,
    FACING_SPEED_MODIFIER_SIDE,
)
from app.engine.facing import (
    facing_offset_deg,
    facing_speed_modifier,
    is_backpedaling,
)
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon

_MAX_SPEED = 80.0
_DT = 0.1


def _make_unit(name: str, side: str, team_id: str, x: float) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=0,
        mobility=1.0,
        position=Vector3(x=x, y=0, z=0),
        weapons=[Weapon(id="rifle", name="Rifle", power=10, range=500.0, accuracy=80)],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        max_speed=_MAX_SPEED,
        acceleration=300.0,
        deceleration=50.0,
        max_turn_rate=360.0,
        max_en=1000,
        en_recovery=0,
        sensor_range=5000.0,
    )


def _setup(distance: float = 2000.0) -> tuple[BattleSimulator, MobileSuit, MobileSuit]:
    player = _make_unit("Player", "PLAYER", "PT", 0.0)
    enemy = _make_unit("Enemy", "ENEMY", "ET", distance)
    sim = BattleSimulator(player, [enemy])
    sim.team_detected_units[player.team_id] = {enemy.id}
    sim.team_detected_units[enemy.team_id] = {player.id}
    return sim, player, enemy


def _face(sim: BattleSimulator, unit: MobileSuit, body: float, movement: float) -> dict:
    resources = sim.unit_resources[str(unit.id)]
    resources["body_heading_deg"] = body
    resources["movement_heading_deg"] = movement
    return resources


def _direction(heading_deg: float) -> np.ndarray:
    rad = np.radians(heading_deg)
    return np.array([np.cos(rad), 0.0, np.sin(rad)])


def _run_inertia(
    sim: BattleSimulator, unit: MobileSuit, heading: float, steps: int = 50
) -> float:
    """移動の向きを heading に保って動かし、最後の 2 ステップの速さの大きい方を返す.

    上限ちょうどの速さでは 1 ステップ減速するため、上限と上限より少し低い値を往復する。
    """
    speeds = []
    for _ in range(steps):
        sim._apply_inertia(unit, _direction(heading), _DT)
        resources = sim.unit_resources[str(unit.id)]
        speeds.append(float(np.linalg.norm(resources["velocity_vec"])))
    return max(speeds[-2:])


# ---------------------------------------------------------------------------
# 係数
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("movement", "expected"),
    [
        (0.0, FACING_SPEED_MODIFIER_FRONT),
        (90.0, FACING_SPEED_MODIFIER_SIDE),
        (-90.0, FACING_SPEED_MODIFIER_SIDE),
        (180.0, FACING_SPEED_MODIFIER_BACK),
        (-180.0, FACING_SPEED_MODIFIER_BACK),
    ],
)
def test_modifier_matches_constants_at_front_side_back(
    movement: float, expected: float
) -> None:
    """前・横・後ろでは定数の値そのものになること."""
    assert facing_speed_modifier(0.0, movement) == pytest.approx(expected)


def test_modifier_between_points_lies_between_neighbors() -> None:
    """中間の角度では、両隣の点の値の間に入ること."""
    assert (
        FACING_SPEED_MODIFIER_SIDE
        < facing_speed_modifier(0.0, 45.0)
        < FACING_SPEED_MODIFIER_FRONT
    )
    assert (
        FACING_SPEED_MODIFIER_BACK
        < facing_speed_modifier(0.0, 135.0)
        < FACING_SPEED_MODIFIER_SIDE
    )
    # 区間の中点では両端の平均になる。
    assert facing_speed_modifier(0.0, 45.0) == pytest.approx(
        (FACING_SPEED_MODIFIER_FRONT + FACING_SPEED_MODIFIER_SIDE) / 2.0
    )
    assert facing_speed_modifier(0.0, 135.0) == pytest.approx(
        (FACING_SPEED_MODIFIER_SIDE + FACING_SPEED_MODIFIER_BACK) / 2.0
    )


def test_modifier_decreases_monotonically_with_offset() -> None:
    """ずれが大きいほど係数が小さくなる（増えない）こと."""
    values = [facing_speed_modifier(0.0, float(deg)) for deg in range(0, 181)]
    assert all(a >= b for a, b in zip(values, values[1:], strict=False))


def test_modifier_is_flat_near_front() -> None:
    """前方付近のわずかなずれでは、ほとんど割り引かないこと."""
    assert facing_speed_modifier(0.0, 5.0) > FACING_SPEED_MODIFIER_FRONT - 0.005


def test_offset_wraps_around_and_is_symmetric() -> None:
    """ずれは 360 度をまたいでも 0〜180 度で測り、左右で同じになること."""
    assert facing_offset_deg(350.0, 10.0) == pytest.approx(20.0)
    assert facing_offset_deg(10.0, 350.0) == pytest.approx(20.0)
    assert facing_offset_deg(-170.0, 170.0) == pytest.approx(20.0)
    assert facing_offset_deg(0.0, 540.0) == pytest.approx(180.0)
    assert facing_speed_modifier(30.0, 100.0) == pytest.approx(
        facing_speed_modifier(30.0, -40.0)
    )


def test_backpedaling_threshold() -> None:
    """ずれが後退中の角度を超えたときだけ後退中とみなすこと."""
    assert not is_backpedaling(0.0, BACKPEDAL_ANGLE_DEG)
    assert is_backpedaling(0.0, BACKPEDAL_ANGLE_DEG + 1.0)
    assert is_backpedaling(0.0, 180.0)
    assert not is_backpedaling(0.0, 0.0)


# ---------------------------------------------------------------------------
# 慣性モデルへの適用
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("movement", "modifier"),
    [
        (0.0, FACING_SPEED_MODIFIER_FRONT),
        (90.0, FACING_SPEED_MODIFIER_SIDE),
        (180.0, FACING_SPEED_MODIFIER_BACK),
    ],
)
def test_max_speed_is_discounted_by_facing(movement: float, modifier: float) -> None:
    """胴体の向きを固定すると、移動の向きに応じて最高速度が割り引かれること."""
    sim, player, _ = _setup()
    _face(sim, player, 0.0, movement)

    speed = _run_inertia(sim, player, movement)

    assert speed == pytest.approx(_MAX_SPEED * modifier)


def test_speed_above_discounted_cap_decays_by_deceleration() -> None:
    """後退へ移った直後は止まらず、減速度で上限まで落ちること."""
    sim, player, _ = _setup()
    resources = _face(sim, player, 0.0, 180.0)
    resources["velocity_vec"] = _direction(180.0) * _MAX_SPEED

    speed = _run_inertia(sim, player, 180.0, steps=1)

    assert speed == pytest.approx(_MAX_SPEED - player.deceleration * _DT)
    assert _run_inertia(sim, player, 180.0) == pytest.approx(
        _MAX_SPEED * FACING_SPEED_MODIFIER_BACK
    )


def test_boost_multiplier_is_not_applied_while_backpedaling() -> None:
    """ブースト中でも後退中は倍率を掛けないこと."""
    sim, player, _ = _setup()
    resources = _face(sim, player, 0.0, 180.0)
    resources["is_boosting"] = True

    speed = _run_inertia(sim, player, 180.0)

    assert speed == pytest.approx(_MAX_SPEED * FACING_SPEED_MODIFIER_BACK)


def test_boost_multiplier_still_applies_when_moving_forward() -> None:
    """前進中のブーストは従来どおり倍率を掛けること."""
    sim, player, _ = _setup()
    resources = _face(sim, player, 0.0, 0.0)
    resources["is_boosting"] = True

    speed = _run_inertia(sim, player, 0.0)

    assert speed == pytest.approx(_MAX_SPEED * DEFAULT_BOOST_SPEED_MULTIPLIER)


# ---------------------------------------------------------------------------
# 後退中のブースト禁止
# ---------------------------------------------------------------------------


def _boost_dash(sim: BattleSimulator, player: MobileSuit, enemy: MobileSuit) -> None:
    pos_actor = player.position.to_numpy()
    pos_target = enemy.position.to_numpy()
    diff = pos_target - pos_actor
    sim._handle_boost_dash_action(
        player,
        enemy,
        player.weapons[0],
        pos_actor,
        pos_target,
        diff,
        float(np.linalg.norm(diff)),
        _DT,
    )


def test_boost_does_not_start_while_backpedaling() -> None:
    """後退中はブーストダッシュを選んでもブーストが始まらないこと."""
    sim, player, enemy = _setup()
    resources = _face(sim, player, 0.0, 180.0)

    _boost_dash(sim, player, enemy)

    assert resources["is_boosting"] is False
    assert not [log for log in sim.logs if log.action_type == "BOOST_START"]


def test_boost_starts_when_not_backpedaling() -> None:
    """後退中でなければブーストが始まること."""
    sim, player, enemy = _setup()
    resources = _face(sim, player, 0.0, 0.0)

    _boost_dash(sim, player, enemy)

    assert resources["is_boosting"] is True


def test_boost_ends_when_unit_starts_backpedaling() -> None:
    """ブースト中に後退へ入ったら、ブーストを終えること."""
    sim, player, _ = _setup()
    resources = _face(sim, player, 0.0, 180.0)
    resources["is_boosting"] = True

    assert sim._check_boost_cancel(player, None, _DT) is True
    assert resources["is_boosting"] is False
    end_logs = [log for log in sim.logs if log.action_type == "BOOST_END"]
    assert len(end_logs) == 1
    assert "後退中" in end_logs[0].message

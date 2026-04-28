"""Tests for the inertia model (Phase 3-1).

慣性モデルの旋回制限・加速制限・位置更新を検証する。
"""

import math

import numpy as np
import pytest

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


def _make_weapon(range_: float = 500.0) -> Weapon:
    return Weapon(
        id="test_weapon",
        name="Test Weapon",
        power=10,
        range=range_,
        accuracy=80,
    )


def _make_unit(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    max_speed: float = 80.0,
    acceleration: float = 30.0,
    deceleration: float = 50.0,
    max_turn_rate: float = 360.0,
    weapon_range: float = 500.0,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=0,
        mobility=1.0,
        position=position,
        weapons=[_make_weapon(weapon_range)],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        max_speed=max_speed,
        acceleration=acceleration,
        deceleration=deceleration,
        max_turn_rate=max_turn_rate,
    )


# ---------------------------------------------------------------------------
# unit_resources 初期化テスト
# ---------------------------------------------------------------------------


def test_unit_resources_initialized_with_velocity_and_heading() -> None:
    """unit_resources に velocity_vec / heading_deg が初期値で追加されること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=200, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    for unit in sim.units:
        uid = str(unit.id)
        resources = sim.unit_resources[uid]
        assert "velocity_vec" in resources
        assert "heading_deg" in resources
        np.testing.assert_array_equal(resources["velocity_vec"], np.zeros(3))
        assert resources["heading_deg"] == 0.0


# ---------------------------------------------------------------------------
# _apply_inertia テスト
# ---------------------------------------------------------------------------


def test_apply_inertia_accelerates_from_rest() -> None:
    """静止状態から加速すること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
        acceleration=30.0, max_speed=80.0,
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=1000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    dt = 0.1
    desired = np.array([1.0, 0.0, 0.0])  # +x 方向
    sim._apply_inertia(player, desired, dt)

    resources = sim.unit_resources[str(player.id)]
    speed = float(np.linalg.norm(resources["velocity_vec"]))
    expected_speed = 30.0 * dt  # = 3.0 m/s
    assert abs(speed - expected_speed) < 1e-6


def test_apply_inertia_does_not_exceed_max_speed() -> None:
    """速度が max_speed を超えないこと."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
        acceleration=30.0, max_speed=80.0,
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=1000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    desired = np.array([1.0, 0.0, 0.0])
    dt = 0.1

    # 速度が max_speed に達するまで加速
    for _ in range(100):
        sim._apply_inertia(player, desired, dt)

    resources = sim.unit_resources[str(player.id)]
    speed = float(np.linalg.norm(resources["velocity_vec"]))
    assert speed <= player.max_speed + 1e-6


def test_apply_inertia_position_updates_correctly() -> None:
    """位置が velocity_vec * dt だけ更新されること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
        acceleration=300.0, max_speed=80.0,  # 大きい加速度で1ステップで max_speed へ
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=1000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    # 1ステップ目で max_speed まで達するように加速度を大きく設定
    dt = 0.1
    desired = np.array([1.0, 0.0, 0.0])

    # 複数ステップ実行してから位置をチェック
    initial_pos = player.position.to_numpy().copy()
    sim._apply_inertia(player, desired, dt)
    resources = sim.unit_resources[str(player.id)]
    v = resources["velocity_vec"]
    # 位置変化 = velocity * dt
    expected_pos = initial_pos + v * dt
    actual_pos = player.position.to_numpy()
    np.testing.assert_allclose(actual_pos, expected_pos, atol=1e-6)


# ---------------------------------------------------------------------------
# 旋回制限テスト
# ---------------------------------------------------------------------------


def test_ma_turn_rate_limited() -> None:
    """MA (max_turn_rate=30) が 1ステップで 3° 以上旋回しないこと."""
    ma = _make_unit(
        "MA", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
        max_turn_rate=30.0, acceleration=15.0, max_speed=300.0,
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=0, y=0, z=1000))
    sim = BattleSimulator(ma, [enemy])

    dt = 0.1
    # heading_deg を 0° (正面: +x 方向) に設定
    uid = str(ma.id)
    sim.unit_resources[uid]["heading_deg"] = 0.0

    # 目標方向を +z 方向（90° 旋回が必要）
    desired = np.array([0.0, 0.0, 1.0])
    sim._apply_inertia(ma, desired, dt)

    resources = sim.unit_resources[uid]
    # max_turn_rate=30 deg/s, dt=0.1s → 最大 3° 旋回
    max_rotation = 30.0 * dt  # = 3.0°
    heading_change = abs(resources["heading_deg"] - 0.0)
    assert heading_change <= max_rotation + 1e-6


def test_normal_ms_turn_rate_larger_than_ma() -> None:
    """通常MS (max_turn_rate=360) が MA (max_turn_rate=30) より多く旋回できること."""
    normal_ms = _make_unit(
        "NormalMS", "PLAYER", "PT1", Vector3(x=0, y=0, z=0),
        max_turn_rate=360.0, acceleration=30.0, max_speed=80.0,
    )
    ma = _make_unit(
        "MA", "ENEMY", "ET1", Vector3(x=100, y=0, z=0),
        max_turn_rate=30.0, acceleration=15.0, max_speed=300.0,
    )
    enemy_normal = _make_unit("Enemy", "ENEMY", "ET1", Vector3(x=100, y=0, z=0))
    enemy_ma = _make_unit("Enemy2", "PLAYER", "PT2", Vector3(x=100, y=0, z=0))

    sim_normal = BattleSimulator(normal_ms, [enemy_normal])
    sim_ma = BattleSimulator(ma, [enemy_ma])

    dt = 0.1
    uid_normal = str(normal_ms.id)
    uid_ma = str(ma.id)

    # 両方とも heading_deg = 0° から 90° 方向に旋回
    sim_normal.unit_resources[uid_normal]["heading_deg"] = 0.0
    sim_ma.unit_resources[uid_ma]["heading_deg"] = 0.0

    desired = np.array([0.0, 0.0, 1.0])  # +z 方向 (90° 旋回が必要)
    sim_normal._apply_inertia(normal_ms, desired, dt)
    sim_ma._apply_inertia(ma, desired, dt)

    heading_normal = sim_normal.unit_resources[uid_normal]["heading_deg"]
    heading_ma = sim_ma.unit_resources[uid_ma]["heading_deg"]

    # 通常MSは MA より大きく旋回できる
    assert heading_normal > heading_ma


# ---------------------------------------------------------------------------
# BattleLog velocity_snapshot テスト
# ---------------------------------------------------------------------------


def test_velocity_snapshot_recorded_in_move_log() -> None:
    """移動ログに velocity_snapshot が記録されること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
        acceleration=30.0, max_speed=80.0,
    )
    # 射程外の敵（移動が発生するように遠距離に配置）
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=2000, y=0, z=0),
        weapon_range=50.0,
    )
    sim = BattleSimulator(player, [enemy])

    sim.step()

    move_logs = [log for log in sim.logs if log.action_type == "MOVE"]
    assert len(move_logs) > 0, "移動ログが生成されること"

    for log in move_logs:
        assert log.velocity_snapshot is not None, (
            "velocity_snapshot が記録されていること"
        )
        assert isinstance(log.velocity_snapshot, Vector3)


# ---------------------------------------------------------------------------
# _process_movement / _search_movement 統合テスト
# ---------------------------------------------------------------------------


def test_process_movement_uses_inertia() -> None:
    """_process_movement が慣性モデルを使って位置更新すること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
        acceleration=30.0, max_speed=80.0,
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=500, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    initial_x = player.position.x
    dt = 0.1

    pos_actor = player.position.to_numpy()
    pos_target = enemy.position.to_numpy()
    diff_vector = pos_target - pos_actor
    distance = float(np.linalg.norm(diff_vector))

    sim._process_movement(player, pos_actor, pos_target, diff_vector, distance, dt)

    # 慣性モデルにより位置が変化すること（速度が増加）
    assert player.position.x > initial_x


def test_search_movement_uses_inertia() -> None:
    """_search_movement が慣性モデルを使って位置更新すること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
        acceleration=30.0, max_speed=80.0,
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=2000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    # 索敵フェーズは実行しない → 未発見

    initial_x = player.position.x
    sim._search_movement(player, dt=0.1)

    # 慣性モデルにより位置が変化すること
    assert player.position.x > initial_x

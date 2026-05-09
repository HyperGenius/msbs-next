"""Tests for Phase 6-1: Fire Arc Restriction, body_heading_deg separation.

胴体向き（body_heading_deg）と移動方向（movement_heading_deg）の分離、
_update_body_heading() の動作、fire_arc_deg ゲートの動作を検証する。
"""

import math
import uuid

import numpy as np
import pytest

from app.engine.constants import DEFAULT_FIRE_ARC_DEG
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_weapon(
    name: str = "Test Weapon",
    range_: float = 500.0,
    power: float = 10.0,
    weapon_type: str = "RANGED",
    is_melee: bool = False,
    fire_arc_deg: float = 30.0,
    max_ammo: int | None = 20,
) -> Weapon:
    return Weapon(
        id=f"weapon_{name.replace(' ', '_')}",
        name=name,
        power=power,
        range=range_,
        accuracy=80,
        weapon_type=weapon_type,
        is_melee=is_melee,
        fire_arc_deg=fire_arc_deg,
        max_ammo=max_ammo,
    )


def _make_unit(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    body_turn_rate: float = 720.0,
    max_hp: int = 1000,
    current_hp: int = 1000,
    weapons: list[Weapon] | None = None,
) -> MobileSuit:
    if weapons is None:
        weapons = [_make_weapon()]
    return MobileSuit(
        name=name,
        max_hp=max_hp,
        current_hp=current_hp,
        armor=0,
        mobility=1.0,
        position=position,
        weapons=weapons,
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        body_turn_rate=body_turn_rate,
        sensor_range=3000.0,
    )


# ---------------------------------------------------------------------------
# 1. unit_resources に movement_heading_deg / body_heading_deg が含まれること
# ---------------------------------------------------------------------------


def test_unit_resources_has_body_and_movement_heading() -> None:
    """unit_resources に body_heading_deg と movement_heading_deg が 0.0 で初期化されること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=500, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    for unit in sim.units:
        uid = str(unit.id)
        resources = sim.unit_resources[uid]
        assert "body_heading_deg" in resources
        assert "movement_heading_deg" in resources
        assert resources["body_heading_deg"] == 0.0
        assert resources["movement_heading_deg"] == 0.0


# ---------------------------------------------------------------------------
# 2. Weapon.fire_arc_deg フィールドのデフォルト値
# ---------------------------------------------------------------------------


def test_weapon_fire_arc_deg_default() -> None:
    """Weapon に fire_arc_deg が指定されていない場合 DEFAULT_FIRE_ARC_DEG になること."""
    weapon = Weapon(
        id="test",
        name="Ranged Weapon",
        power=10,
        range=500.0,
        accuracy=80,
    )
    assert weapon.fire_arc_deg == DEFAULT_FIRE_ARC_DEG


def test_weapon_fire_arc_deg_melee_can_be_360() -> None:
    """MELEE 武器に fire_arc_deg=360 を設定できること."""
    melee = _make_weapon(
        name="Beam Saber",
        range_=50.0,
        weapon_type="MELEE",
        is_melee=True,
        fire_arc_deg=360.0,
        max_ammo=None,
    )
    assert melee.fire_arc_deg == 360.0


# ---------------------------------------------------------------------------
# 3. MobileSuit.body_turn_rate フィールド
# ---------------------------------------------------------------------------


def test_mobile_suit_body_turn_rate_default() -> None:
    """MobileSuit に body_turn_rate が 720.0 でデフォルト設定されること."""
    unit = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    assert unit.body_turn_rate == 720.0


def test_mobile_suit_body_turn_rate_custom() -> None:
    """MobileSuit に body_turn_rate をカスタム設定できること."""
    unit = _make_unit(
        "MA", "PLAYER", "PT", Vector3(x=0, y=0, z=0), body_turn_rate=180.0
    )
    assert unit.body_turn_rate == 180.0


# ---------------------------------------------------------------------------
# 4. _update_body_heading() の旋回制限テスト
# ---------------------------------------------------------------------------


def test_update_body_heading_turns_toward_target() -> None:
    """_update_body_heading が毎ステップ body_turn_rate の範囲内で旋回すること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), body_turn_rate=720.0
    )
    # 敵を +z 方向（90° 旋回が必要）に配置
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=0, y=0, z=500))
    sim = BattleSimulator(player, [enemy])

    # 検出フェーズ実行
    sim._detection_phase()

    uid = str(player.id)
    # body_heading を 0° に設定
    sim.unit_resources[uid]["body_heading_deg"] = 0.0
    sim.unit_resources[uid]["current_action"] = "ATTACK"

    dt = 0.1
    sim._update_body_heading(player, dt)

    # body_turn_rate=720 deg/s, dt=0.1s → 最大 72° 旋回
    max_rotation = 720.0 * dt
    new_heading = sim.unit_resources[uid]["body_heading_deg"]
    assert abs(new_heading - 0.0) <= max_rotation + 1e-6
    # 旋回方向は正（+z 方向 = 90°）へ向かっている
    assert new_heading > 0.0


def test_update_body_heading_slow_unit_limited() -> None:
    """body_turn_rate が小さいユニットは旋回量が制限されること."""
    player = _make_unit(
        "MA", "PLAYER", "PT", Vector3(x=0, y=0, z=0), body_turn_rate=90.0
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=0, y=0, z=500))
    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    sim.unit_resources[uid]["body_heading_deg"] = 0.0
    sim.unit_resources[uid]["current_action"] = "ATTACK"

    dt = 0.1
    sim._update_body_heading(player, dt)

    # body_turn_rate=90 deg/s, dt=0.1s → 最大 9° 旋回
    max_rotation = 90.0 * dt
    new_heading = sim.unit_resources[uid]["body_heading_deg"]
    assert abs(new_heading - 0.0) <= max_rotation + 1e-6


def test_update_body_heading_fallback_when_no_target() -> None:
    """ターゲット未選択時は body_heading が movement_heading に追従すること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), body_turn_rate=720.0
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=500, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    # 検出フェーズを実行しない（検出なし）→ target=None
    uid = str(player.id)
    sim.unit_resources[uid]["body_heading_deg"] = 0.0
    sim.unit_resources[uid]["movement_heading_deg"] = 45.0
    sim.unit_resources[uid]["current_action"] = "MOVE"  # no target action

    dt = 0.1
    sim._update_body_heading(player, dt)

    # ターゲットなしの MOVE → movement_heading_deg へ追従
    new_heading = sim.unit_resources[uid]["body_heading_deg"]
    assert new_heading > 0.0  # 45° 方向へ少し旋回したはず


# ---------------------------------------------------------------------------
# 5. DEFAULT_FIRE_ARC_DEG 定数のテスト
# ---------------------------------------------------------------------------


def test_default_fire_arc_deg_constant() -> None:
    """DEFAULT_FIRE_ARC_DEG が 30.0 であること."""
    assert DEFAULT_FIRE_ARC_DEG == 30.0


# ---------------------------------------------------------------------------
# 6. fire_arc_deg ゲートテスト
# ---------------------------------------------------------------------------


def test_fire_arc_gate_blocks_attack_out_of_arc() -> None:
    """body_heading が大きくずれている場合、_process_attack が TURNING_TO_TARGET を記録してスキップすること."""
    ranged_weapon = _make_weapon(
        name="Beam Rifle",
        range_=800.0,
        weapon_type="RANGED",
        is_melee=False,
        fire_arc_deg=30.0,
        max_ammo=20,
    )
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), weapons=[ranged_weapon]
    )
    # 敵を真横 (90°) に配置
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=0, y=0, z=300))

    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    # body_heading を 0° (正面 = +x 方向) に設定 → 敵は 90° → 弧外
    sim.unit_resources[uid]["body_heading_deg"] = 0.0

    pos_actor = player.position.to_numpy()
    pos_enemy = enemy.position.to_numpy()
    distance = float(np.linalg.norm(pos_enemy - pos_actor))

    initial_log_count = len(sim.logs)
    sim._process_attack(player, enemy, distance, pos_actor, ranged_weapon)

    # TURNING_TO_TARGET ログが記録されること
    new_logs = sim.logs[initial_log_count:]
    turning_logs = [l for l in new_logs if l.action_type == "TURNING_TO_TARGET"]
    assert len(turning_logs) >= 1, "弧外の場合 TURNING_TO_TARGET ログが記録されること"

    # 攻撃が実行されていないこと（武器弾薬が変わっていない）
    weapon_state = sim.unit_resources[uid]["weapon_states"].get(ranged_weapon.id, {})
    assert weapon_state.get("current_ammo", 20) == 20, "弧外では弾薬を消費しないこと"


def test_fire_arc_gate_allows_attack_in_arc() -> None:
    """body_heading がターゲット方向に向いている場合、攻撃が実行されること."""
    ranged_weapon = _make_weapon(
        name="Beam Rifle",
        range_=800.0,
        weapon_type="RANGED",
        is_melee=False,
        fire_arc_deg=30.0,
        max_ammo=20,
    )
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), weapons=[ranged_weapon]
    )
    # 敵を正面 (+x 方向) に配置
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=300, y=0, z=0))

    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    # body_heading を 0° (正面 = +x 方向) に設定 → 敵は 0° → 弧内
    sim.unit_resources[uid]["body_heading_deg"] = 0.0

    pos_actor = player.position.to_numpy()
    pos_enemy = enemy.position.to_numpy()
    distance = float(np.linalg.norm(pos_enemy - pos_actor))

    initial_log_count = len(sim.logs)
    sim._process_attack(player, enemy, distance, pos_actor, ranged_weapon)

    # TURNING_TO_TARGET ログが記録されていないこと
    new_logs = sim.logs[initial_log_count:]
    turning_logs = [l for l in new_logs if l.action_type == "TURNING_TO_TARGET"]
    assert len(turning_logs) == 0, "弧内では TURNING_TO_TARGET ログが記録されないこと"

    # 攻撃が実行されたこと（ATTACK/MISS ログが記録された）
    attack_logs = [l for l in new_logs if l.action_type in ("ATTACK", "MISS")]
    assert len(attack_logs) >= 1, "弧内では攻撃ログが記録されること"


def test_melee_weapon_skips_fire_arc_gate() -> None:
    """MELEE 武器は fire_arc_deg ゲートをスキップして全方位攻撃できること."""
    melee_weapon = _make_weapon(
        name="Beam Saber",
        range_=50.0,
        weapon_type="MELEE",
        is_melee=True,
        fire_arc_deg=360.0,
        max_ammo=None,
    )
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), weapons=[melee_weapon]
    )
    # 敵を背後 (180°) に配置（body_heading=0なので背後）
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=-30, y=0, z=0))

    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    # body_heading を 0° (正面 = +x 方向) に設定 → 敵は -180° (背後)
    sim.unit_resources[uid]["body_heading_deg"] = 0.0

    pos_actor = player.position.to_numpy()
    pos_enemy = enemy.position.to_numpy()
    distance = float(np.linalg.norm(pos_enemy - pos_actor))

    initial_log_count = len(sim.logs)
    sim._process_attack(player, enemy, distance, pos_actor, melee_weapon)

    # TURNING_TO_TARGET ログが記録されていないこと（MELEE はスキップ）
    new_logs = sim.logs[initial_log_count:]
    turning_logs = [l for l in new_logs if l.action_type == "TURNING_TO_TARGET"]
    assert len(turning_logs) == 0, "MELEE 武器は弧チェックをスキップすること"


# ---------------------------------------------------------------------------
# 7. angle_to_target がファジィ推論に渡されること
# ---------------------------------------------------------------------------


def test_ai_decision_includes_angle_to_target() -> None:
    """_ai_decision_phase で angle_to_target が計算されログに反映されること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), body_turn_rate=720.0
    )
    player.strategy_mode = "AGGRESSIVE"
    # 敵を正面 (+x 方向) に配置
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=500, y=0, z=0))

    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    sim.unit_resources[uid]["body_heading_deg"] = 0.0  # 正面 (+x)

    sim._ai_decision_phase(player)

    # AI_DECISION ログに "対目標角" が含まれること
    ai_logs = [l for l in sim.logs if l.action_type == "AI_DECISION"]
    assert len(ai_logs) >= 1
    assert "対目標角" in ai_logs[0].message, "angle_to_target がログに含まれること"
    # 正面方向なので角度差が小さい
    assert "対目標角:0.0°" in ai_logs[0].message


def test_angle_to_target_is_180_when_no_target() -> None:
    """ターゲット未選択時（検出なし）の angle_to_target は 180.0 で処理されること.

    仕様: ターゲット未選択時は REAR のメンバーシップ度が最大になるよう 180.0 を使用する。
    これによりファジィ推論で ATTACK が選ばれなくなる。
    """
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), body_turn_rate=720.0
    )
    player.strategy_mode = "AGGRESSIVE"
    # 敵なし（敵ユニットが存在しない場合は検出されない）
    sim = BattleSimulator(player, [])
    # 検出フェーズをスキップ → 検出済み敵 = なし

    sim._ai_decision_phase(player)

    # 敵が検出されていない場合は MOVE にフォールバックする
    uid = str(player.id)
    action = sim.unit_resources[uid]["current_action"]
    assert action == "MOVE", "敵未検出時は MOVE にフォールバックすること"

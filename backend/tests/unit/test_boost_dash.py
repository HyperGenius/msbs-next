"""Tests for the Boost Dash System (Phase B).

ブーストダッシュシステムの速度制御・EN消費・キャンセル判定・ログ記録を検証する。
"""

import numpy as np

from app.engine.constants import (
    DEFAULT_BOOST_COOLDOWN,
    DEFAULT_BOOST_EN_COST,
    DEFAULT_BOOST_MAX_DURATION,
    DEFAULT_BOOST_SPEED_MULTIPLIER,
)
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_weapon(
    range_: float = 500.0,
    is_melee: bool = False,
    max_ammo: int | None = None,
) -> Weapon:
    return Weapon(
        id="test_weapon",
        name="Test Weapon",
        power=10,
        range=range_,
        accuracy=80,
        is_melee=is_melee,
        max_ammo=max_ammo,
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
    max_en: int = 1000,
    boost_speed_multiplier: float = DEFAULT_BOOST_SPEED_MULTIPLIER,
    boost_en_cost: float = DEFAULT_BOOST_EN_COST,
    boost_max_duration: float = DEFAULT_BOOST_MAX_DURATION,
    boost_cooldown: float = DEFAULT_BOOST_COOLDOWN,
    is_melee_weapon: bool = False,
    sensor_range: float = 5000.0,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=0,
        mobility=1.0,
        position=position,
        weapons=[_make_weapon(weapon_range, is_melee=is_melee_weapon)],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        max_speed=max_speed,
        acceleration=acceleration,
        deceleration=deceleration,
        max_turn_rate=max_turn_rate,
        max_en=max_en,
        en_recovery=0,  # テスト中のEN回復を無効化
        boost_speed_multiplier=boost_speed_multiplier,
        boost_en_cost=boost_en_cost,
        boost_max_duration=boost_max_duration,
        boost_cooldown=boost_cooldown,
        sensor_range=sensor_range,
    )


# ---------------------------------------------------------------------------
# unit_resources 初期化テスト
# ---------------------------------------------------------------------------


def test_unit_resources_initialized_with_boost_state() -> None:
    """unit_resources にブースト状態フィールドが初期化されること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=200, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    for unit in sim.units:
        uid = str(unit.id)
        resources = sim.unit_resources[uid]
        assert "is_boosting" in resources
        assert "boost_elapsed" in resources
        assert "boost_cooldown_remaining" in resources
        assert resources["is_boosting"] is False
        assert resources["boost_elapsed"] == 0.0
        assert resources["boost_cooldown_remaining"] == 0.0


# ---------------------------------------------------------------------------
# ブースト速度上限テスト
# ---------------------------------------------------------------------------


def test_boost_allows_speed_above_max_speed() -> None:
    """ブースト中は max_speed × boost_speed_multiplier を超える速度が出ること."""
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        Vector3(x=0, y=0, z=0),
        max_speed=80.0,
        acceleration=300.0,  # 1ステップで高速に達するよう大きく設定
        boost_speed_multiplier=2.0,
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=5000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    uid = str(player.id)
    # ブーストを有効化
    sim.unit_resources[uid]["is_boosting"] = True

    dt = 0.1
    desired = np.array([1.0, 0.0, 0.0])

    # 十分なステップを実行して boost 速度に近づける
    for _ in range(50):
        sim._apply_inertia(player, desired, dt)

    speed = float(np.linalg.norm(sim.unit_resources[uid]["velocity_vec"]))
    # ブースト中は max_speed (80m/s) を超えられること
    assert speed > player.max_speed, (
        f"ブースト中の速度 ({speed:.1f}) が max_speed ({player.max_speed}) を超えていること"
    )
    # ブースト速度上限 (160m/s) を超えないこと
    boost_max = player.max_speed * player.boost_speed_multiplier
    assert speed <= boost_max + 1e-6, (
        f"ブースト速度 ({speed:.1f}) が上限 ({boost_max}) を超えていないこと"
    )


def test_non_boost_speed_capped_at_max_speed() -> None:
    """非ブースト時は max_speed を超えないこと（既存動作の確認）."""
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        Vector3(x=0, y=0, z=0),
        max_speed=80.0,
        acceleration=300.0,
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=5000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    uid = str(player.id)
    assert sim.unit_resources[uid]["is_boosting"] is False

    desired = np.array([1.0, 0.0, 0.0])
    for _ in range(50):
        sim._apply_inertia(player, desired, 0.1)

    speed = float(np.linalg.norm(sim.unit_resources[uid]["velocity_vec"]))
    assert speed <= player.max_speed + 1e-6


# ---------------------------------------------------------------------------
# EN 消費・クールダウンテスト
# ---------------------------------------------------------------------------


def test_boost_en_consumption_per_dt() -> None:
    """ブースト中は EN が boost_en_cost × dt ずつ消費されること."""
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        Vector3(x=0, y=0, z=0),
        max_en=1000,
        boost_en_cost=5.0,
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=5000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = True
    initial_en = sim.unit_resources[uid]["current_en"]

    dt = 0.1
    sim._refresh_phase(dt)

    expected_en = initial_en - player.boost_en_cost * dt
    assert abs(sim.unit_resources[uid]["current_en"] - expected_en) < 1e-6


def test_boost_elapsed_increments_during_boost() -> None:
    """ブースト中は boost_elapsed が dt ずつ増加すること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=5000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = True
    sim.unit_resources[uid]["boost_elapsed"] = 0.0

    dt = 0.1
    sim._refresh_phase(dt)

    assert abs(sim.unit_resources[uid]["boost_elapsed"] - dt) < 1e-6


def test_cooldown_decrements_when_not_boosting() -> None:
    """非ブースト中はクールダウンが dt ずつ減少すること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=5000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = False
    sim.unit_resources[uid]["boost_cooldown_remaining"] = 5.0

    dt = 0.1
    sim._refresh_phase(dt)

    assert abs(sim.unit_resources[uid]["boost_cooldown_remaining"] - 4.9) < 1e-6


def test_cooldown_does_not_go_negative() -> None:
    """クールダウンが 0 以下にならないこと."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=5000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = False
    sim.unit_resources[uid]["boost_cooldown_remaining"] = 0.05  # dt より小さい値

    dt = 0.1
    sim._refresh_phase(dt)

    assert sim.unit_resources[uid]["boost_cooldown_remaining"] == 0.0


def test_en_not_recovered_during_boost() -> None:
    """ブースト中は EN 回復が行われないこと（消費のみ）."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), max_en=1000, boost_en_cost=5.0
    )
    # en_recovery=0 を設定しているので、ブーストなしならENは変わらない
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=5000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = True
    sim.unit_resources[uid]["current_en"] = 500.0

    sim._refresh_phase(0.1)

    # EN は回復せず消費されること
    assert sim.unit_resources[uid]["current_en"] < 500.0


# ---------------------------------------------------------------------------
# ブーストキャンセル判定テスト
# ---------------------------------------------------------------------------


def test_boost_cancel_max_duration() -> None:
    """boost_elapsed >= boost_max_duration でブーストがキャンセルされること."""
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        Vector3(x=0, y=0, z=0),
        boost_max_duration=3.0,
        boost_cooldown=5.0,
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=5000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = True
    sim.unit_resources[uid]["boost_elapsed"] = 3.0  # 最大継続時間に到達

    cancelled = sim._check_boost_cancel(player, enemy, 0.1)

    assert cancelled is True
    assert sim.unit_resources[uid]["is_boosting"] is False
    assert sim.unit_resources[uid]["boost_cooldown_remaining"] == player.boost_cooldown


def test_boost_cancel_en_empty() -> None:
    """EN 枯渇でブーストがキャンセルされること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=5000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = True
    sim.unit_resources[uid]["current_en"] = 0.0  # EN 枯渇

    cancelled = sim._check_boost_cancel(player, enemy, 0.1)

    assert cancelled is True
    assert sim.unit_resources[uid]["is_boosting"] is False


def test_boost_cancel_melee_arrival_range() -> None:
    """ターゲットが MELEE_BOOST_ARRIVAL_RANGE 以内に入るとキャンセルされること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    # ターゲットを MELEE_BOOST_ARRIVAL_RANGE (100m) 以内に配置
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=50, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = True

    cancelled = sim._check_boost_cancel(player, enemy, 0.1)

    assert cancelled is True
    assert sim.unit_resources[uid]["is_boosting"] is False


def test_boost_cancel_inertia_cancel() -> None:
    """停止予想位置から遠距離武器の射程内に入ったらキャンセルされること."""
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        Vector3(x=0, y=0, z=0),
        max_speed=160.0,
        deceleration=50.0,
        weapon_range=500.0,
    )
    # ターゲットを射程内 (500m) よりやや遠い位置（400m）に配置
    # 現在速度: 100 m/s → 停止距離 = 100² / (2 × 50) = 100m
    # 停止予想位置: 100m → ターゲットまでの距離 = 400 - 100 = 300m < 500m → キャンセル
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=400, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = True
    # 現在速度を +x 方向 100 m/s に設定
    sim.unit_resources[uid]["velocity_vec"] = np.array([100.0, 0.0, 0.0])

    cancelled = sim._check_boost_cancel(player, enemy, 0.1)

    assert cancelled is True, (
        "停止予想位置 (100m) からターゲット (400m) まで 300m < 武器射程 (500m) → キャンセルされること"
    )
    assert sim.unit_resources[uid]["is_boosting"] is False


def test_boost_no_cancel_when_target_far() -> None:
    """ターゲットが遠い場合はキャンセルされないこと."""
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        Vector3(x=0, y=0, z=0),
        max_speed=160.0,
        deceleration=50.0,
        weapon_range=500.0,
        boost_max_duration=10.0,
    )
    # ターゲットを2000m遠くに配置（停止予想位置からも射程外）
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=2000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = True
    sim.unit_resources[uid]["current_en"] = 1000.0
    sim.unit_resources[uid]["boost_elapsed"] = 0.0
    # 現在速度: 80m/s → 停止距離 = 80² / (2 × 50) = 64m
    # 停止予想位置: 64m → ターゲットまでの距離 = 2000 - 64 = 1936m > 500m → 継続
    sim.unit_resources[uid]["velocity_vec"] = np.array([80.0, 0.0, 0.0])

    cancelled = sim._check_boost_cancel(player, enemy, 0.1)

    assert cancelled is False


def test_boost_cancel_logs_boost_end() -> None:
    """ブーストキャンセル時に BOOST_END ログが記録されること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), boost_max_duration=3.0
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=5000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = True
    sim.unit_resources[uid]["boost_elapsed"] = 3.0

    _ = len(sim.logs)
    sim._check_boost_cancel(player, enemy, 0.1)

    boost_end_logs = [log for log in sim.logs if log.action_type == "BOOST_END"]
    assert len(boost_end_logs) >= 1
    assert boost_end_logs[-1].actor_id == player.id


def test_boost_not_started_during_cooldown() -> None:
    """クールダウン中は BOOST_DASH アクションが MOVE にフォールバックされること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=200, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    sim.unit_resources[uid]["boost_cooldown_remaining"] = 5.0  # クールダウン中
    sim.unit_resources[uid]["current_action"] = "BOOST_DASH"

    # _ai_decision_phase を経由してクールダウン中の BOOST_DASH が MOVE にフォールバックされること
    # ここでは直接 _action_phase を呼んで is_boosting が True にならないことを確認
    sim._action_phase(player, 0.1)

    # クールダウン中のため is_boosting が True にならないこと
    assert sim.unit_resources[uid]["is_boosting"] is False


# ---------------------------------------------------------------------------
# BOOST_START ログテスト
# ---------------------------------------------------------------------------


def test_boost_start_logged_on_boost_dash_action() -> None:
    """BOOST_DASH アクション実行時に BOOST_START ログが記録されること."""
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        Vector3(x=0, y=0, z=0),
        boost_max_duration=10.0,  # 十分な継続時間
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=2000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    sim.unit_resources[uid]["current_action"] = "BOOST_DASH"
    sim.unit_resources[uid]["boost_cooldown_remaining"] = 0.0
    sim.unit_resources[uid]["is_boosting"] = False

    sim._action_phase(player, 0.1)

    boost_start_logs = [log for log in sim.logs if log.action_type == "BOOST_START"]
    assert len(boost_start_logs) >= 1
    assert boost_start_logs[0].actor_id == player.id


def test_boost_start_not_logged_when_already_boosting() -> None:
    """既にブースト中の場合は BOOST_START が重複記録されないこと."""
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        Vector3(x=0, y=0, z=0),
        boost_max_duration=10.0,
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=2000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    sim.unit_resources[uid]["current_action"] = "BOOST_DASH"
    sim.unit_resources[uid]["boost_cooldown_remaining"] = 0.0
    sim.unit_resources[uid]["is_boosting"] = True  # 既にブースト中
    sim.unit_resources[uid]["boost_elapsed"] = 0.5

    initial_boost_start_count = len(
        [log for log in sim.logs if log.action_type == "BOOST_START"]
    )
    sim._action_phase(player, 0.1)

    boost_start_logs = [log for log in sim.logs if log.action_type == "BOOST_START"]
    # 新たに BOOST_START が追加されないこと
    assert len(boost_start_logs) == initial_boost_start_count


# ---------------------------------------------------------------------------
# EN 切れによるブースト終了テスト
# ---------------------------------------------------------------------------


def test_boost_ends_when_en_depleted_via_refresh() -> None:
    """_refresh_phase で EN が枯渇した場合、次の _check_boost_cancel でブーストが終了すること."""
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        Vector3(x=0, y=0, z=0),
        max_en=10,
        boost_en_cost=100.0,  # 大きな消費で即座に枯渇
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=5000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])
    sim._detection_phase()

    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = True
    sim.unit_resources[uid]["boost_elapsed"] = 0.0
    sim.unit_resources[uid]["current_en"] = 5.0  # 少量のEN

    # refresh phase で EN を消費
    sim._refresh_phase(0.1)

    # EN が枯渇していること
    assert sim.unit_resources[uid]["current_en"] <= 0.0

    # check_boost_cancel で終了
    cancelled = sim._check_boost_cancel(player, enemy, 0.1)
    assert cancelled is True
    assert sim.unit_resources[uid]["is_boosting"] is False


# ---------------------------------------------------------------------------
# MobileSuit フィールドテスト
# ---------------------------------------------------------------------------


def test_mobile_suit_has_boost_fields() -> None:
    """MobileSuit にブースト関連フィールドが追加されていること."""
    ms = _make_unit(
        "TestMS",
        "PLAYER",
        "PT",
        Vector3(x=0, y=0, z=0),
        boost_speed_multiplier=2.5,
        boost_en_cost=8.0,
        boost_max_duration=4.0,
        boost_cooldown=6.0,
    )
    assert ms.boost_speed_multiplier == 2.5
    assert ms.boost_en_cost == 8.0
    assert ms.boost_max_duration == 4.0
    assert ms.boost_cooldown == 6.0


def test_mobile_suit_boost_field_defaults() -> None:
    """MobileSuit のブースト関連フィールドがデフォルト値を持つこと."""
    ms = MobileSuit(
        name="DefaultMS",
        max_hp=1000,
        current_hp=1000,
        side="PLAYER",
    )
    assert ms.boost_speed_multiplier == DEFAULT_BOOST_SPEED_MULTIPLIER
    assert ms.boost_en_cost == DEFAULT_BOOST_EN_COST
    assert ms.boost_max_duration == DEFAULT_BOOST_MAX_DURATION
    assert ms.boost_cooldown == DEFAULT_BOOST_COOLDOWN

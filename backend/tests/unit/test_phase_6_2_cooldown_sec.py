"""Phase 6-2 テスト — 武器クールダウンの時間ステップ制対応.

検証項目:
    1. Weapon.cooldown_sec フィールドが追加され、デフォルト値 1.0 が設定されている
    2. unit_resources["weapon_states"] が cooldown_remaining_sec: float を持つ
    3. _refresh_phase() で dt ずつデクリメントされ、0未満にならない
    4. _check_attack_resources() が cooldown_remaining_sec > 0.0 を正しく判定する
    5. 発射後に cooldown_sec の値が cooldown_remaining_sec にセットされる
    6. WAIT ログに秒単位（例: 残り1.5s）で表示される
    7. cool_down_turn への参照がシミュレーションコードから除去されている
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


# ---------------------------------------------------------------------------
# テスト用ヘルパー
# ---------------------------------------------------------------------------

DT = 0.1  # シミュレーションのタイムステップ (秒)


def _make_weapon(
    weapon_id: str = "w1",
    cooldown_sec: float = 0.0,
    max_ammo: int | None = None,
    en_cost: int = 0,
    power: int = 100,
    range_: int = 500,
) -> Weapon:
    return Weapon(
        id=weapon_id,
        name="Test Weapon",
        power=power,
        range=range_,
        accuracy=100,
        type="PHYSICAL",
        max_ammo=max_ammo,
        en_cost=en_cost,
        cooldown_sec=cooldown_sec,
    )


def _make_player(weapons: list[Weapon]) -> MobileSuit:
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
    )


def _make_enemy(distance: float = 100.0) -> MobileSuit:
    return MobileSuit(
        name="Enemy MS",
        max_hp=500,
        current_hp=500,
        armor=0,
        mobility=0.5,
        position=Vector3(x=distance, y=0, z=0),
        weapons=[_make_weapon("enemy_w", cooldown_sec=0.0)],
        side="ENEMY",
        team_id="ENEMY_TEAM",
        max_en=1000,
        en_recovery=100,
        max_propellant=1000,
        sensor_range=1000,
    )


# ---------------------------------------------------------------------------
# 1. Weapon.cooldown_sec フィールドとデフォルト値
# ---------------------------------------------------------------------------


def test_cooldown_sec_default_value() -> None:
    """Weapon.cooldown_sec のデフォルト値が 1.0 であること."""
    weapon = Weapon(id="w", name="Default", power=10, range=100, accuracy=80)
    assert weapon.cooldown_sec == 1.0, "cooldown_sec のデフォルトは 1.0 秒"


def test_cooldown_sec_can_be_set() -> None:
    """Weapon.cooldown_sec に任意の値を設定できること."""
    for val in [0.0, 0.3, 1.5, 2.0, 5.0]:
        w = Weapon(
            id="w",
            name="Test",
            power=10,
            range=100,
            accuracy=80,
            cooldown_sec=val,
        )
        assert w.cooldown_sec == val


def test_cool_down_turn_still_exists() -> None:
    """後方互換フィールド cool_down_turn が引き続き存在すること."""
    w = Weapon(id="w", name="Old", power=10, range=100, accuracy=80, cool_down_turn=3)
    assert w.cool_down_turn == 3, "cool_down_turn は後方互換フィールドとして残る"


# ---------------------------------------------------------------------------
# 2. unit_resources["weapon_states"] が cooldown_remaining_sec を持つ
# ---------------------------------------------------------------------------


def test_weapon_state_initialized_with_cooldown_remaining_sec() -> None:
    """BattleSimulator 初期化後に cooldown_remaining_sec: 0.0 が設定されること."""
    weapon = _make_weapon("w1", cooldown_sec=2.0)
    player = _make_player([weapon])
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])

    weapon_state = sim.unit_resources[str(player.id)]["weapon_states"][weapon.id]
    assert "cooldown_remaining_sec" in weapon_state, (
        "cooldown_remaining_sec キーが weapon_states に存在すること"
    )
    assert weapon_state["cooldown_remaining_sec"] == 0.0, (
        "初期値は 0.0 (クールダウンなし)"
    )


def test_weapon_state_no_current_cool_down_key() -> None:
    """旧フィールド current_cool_down が weapon_states に存在しないこと (Phase 6-2)."""
    weapon = _make_weapon("w1", cooldown_sec=1.0)
    player = _make_player([weapon])
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])

    weapon_state = sim.unit_resources[str(player.id)]["weapon_states"][weapon.id]
    assert "current_cool_down" not in weapon_state, (
        "current_cool_down キーはもはや存在しない (Phase 6-2 で除去)"
    )


# ---------------------------------------------------------------------------
# 3. _refresh_phase() が dt ずつデクリメントし 0 未満にならない
# ---------------------------------------------------------------------------


def test_refresh_phase_decrements_cooldown_by_dt() -> None:
    """_refresh_phase() が cooldown_remaining_sec を dt=0.1 ずつ減らすこと."""
    weapon = _make_weapon("w1", cooldown_sec=2.0)
    player = _make_player([weapon])
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])

    player_id = str(player.id)
    # 手動でクールダウンを設定
    sim.unit_resources[player_id]["weapon_states"][weapon.id][
        "cooldown_remaining_sec"
    ] = 1.0

    # 1ステップ実行 (dt=0.1)
    sim.step()

    remaining = sim.unit_resources[player_id]["weapon_states"][weapon.id][
        "cooldown_remaining_sec"
    ]
    # 1.0 - 0.1 = 0.9 (浮動小数点誤差を考慮)
    assert abs(remaining - 0.9) < 1e-9, f"期待値 0.9 秒, 実際 {remaining}"


def test_refresh_phase_does_not_go_below_zero() -> None:
    """_refresh_phase() が cooldown_remaining_sec を 0.0 未満にしないこと."""
    weapon = _make_weapon("w1", cooldown_sec=1.0)
    player = _make_player([weapon])
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])

    player_id = str(player.id)
    # 残り 0.05 秒（1ステップ分より少ない）
    sim.unit_resources[player_id]["weapon_states"][weapon.id][
        "cooldown_remaining_sec"
    ] = 0.05

    sim.step()

    remaining = sim.unit_resources[player_id]["weapon_states"][weapon.id][
        "cooldown_remaining_sec"
    ]
    assert remaining == 0.0, f"0.0 未満にならないこと, 実際 {remaining}"


# ---------------------------------------------------------------------------
# 4. _check_attack_resources() が cooldown_remaining_sec > 0.0 を判定
# ---------------------------------------------------------------------------


def test_check_attack_resources_blocked_when_cooldown_positive() -> None:
    """cooldown_remaining_sec > 0 の場合、攻撃がブロックされること."""
    weapon = _make_weapon("w1", cooldown_sec=2.0)
    player = _make_player([weapon])
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])

    player_id = str(player.id)
    resources = sim.unit_resources[player_id]
    weapon_state = sim._get_or_init_weapon_state(weapon, resources)
    # クールダウン中に設定
    weapon_state["cooldown_remaining_sec"] = 1.5

    ok, reason = sim._check_attack_resources(weapon, weapon_state, resources)
    assert not ok, "クールダウン中は攻撃不可"
    assert "クールダウン" in reason, f"reason にクールダウン情報が含まれること: {reason}"
    assert "1.5s" in reason, f"残り秒数が表示されること: {reason}"


def test_check_attack_resources_allowed_when_cooldown_zero() -> None:
    """cooldown_remaining_sec == 0.0 の場合、クールダウンでブロックされないこと."""
    weapon = _make_weapon("w1", cooldown_sec=2.0)
    player = _make_player([weapon])
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])

    player_id = str(player.id)
    resources = sim.unit_resources[player_id]
    weapon_state = sim._get_or_init_weapon_state(weapon, resources)
    # 初期状態 (cooldown_remaining_sec = 0.0) では攻撃可能
    ok, _ = sim._check_attack_resources(weapon, weapon_state, resources)
    assert ok, "クールダウンが 0.0 の場合は攻撃可能"


# ---------------------------------------------------------------------------
# 5. 発射後に cooldown_sec が cooldown_remaining_sec にセットされる
# ---------------------------------------------------------------------------


def test_consume_sets_cooldown_remaining_after_fire() -> None:
    """_consume_attack_resources() が cooldown_sec を cooldown_remaining_sec にセットすること."""
    cooldown = 1.5
    weapon = _make_weapon("w1", cooldown_sec=cooldown, power=10)
    player = _make_player([weapon])
    enemy = _make_enemy(distance=100.0)
    sim = BattleSimulator(player, [enemy])

    player_id = str(player.id)
    resources = sim.unit_resources[player_id]
    weapon_state = sim._get_or_init_weapon_state(weapon, resources)

    assert weapon_state["cooldown_remaining_sec"] == 0.0

    sim._consume_attack_resources(weapon, weapon_state, resources)

    assert weapon_state["cooldown_remaining_sec"] == cooldown, (
        f"発射後に cooldown_remaining_sec = {cooldown} がセットされること, "
        f"実際 {weapon_state['cooldown_remaining_sec']}"
    )


def test_consume_no_cooldown_when_cooldown_sec_zero() -> None:
    """cooldown_sec=0.0 の場合、発射後も cooldown_remaining_sec が 0.0 のままであること."""
    weapon = _make_weapon("w1", cooldown_sec=0.0, power=10)
    player = _make_player([weapon])
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])

    player_id = str(player.id)
    resources = sim.unit_resources[player_id]
    weapon_state = sim._get_or_init_weapon_state(weapon, resources)

    sim._consume_attack_resources(weapon, weapon_state, resources)

    assert weapon_state["cooldown_remaining_sec"] == 0.0, (
        f"cooldown_sec=0.0 なら cooldown_remaining_sec は 0.0 のまま: "
        f"{weapon_state['cooldown_remaining_sec']}"
    )


# ---------------------------------------------------------------------------
# 6. WAIT ログに秒単位で表示される
# ---------------------------------------------------------------------------


def test_wait_log_shows_seconds() -> None:
    """クールダウン待機 WAIT ログが秒単位（例: 残り1.5s）で表示されること."""
    cooldown_weapon = Weapon(
        id="cannon",
        name="Heavy Cannon",
        power=200,
        range=600,
        accuracy=75,
        type="PHYSICAL",
        max_ammo=None,
        en_cost=0,
        cooldown_sec=2.0,
    )

    player = MobileSuit(
        name="Player",
        max_hp=2000,
        current_hp=2000,
        weapons=[cooldown_weapon],
        max_en=1000,
        en_recovery=100,
        max_propellant=1000,
        sensor_range=1000,
    )

    enemy = MobileSuit(
        name="Enemy",
        max_hp=2000,
        current_hp=2000,
        side="ENEMY",
        position=Vector3(x=100, y=0, z=0),
        sensor_range=1000,
        max_en=1000,
        en_recovery=100,
        max_propellant=1000,
    )

    sim = BattleSimulator(player, [enemy])

    for _ in range(30):
        sim.step()
        if sim.is_finished:
            break

    wait_logs = [
        log
        for log in sim.logs
        if log.action_type == "WAIT" and "冷却を待ちながら" in (log.message or "")
    ]
    assert len(wait_logs) > 0, "WAIT ログ（クールダウン待機）が発生すること"

    for wl in wait_logs:
        assert "s）" in (wl.message or ""), (
            f"WAIT ログが秒単位（残りXXs）で表示されること: {wl.message}"
        )
        assert "ターン" not in (wl.message or ""), (
            f"旧ターン表記が残っていないこと: {wl.message}"
        )

"""Issue #506 テスト — 武装持ち替えアルゴリズムと行動不能ペナルティ.

検証項目:
    1. calculate_weapon_switch_lock_sec() が REF ステータスで行動不能タイムを短縮する（最大30%）
    2. unit_resources に active_weapon_id / weapon_switch_lock_remaining_sec が初期化される
    3. _refresh_phase() が weapon_switch_lock_remaining_sec を dt ずつデクリメントし 0 未満にならない
    4. 初回の武器選択は持ち替え扱いにならず、行動不能タイムが発生しない
    5. NEVER ポリシー: 手持ち武器が使用不能になっても持ち替えない
    6. RACK_ONLY ポリシー: 手持ち武器が使用不能になった時だけ強制的に持ち替える
    7. BALANCED ポリシー: スコア差が閾値未満なら持ち替えない、閾値以上なら持ち替える
    8. AGGRESSIVE ポリシー: 拘束コストを無視し、スコアが少しでも高ければ持ち替える
    9. 持ち替え中（weapon_switch_lock_remaining_sec > 0）は武器選択が None を返す
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.engine.calculator import PilotStats, calculate_weapon_switch_lock_sec
from app.engine.constants import WEAPON_SWITCH_LOCK_BASE_SEC
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon

DT = 0.1


def _make_weapon(
    weapon_id: str = "w1",
    cooldown_sec: float = 0.0,
    max_ammo: int | None = None,
) -> Weapon:
    return Weapon(
        id=weapon_id,
        name=f"Weapon-{weapon_id}",
        power=100,
        range=500,
        accuracy=100,
        type="PHYSICAL",
        max_ammo=max_ammo,
        cooldown_sec=cooldown_sec,
    )


def _make_player(weapons: list[Weapon], tactics: dict | None = None) -> MobileSuit:
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
        tactics=tactics or {"priority": "CLOSEST", "range": "BALANCED"},
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
# 1. calculate_weapon_switch_lock_sec()
# ---------------------------------------------------------------------------


def test_switch_lock_sec_zero_ref_returns_base() -> None:
    """REF=0 なら基礎値と同一の行動不能タイムを返すこと."""
    assert calculate_weapon_switch_lock_sec(1.5, ref_stat=0) == 1.5


def test_switch_lock_sec_reduced_by_ref() -> None:
    """REF に応じて行動不能タイムが短縮されること."""
    # ref=10 -> 10%短縮
    assert calculate_weapon_switch_lock_sec(1.5, ref_stat=10) == 1.5 * 0.9


def test_switch_lock_sec_capped_at_30_percent() -> None:
    """REF による短縮が最大30%で頭打ちになること."""
    # ref=30 で上限（30%短縮）に到達し、それ以上は変わらない
    capped = calculate_weapon_switch_lock_sec(1.5, ref_stat=30)
    over = calculate_weapon_switch_lock_sec(1.5, ref_stat=100)
    assert capped == 1.5 * 0.7
    assert over == capped


# ---------------------------------------------------------------------------
# 2/3. unit_resources 初期化・_refresh_phase() でのデクリメント
# ---------------------------------------------------------------------------


def test_unit_resources_initialized_with_switch_fields() -> None:
    """unit_resources に持ち替え関連フィールドが初期化されること."""
    weapon = _make_weapon("w1")
    player = _make_player([weapon])
    sim = BattleSimulator(player, [_make_enemy()])

    resources = sim.unit_resources[str(player.id)]
    assert resources["active_weapon_id"] is None
    assert resources["weapon_switch_lock_remaining_sec"] == 0.0


def test_refresh_phase_decrements_switch_lock() -> None:
    """_refresh_phase() が dt ずつ減算し 0 未満にならないこと."""
    weapon = _make_weapon("w1")
    player = _make_player([weapon])
    sim = BattleSimulator(player, [_make_enemy()])
    resources = sim.unit_resources[str(player.id)]
    resources["weapon_switch_lock_remaining_sec"] = 0.25

    sim._refresh_phase(dt=DT)
    assert abs(resources["weapon_switch_lock_remaining_sec"] - 0.15) < 1e-9

    sim._refresh_phase(dt=DT)
    sim._refresh_phase(dt=DT)
    # 0未満にならない
    assert resources["weapon_switch_lock_remaining_sec"] == 0.0


# ---------------------------------------------------------------------------
# 4. 初回の武器選択は拘束タイムを発生させない
# ---------------------------------------------------------------------------


def test_first_weapon_selection_has_no_lock() -> None:
    """初回の武器選択は持ち替え扱いにならず、行動不能タイムが発生しないこと."""
    weapon = _make_weapon("w1")
    player = _make_player([weapon])
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])

    selected = sim._select_weapon_with_switch_policy(player, enemy)

    assert selected is not None
    assert selected.id == "w1"
    resources = sim.unit_resources[str(player.id)]
    assert resources["active_weapon_id"] == "w1"
    assert resources["weapon_switch_lock_remaining_sec"] == 0.0


# ---------------------------------------------------------------------------
# 5/6. NEVER / RACK_ONLY: 手持ち武器が使用不能になった場合の挙動差
# ---------------------------------------------------------------------------


def test_never_policy_does_not_switch_even_when_unusable() -> None:
    """NEVER は手持ち武器が使用不能になっても持ち替えないこと."""
    w1 = _make_weapon("w1")
    w2 = _make_weapon("w2")
    player = _make_player(
        [w1, w2], tactics={"priority": "CLOSEST", "weapon_switch_policy": "NEVER"}
    )
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])
    resources = sim.unit_resources[str(player.id)]

    # w1 を手持ち武器として確定させる
    resources["active_weapon_id"] = "w1"
    # w1 をクールダウン中（使用不能）にする
    resources["weapon_states"]["w1"] = {
        "current_ammo": None,
        "cooldown_remaining_sec": 5.0,
    }

    selected = sim._select_weapon_with_switch_policy(player, enemy)

    assert selected is None, "手持ち武器が使用不能でも NEVER は攻撃できないまま待機する"
    assert resources["active_weapon_id"] == "w1", "NEVER は持ち替えない"
    assert resources["weapon_switch_lock_remaining_sec"] == 0.0


def test_rack_only_policy_forces_switch_when_unusable() -> None:
    """RACK_ONLY は手持ち武器が使用不能になった時だけ強制的に持ち替えること."""
    w1 = _make_weapon("w1")
    w2 = _make_weapon("w2")
    player = _make_player(
        [w1, w2],
        tactics={"priority": "CLOSEST", "weapon_switch_policy": "RACK_ONLY"},
    )
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])
    resources = sim.unit_resources[str(player.id)]

    resources["active_weapon_id"] = "w1"
    resources["weapon_states"]["w1"] = {
        "current_ammo": None,
        "cooldown_remaining_sec": 5.0,
    }

    selected = sim._select_weapon_with_switch_policy(player, enemy)

    assert selected is None, "持ち替え開始ステップは攻撃不可"
    assert resources["active_weapon_id"] == "w2", (
        "使用不能になったため w2 へ強制的に持ち替える"
    )
    assert resources["weapon_switch_lock_remaining_sec"] > 0.0


def test_rack_only_policy_keeps_weapon_while_usable() -> None:
    """RACK_ONLY は使用可能な間は持ち替えないこと."""
    w1 = _make_weapon("w1")
    w2 = _make_weapon("w2")
    player = _make_player(
        [w1, w2],
        tactics={"priority": "CLOSEST", "weapon_switch_policy": "RACK_ONLY"},
    )
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])
    resources = sim.unit_resources[str(player.id)]
    resources["active_weapon_id"] = "w1"

    # w1 は使用可能なまま。仮に fuzzy 推論が w2 を推しても、RACK_ONLY は持ち替えない
    sim._select_weapon_fuzzy = lambda actor, target: w2  # type: ignore[method-assign]
    sim._weapon_score_cache[str(player.id)] = {"w1": 0.5, "w2": 0.9}

    selected = sim._select_weapon_with_switch_policy(player, enemy)

    assert selected is not None and selected.id == "w1"
    assert resources["active_weapon_id"] == "w1"
    assert resources["weapon_switch_lock_remaining_sec"] == 0.0


# ---------------------------------------------------------------------------
# 7. BALANCED: スコア差と閾値
# ---------------------------------------------------------------------------


def test_balanced_policy_does_not_switch_below_margin() -> None:
    """BALANCED はスコア差が閾値未満なら持ち替えないこと."""
    w1 = _make_weapon("w1")
    w2 = _make_weapon("w2")
    player = _make_player(
        [w1, w2],
        tactics={"priority": "CLOSEST", "weapon_switch_policy": "BALANCED"},
    )
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])
    resources = sim.unit_resources[str(player.id)]
    resources["active_weapon_id"] = "w1"

    sim._select_weapon_fuzzy = lambda actor, target: w2  # type: ignore[method-assign]
    # スコア差 0.1 < WEAPON_SWITCH_BALANCED_SCORE_MARGIN (0.15)
    sim._weapon_score_cache[str(player.id)] = {"w1": 0.5, "w2": 0.6}

    selected = sim._select_weapon_with_switch_policy(player, enemy)

    assert selected is not None and selected.id == "w1"
    assert resources["weapon_switch_lock_remaining_sec"] == 0.0


def test_balanced_policy_switches_above_margin() -> None:
    """BALANCED はスコア差が閾値以上なら持ち替えること."""
    w1 = _make_weapon("w1")
    w2 = _make_weapon("w2")
    player = _make_player(
        [w1, w2],
        tactics={"priority": "CLOSEST", "weapon_switch_policy": "BALANCED"},
    )
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])
    resources = sim.unit_resources[str(player.id)]
    resources["active_weapon_id"] = "w1"

    sim._select_weapon_fuzzy = lambda actor, target: w2  # type: ignore[method-assign]
    # スコア差 0.2 >= WEAPON_SWITCH_BALANCED_SCORE_MARGIN (0.15)
    sim._weapon_score_cache[str(player.id)] = {"w1": 0.5, "w2": 0.7}

    selected = sim._select_weapon_with_switch_policy(player, enemy)

    assert selected is None, "持ち替え開始ステップは攻撃不可"
    assert resources["active_weapon_id"] == "w2"
    assert resources["weapon_switch_lock_remaining_sec"] > 0.0


# ---------------------------------------------------------------------------
# 8. AGGRESSIVE: 拘束コストを無視して常に切り替える
# ---------------------------------------------------------------------------


def test_aggressive_policy_switches_on_tiny_score_gain() -> None:
    """AGGRESSIVE は僅かなスコア差でも持ち替えること."""
    w1 = _make_weapon("w1")
    w2 = _make_weapon("w2")
    player = _make_player(
        [w1, w2],
        tactics={"priority": "CLOSEST", "weapon_switch_policy": "AGGRESSIVE"},
    )
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])
    resources = sim.unit_resources[str(player.id)]
    resources["active_weapon_id"] = "w1"

    sim._select_weapon_fuzzy = lambda actor, target: w2  # type: ignore[method-assign]
    sim._weapon_score_cache[str(player.id)] = {"w1": 0.50, "w2": 0.51}

    selected = sim._select_weapon_with_switch_policy(player, enemy)

    assert selected is None
    assert resources["active_weapon_id"] == "w2"
    assert resources["weapon_switch_lock_remaining_sec"] > 0.0


# ---------------------------------------------------------------------------
# 9. 持ち替え中は武器選択が None を返す（移動のみ可能）
# ---------------------------------------------------------------------------


def test_locked_during_switch_returns_none() -> None:
    """持ち替え中（weapon_switch_lock_remaining_sec > 0）は武器選択が None を返すこと."""
    weapon = _make_weapon("w1")
    player = _make_player([weapon])
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy])
    resources = sim.unit_resources[str(player.id)]
    resources["active_weapon_id"] = "w1"
    resources["weapon_switch_lock_remaining_sec"] = WEAPON_SWITCH_LOCK_BASE_SEC

    selected = sim._select_weapon_with_switch_policy(player, enemy)

    assert selected is None


def test_ref_stat_shortens_switch_lock_end_to_end() -> None:
    """REF ステータスが実際の持ち替え行動不能タイムを短縮すること（結合確認）."""
    w1 = _make_weapon("w1")
    w2 = _make_weapon("w2")
    player = _make_player(
        [w1, w2],
        tactics={"priority": "CLOSEST", "weapon_switch_policy": "AGGRESSIVE"},
    )
    enemy = _make_enemy()
    sim = BattleSimulator(player, [enemy], player_pilot_stats=PilotStats(ref=10))
    resources = sim.unit_resources[str(player.id)]
    resources["active_weapon_id"] = "w1"

    sim._select_weapon_fuzzy = lambda actor, target: w2  # type: ignore[method-assign]
    sim._weapon_score_cache[str(player.id)] = {"w1": 0.5, "w2": 0.9}

    sim._select_weapon_with_switch_policy(player, enemy)

    expected = calculate_weapon_switch_lock_sec(
        WEAPON_SWITCH_LOCK_BASE_SEC, ref_stat=10
    )
    assert abs(resources["weapon_switch_lock_remaining_sec"] - expected) < 1e-9
    assert expected < WEAPON_SWITCH_LOCK_BASE_SEC

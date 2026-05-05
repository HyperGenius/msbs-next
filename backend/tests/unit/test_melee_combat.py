"""Tests for the Melee Combat System (Phase C).

近接戦闘トリガー・格闘メリット・コンボシステムを検証する。

検証項目:
- 命中率距離補正 (_get_accuracy_modifier)
- 格闘武器の耐性無視 (_apply_hit_damage_modifiers)
- 格闘武器の弾薬・EN消費ゼロ (_check_attack_resources / _consume_attack_resources)
- 格闘コンボシステム (_process_melee_combo)
- 格闘命中後の再配置 (_process_engage_melee)
- ファジィ入力変数の追加 (ranged_ammo_ratio / los_blocked / boost_available)
"""

import random
from unittest.mock import patch

import numpy as np
import pytest

from app.engine.constants import (
    CLOSE_RANGE,
    COMBO_BASE_CHANCE,
    COMBO_DAMAGE_MULTIPLIER,
    COMBO_MAX_CHAIN,
    MELEE_CLOSE_ACCURACY_BONUS,
    MELEE_MID_ACCURACY_BONUS,
    MELEE_RANGE,
    POST_MELEE_DISTANCE,
    RANGED_CLOSE_ACCURACY_PENALTY,
    RANGED_MID_ACCURACY_PENALTY,
)
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_melee_weapon(power: int = 100) -> Weapon:
    """格闘武器を生成する."""
    return Weapon(
        id="melee_blade",
        name="Beam Saber",
        power=power,
        range=50.0,
        accuracy=90,
        type="PHYSICAL",
        weapon_type="MELEE",
        is_melee=True,
        optimal_range=30.0,
        decay_rate=0.0,
        max_ammo=None,
        en_cost=0,
    )


def _make_ranged_weapon(max_ammo: int | None = 20) -> Weapon:
    """遠距離武器を生成する."""
    return Weapon(
        id="beam_rifle",
        name="Beam Rifle",
        power=80,
        range=500.0,
        accuracy=85,
        type="BEAM",
        weapon_type="RANGED",
        is_melee=False,
        optimal_range=300.0,
        decay_rate=0.05,
        max_ammo=max_ammo,
        en_cost=10,
    )


def _make_close_range_weapon() -> Weapon:
    """近距離武器 (CLOSE_RANGE) を生成する."""
    return Weapon(
        id="shotgun",
        name="Shotgun",
        power=60,
        range=150.0,
        accuracy=80,
        type="PHYSICAL",
        weapon_type="CLOSE_RANGE",
        is_melee=False,
        optimal_range=50.0,
        decay_rate=0.1,
        max_ammo=None,
        en_cost=0,
    )


def _make_unit(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    weapons: list[Weapon] | None = None,
    hp: int = 1000,
    beam_resistance: float = 0.0,
    physical_resistance: float = 0.0,
    max_en: int = 1000,
    en_recovery: int = 0,
) -> MobileSuit:
    if weapons is None:
        weapons = [_make_melee_weapon()]
    return MobileSuit(
        name=name,
        max_hp=hp,
        current_hp=hp,
        armor=0,
        mobility=1.0,
        position=position,
        weapons=weapons,
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        max_en=max_en,
        en_recovery=en_recovery,
        sensor_range=5000.0,
        beam_resistance=beam_resistance,
        physical_resistance=physical_resistance,
    )


# ---------------------------------------------------------------------------
# 1. 命中率距離補正 (Phase C)
# ---------------------------------------------------------------------------


class TestGetAccuracyModifier:
    """_get_accuracy_modifier() の単体テスト."""

    def test_ranged_at_melee_range(self) -> None:
        """遠距離武器: d <= MELEE_RANGE で 0.4 倍."""
        mod = BattleSimulator._get_accuracy_modifier(MELEE_RANGE, "RANGED")
        assert mod == pytest.approx(RANGED_CLOSE_ACCURACY_PENALTY)

    def test_ranged_exactly_at_melee_range(self) -> None:
        """遠距離武器: d == MELEE_RANGE の境界値."""
        mod = BattleSimulator._get_accuracy_modifier(MELEE_RANGE, "RANGED")
        assert mod == pytest.approx(0.4)

    def test_ranged_at_close_range(self) -> None:
        """遠距離武器: MELEE_RANGE < d <= CLOSE_RANGE で 0.7 倍."""
        mod = BattleSimulator._get_accuracy_modifier(CLOSE_RANGE, "RANGED")
        assert mod == pytest.approx(RANGED_MID_ACCURACY_PENALTY)

    def test_ranged_beyond_close_range(self) -> None:
        """遠距離武器: d > CLOSE_RANGE で 1.0 倍."""
        mod = BattleSimulator._get_accuracy_modifier(300.0, "RANGED")
        assert mod == pytest.approx(1.0)

    def test_melee_at_melee_range(self) -> None:
        """格闘武器: d <= MELEE_RANGE で 1.5 倍."""
        mod = BattleSimulator._get_accuracy_modifier(MELEE_RANGE, "MELEE")
        assert mod == pytest.approx(MELEE_CLOSE_ACCURACY_BONUS)

    def test_melee_at_close_range(self) -> None:
        """格闘武器: MELEE_RANGE < d <= CLOSE_RANGE で 1.2 倍."""
        mod = BattleSimulator._get_accuracy_modifier(100.0, "MELEE")
        assert mod == pytest.approx(MELEE_MID_ACCURACY_BONUS)

    def test_melee_beyond_close_range(self) -> None:
        """格闘武器: d > CLOSE_RANGE で 0.8 倍."""
        mod = BattleSimulator._get_accuracy_modifier(300.0, "MELEE")
        assert mod == pytest.approx(0.8)

    def test_close_range_weapon_at_melee_range(self) -> None:
        """CLOSE_RANGE武器: d <= MELEE_RANGE で MELEE 扱い (1.5倍)."""
        mod = BattleSimulator._get_accuracy_modifier(30.0, "CLOSE_RANGE")
        assert mod == pytest.approx(MELEE_CLOSE_ACCURACY_BONUS)

    def test_close_range_weapon_at_close_range(self) -> None:
        """CLOSE_RANGE武器: d <= CLOSE_RANGE で 1.2倍."""
        mod = BattleSimulator._get_accuracy_modifier(150.0, "CLOSE_RANGE")
        assert mod == pytest.approx(MELEE_MID_ACCURACY_BONUS)


class TestCalculateHitChanceWithDistanceModifier:
    """_calculate_hit_chance() に距離補正が適用されることを検証する."""

    def test_melee_weapon_at_melee_range_has_higher_hit_than_ranged(self) -> None:
        """格闘武器は近接距離で遠距離武器より高い命中率を持つ."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
                             weapons=[_make_melee_weapon()])
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=30, y=0, z=0))
        sim = BattleSimulator(player, [enemy])

        melee_w = _make_melee_weapon()
        ranged_w = _make_ranged_weapon()
        distance = 30.0  # MELEE_RANGE 以内

        hit_melee, _ = sim._calculate_hit_chance(player, enemy, melee_w, distance)
        hit_ranged, _ = sim._calculate_hit_chance(player, enemy, ranged_w, distance)

        assert hit_melee > hit_ranged

    def test_ranged_weapon_at_melee_range_has_0_4_modifier(self) -> None:
        """遠距離武器は d <= 50m で 0.4 倍補正を受ける."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
                             weapons=[_make_ranged_weapon()])
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=30, y=0, z=0))
        sim = BattleSimulator(player, [enemy])
        sim_no_dist = BattleSimulator(player, [enemy])

        ranged_w = _make_ranged_weapon()
        distance = 30.0

        # 距離補正無し基準値を計算するため同条件で比較
        # 補正前の hit は ranged_w.accuracy と distance から計算できる
        # ここでは距離補正が適用されていることだけを確認
        hit_close, _ = sim._calculate_hit_chance(player, enemy, ranged_w, distance)
        hit_far, _ = sim_no_dist._calculate_hit_chance(player, enemy, ranged_w, 300.0)

        # 遠射程(300m)より近接距離(30m)の方が命中率が低い
        assert hit_close < hit_far

    def test_melee_weapon_hit_chance_clamped_to_100(self) -> None:
        """命中率は 100% を超えない."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
                             weapons=[_make_melee_weapon()])
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0))
        sim = BattleSimulator(player, [enemy])

        melee_w = Weapon(
            id="test",
            name="test",
            power=100,
            range=50.0,
            accuracy=99,
            weapon_type="MELEE",
            is_melee=True,
            optimal_range=10.0,
            decay_rate=0.0,
        )
        hit, _ = sim._calculate_hit_chance(player, enemy, melee_w, 10.0)
        assert hit <= 100.0
        assert hit >= 0.0


# ---------------------------------------------------------------------------
# 2. 格闘武器の耐性無視 (Phase C)
# ---------------------------------------------------------------------------


class TestMeleeResistanceBypass:
    """MELEE 武器は耐性を無視することを検証する."""

    def test_melee_weapon_ignores_physical_resistance(self) -> None:
        """MELEE 武器は physical_resistance を無視する."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
                             weapons=[_make_melee_weapon()])
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0),
                            physical_resistance=0.5)  # 50% 耐性
        sim = BattleSimulator(player, [enemy])

        melee_w = _make_melee_weapon(power=100)
        base_damage = 100

        result_damage, resistance_msg = sim._apply_hit_damage_modifiers(
            player, enemy, melee_w, base_damage
        )
        # 耐性無視: base_damage × 1.0 = 100
        assert result_damage == 100
        assert resistance_msg == ""

    def test_melee_weapon_ignores_beam_resistance(self) -> None:
        """MELEE 武器は beam_resistance を無視する."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
                             weapons=[_make_melee_weapon()])
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0),
                            beam_resistance=0.3)  # 30% ビーム耐性
        sim = BattleSimulator(player, [enemy])

        melee_w = _make_melee_weapon(power=100)
        base_damage = 100

        result_damage, resistance_msg = sim._apply_hit_damage_modifiers(
            player, enemy, melee_w, base_damage
        )
        # 耐性無視: base_damage × 1.0 = 100
        assert result_damage == 100
        assert resistance_msg == ""

    def test_ranged_weapon_applies_resistance(self) -> None:
        """遠距離武器は physical_resistance を適用する."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
                             weapons=[_make_ranged_weapon()])
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=100, y=0, z=0),
                            physical_resistance=0.5)
        sim = BattleSimulator(player, [enemy])

        ranged_w = Weapon(
            id="machine_gun",
            name="Machine Gun",
            power=100,
            range=400.0,
            accuracy=80,
            type="PHYSICAL",
            weapon_type="RANGED",
            is_melee=False,
        )
        base_damage = 100

        result_damage, _ = sim._apply_hit_damage_modifiers(
            player, enemy, ranged_w, base_damage
        )
        # 50% 耐性: 100 × (1 - 0.5) = 50
        assert result_damage == 50

    def test_is_melee_flag_also_bypasses_resistance(self) -> None:
        """is_melee=True フラグでも耐性を無視する（後方互換）."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0),
                            physical_resistance=0.5)
        sim = BattleSimulator(player, [enemy])

        legacy_melee_w = Weapon(
            id="old_blade",
            name="Old Blade",
            power=100,
            range=50.0,
            accuracy=90,
            type="PHYSICAL",
            weapon_type="RANGED",  # weapon_type は RANGED だが is_melee=True
            is_melee=True,
        )
        base_damage = 100
        result_damage, _ = sim._apply_hit_damage_modifiers(
            player, enemy, legacy_melee_w, base_damage
        )
        # is_melee=True なので耐性無視
        assert result_damage == 100


# ---------------------------------------------------------------------------
# 3. 格闘武器の弾薬・EN消費ゼロ (Phase C)
# ---------------------------------------------------------------------------


class TestMeleeZeroResourceConsumption:
    """MELEE 武器は弾薬・EN 消費がゼロであることを検証する."""

    def test_melee_weapon_passes_ammo_check(self) -> None:
        """MELEE 武器は弾切れ扱いにならない."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0))
        sim = BattleSimulator(player, [enemy])

        melee_w = _make_melee_weapon()
        weapon_state = {"current_ammo": 0, "current_cool_down": 0}
        resources = sim.unit_resources[str(player.id)]

        can_attack, reason = sim._check_attack_resources(melee_w, weapon_state, resources)
        assert can_attack, f"MELEE 武器で弾切れになってはいけない: {reason}"

    def test_melee_weapon_passes_en_check(self) -> None:
        """MELEE 武器は EN 不足扱いにならない."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
                             max_en=100)
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0))
        sim = BattleSimulator(player, [enemy])

        melee_w = Weapon(
            id="blade_en",
            name="Blade EN",
            power=100,
            range=50.0,
            accuracy=90,
            type="PHYSICAL",
            weapon_type="MELEE",
            is_melee=True,
            en_cost=999,  # 高 EN コストだが無視される
        )
        weapon_state = {"current_ammo": None, "current_cool_down": 0}
        resources = sim.unit_resources[str(player.id)]
        resources["current_en"] = 0  # EN ゼロ

        can_attack, reason = sim._check_attack_resources(melee_w, weapon_state, resources)
        assert can_attack, f"MELEE 武器で EN 不足になってはいけない: {reason}"

    def test_melee_weapon_does_not_consume_ammo(self) -> None:
        """MELEE 武器は弾薬を消費しない."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0))
        sim = BattleSimulator(player, [enemy])

        melee_w = Weapon(
            id="blade_ammo",
            name="Blade",
            power=100,
            range=50.0,
            accuracy=90,
            weapon_type="MELEE",
            is_melee=True,
            max_ammo=5,
        )
        weapon_state = {"current_ammo": 5, "current_cool_down": 0}
        resources = sim.unit_resources[str(player.id)]

        sim._consume_attack_resources(melee_w, weapon_state, resources)

        assert weapon_state["current_ammo"] == 5, "MELEE 武器は弾薬を消費しない"

    def test_melee_weapon_does_not_consume_en(self) -> None:
        """MELEE 武器は EN を消費しない."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0))
        sim = BattleSimulator(player, [enemy])

        melee_w = Weapon(
            id="blade_en_cost",
            name="Blade EN",
            power=100,
            range=50.0,
            accuracy=90,
            weapon_type="MELEE",
            is_melee=True,
            en_cost=100,
        )
        weapon_state = {"current_ammo": None, "current_cool_down": 0}
        resources = sim.unit_resources[str(player.id)]
        initial_en = resources["current_en"]

        sim._consume_attack_resources(melee_w, weapon_state, resources)

        assert resources["current_en"] == initial_en, "MELEE 武器は EN を消費しない"

    def test_ranged_weapon_consumes_ammo(self) -> None:
        """遠距離武器は弾薬を消費する（正常系確認）."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
                             weapons=[_make_ranged_weapon()])
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=100, y=0, z=0))
        sim = BattleSimulator(player, [enemy])

        ranged_w = _make_ranged_weapon(max_ammo=10)
        weapon_state = {"current_ammo": 10, "current_cool_down": 0}
        resources = sim.unit_resources[str(player.id)]

        sim._consume_attack_resources(ranged_w, weapon_state, resources)

        assert weapon_state["current_ammo"] == 9, "遠距離武器は弾薬を消費する"


# ---------------------------------------------------------------------------
# 4. 格闘コンボシステム (Phase C)
# ---------------------------------------------------------------------------


class TestMeleeCombo:
    """格闘コンボシステムの検証."""

    def test_no_combo_when_random_above_chance(self) -> None:
        """乱数がCOMBO_BASE_CHANCEより大きい場合はコンボなし."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0))
        sim = BattleSimulator(player, [enemy])

        melee_w = _make_melee_weapon(power=100)
        snapshot = player.position

        initial_hp = enemy.current_hp
        combo_logs_before = len(sim.logs)

        with patch("random.random", return_value=1.0):
            sim._process_melee_combo(player, enemy, melee_w, 100, snapshot)

        # コンボなし: HP変化なし、MELEE_COMBOログなし
        assert enemy.current_hp == initial_hp
        combo_logs = [l for l in sim.logs if l.action_type == "MELEE_COMBO"]
        assert len(combo_logs) == 0

    def test_single_combo_fires(self) -> None:
        """1回コンボが発生する（確率を制御）."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0), hp=10000)
        sim = BattleSimulator(player, [enemy])

        melee_w = _make_melee_weapon(power=100)
        snapshot = player.position
        initial_hp = enemy.current_hp

        # 1回目: コンボ発動(0 < 0.3)、2回目: コンボ失敗 (1.0 > 0.15)
        with patch("random.random", side_effect=[0.1, 1.0]):
            sim._process_melee_combo(player, enemy, melee_w, 100, snapshot)

        expected_combo_damage = int(100 * COMBO_DAMAGE_MULTIPLIER)
        assert enemy.current_hp == initial_hp - expected_combo_damage

        combo_logs = [l for l in sim.logs if l.action_type == "MELEE_COMBO"]
        assert len(combo_logs) == 1
        assert combo_logs[0].combo_count == 1
        assert "1Combo" in combo_logs[0].combo_message

    def test_max_combo_chain(self) -> None:
        """最大 COMBO_MAX_CHAIN 連コンボが発生する."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0), hp=100000)
        sim = BattleSimulator(player, [enemy])

        melee_w = _make_melee_weapon(power=100)
        snapshot = player.position
        initial_hp = enemy.current_hp

        # 全コンボ発動: 常に 0.0 を返す
        with patch("random.random", return_value=0.0):
            sim._process_melee_combo(player, enemy, melee_w, 100, snapshot)

        expected_combo_count = COMBO_MAX_CHAIN
        expected_total_damage = int(100 * COMBO_DAMAGE_MULTIPLIER) * expected_combo_count
        assert enemy.current_hp == initial_hp - expected_total_damage

        combo_logs = [l for l in sim.logs if l.action_type == "MELEE_COMBO"]
        assert len(combo_logs) == 1
        assert combo_logs[0].combo_count == COMBO_MAX_CHAIN
        assert f"{COMBO_MAX_CHAIN}Combo" in combo_logs[0].combo_message

    def test_combo_message_format(self) -> None:
        """コンボメッセージが正しい形式であること."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0), hp=10000)
        sim = BattleSimulator(player, [enemy])

        melee_w = _make_melee_weapon(power=100)
        snapshot = player.position

        with patch("random.random", side_effect=[0.1, 0.05, 1.0]):
            sim._process_melee_combo(player, enemy, melee_w, 100, snapshot)

        combo_logs = [l for l in sim.logs if l.action_type == "MELEE_COMBO"]
        assert len(combo_logs) == 1
        log = combo_logs[0]
        assert log.combo_count == 2
        # メッセージ形式: "2Combo Xダメージ!!"
        assert log.combo_message is not None
        assert "Combo" in log.combo_message
        assert "ダメージ" in log.combo_message

    def test_combo_destroys_target(self) -> None:
        """コンボでターゲットを撃破できる."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0), hp=50)
        sim = BattleSimulator(player, [enemy])

        melee_w = _make_melee_weapon(power=100)
        snapshot = player.position

        with patch("random.random", return_value=0.0):
            sim._process_melee_combo(player, enemy, melee_w, 100, snapshot)

        # 撃破ログが記録される
        destroyed_logs = [l for l in sim.logs if l.action_type == "DESTROYED"]
        assert len(destroyed_logs) >= 1

    def test_combo_stops_when_target_dead(self) -> None:
        """ターゲットが死亡するとコンボが止まる."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=10, y=0, z=0), hp=1)
        sim = BattleSimulator(player, [enemy])

        melee_w = _make_melee_weapon(power=200)
        snapshot = player.position
        enemy.current_hp = 1  # HP を1に設定（コンボ1回で撃破）

        with patch("random.random", return_value=0.0):
            sim._process_melee_combo(player, enemy, melee_w, 200, snapshot)

        # ターゲットが死亡しているので HP は 0
        assert enemy.current_hp == 0


# ---------------------------------------------------------------------------
# 5. 格闘命中後の再配置 (Phase C)
# ---------------------------------------------------------------------------


class TestProcessEngageMelee:
    """_process_engage_melee() の格闘後再配置テスト."""

    def test_post_melee_repositioning(self) -> None:
        """格闘命中後、攻撃者がターゲットから POST_MELEE_DISTANCE の位置に再配置される."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
                             weapons=[_make_melee_weapon()])
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=30, y=0, z=0), hp=10000)
        sim = BattleSimulator(player, [enemy])

        melee_w = _make_melee_weapon()
        pos_actor = player.position.to_numpy()

        # 命中を確実にする（乱数制御）
        with patch("random.random", return_value=0.0):
            sim._process_engage_melee(player, enemy, pos_actor, melee_w)

        # 格闘後の位置がターゲットから POST_MELEE_DISTANCE 以内/近く
        new_pos = player.position.to_numpy()
        enemy_pos = enemy.position.to_numpy()
        dist_after = float(np.linalg.norm(new_pos - enemy_pos))

        assert dist_after == pytest.approx(POST_MELEE_DISTANCE, rel=0.01)

    def test_post_melee_velocity_reset(self) -> None:
        """格闘命中後、速度ベクトルがゼロにリセットされる."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
                             weapons=[_make_melee_weapon()])
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=30, y=0, z=0), hp=10000)
        sim = BattleSimulator(player, [enemy])

        # 速度を設定
        unit_id = str(player.id)
        sim.unit_resources[unit_id]["velocity_vec"] = np.array([10.0, 0.0, 5.0])

        melee_w = _make_melee_weapon()
        pos_actor = player.position.to_numpy()

        with patch("random.random", return_value=0.0):
            sim._process_engage_melee(player, enemy, pos_actor, melee_w)

        velocity = sim.unit_resources[unit_id]["velocity_vec"]
        assert float(np.linalg.norm(velocity)) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 6. ファジィ入力変数の検証 (Phase C)
# ---------------------------------------------------------------------------


class TestFuzzyInputVariables:
    """新ファジィ入力変数 (ranged_ammo_ratio / los_blocked / boost_available) の検証."""

    def test_ranged_ammo_ratio_empty_triggers_engage_melee(self) -> None:
        """ranged_ammo_ratio == 0 (EMPTY) のとき ENGAGE_MELEE が高スコアになる."""
        from app.engine.fuzzy_engine import FuzzyEngine
        from app.engine.constants import FUZZY_RULES_DIR

        engine = FuzzyEngine.from_json(FUZZY_RULES_DIR / "assault.json")
        _, debug = engine.infer_with_debug({
            "hp_ratio": 1.0,
            "enemy_count_near": 1.0,
            "ally_count_near": 0.0,
            "distance_to_nearest_enemy": 200.0,
            "ranged_ammo_ratio": 0.0,  # EMPTY
            "los_blocked": 0.0,
            "boost_available": 0.0,
        })
        action_activations: dict[str, float] = debug.get("activations", {}).get("action", {})
        # ENGAGE_MELEE が高スコア（>= 0.5）であることを確認
        engage_melee_score = action_activations.get("ENGAGE_MELEE", 0.0)
        assert engage_melee_score >= 0.5, (
            f"弾切れ時は ENGAGE_MELEE が高スコアになるべき: {engage_melee_score} ({action_activations})"
        )
        # ENGAGE_MELEE が全スコアの最高値と同等であることを確認
        max_score = max(action_activations.values()) if action_activations else 0.0
        assert engage_melee_score >= max_score, (
            f"ENGAGE_MELEE は最高スコアと同等であるべき: {engage_melee_score} vs max {max_score}"
        )

    def test_hp_high_and_distance_melee_triggers_engage_melee(self) -> None:
        """hp_ratio IS HIGH AND distance IS MELEE 時に ENGAGE_MELEE が選択される."""
        from app.engine.fuzzy_engine import FuzzyEngine
        from app.engine.constants import FUZZY_RULES_DIR

        engine = FuzzyEngine.from_json(FUZZY_RULES_DIR / "aggressive.json")
        _, debug = engine.infer_with_debug({
            "hp_ratio": 1.0,
            "enemy_count_near": 1.0,
            "ally_count_near": 0.0,
            "distance_to_nearest_enemy": 20.0,  # MELEE 範囲
            "ranged_ammo_ratio": 1.0,
            "los_blocked": 0.0,
            "boost_available": 0.0,
        })
        action_activations: dict[str, float] = debug.get("activations", {}).get("action", {})
        # ENGAGE_MELEE が正のスコアを持つことを確認
        engage_melee_score = action_activations.get("ENGAGE_MELEE", 0.0)
        assert engage_melee_score > 0.0, (
            f"HP HIGH + MELEE 距離で ENGAGE_MELEE が正のスコアを持つべき: ({action_activations})"
        )
        # ENGAGE_MELEE が全スコアの最高値と同等であることを確認
        max_score = max(action_activations.values()) if action_activations else 0.0
        assert engage_melee_score >= max_score, (
            f"ENGAGE_MELEE は最高スコアと同等であるべき: {engage_melee_score} vs max {max_score}"
        )

    def test_los_blocked_and_boost_available_triggers_boost_dash(self) -> None:
        """los_blocked IS BLOCKED AND boost_available IS AVAILABLE 時に BOOST_DASH が選択される."""
        from app.engine.fuzzy_engine import FuzzyEngine
        from app.engine.constants import FUZZY_RULES_DIR

        engine = FuzzyEngine.from_json(FUZZY_RULES_DIR / "assault.json")
        _, debug = engine.infer_with_debug({
            "hp_ratio": 0.8,
            "enemy_count_near": 1.0,
            "ally_count_near": 0.0,
            "distance_to_nearest_enemy": 500.0,
            "ranged_ammo_ratio": 1.0,
            "los_blocked": 1.0,    # BLOCKED
            "boost_available": 1.0,  # AVAILABLE
        })
        action_activations: dict[str, float] = debug.get("activations", {}).get("action", {})
        # BOOST_DASH が正のスコアを持つことを確認
        boost_dash_score = action_activations.get("BOOST_DASH", 0.0)
        assert boost_dash_score > 0.0, (
            f"LOS閉塞+ブースト可能で BOOST_DASH が正のスコアを持つべき: ({action_activations})"
        )
        # BOOST_DASH が全スコアの最高値と同等であることを確認
        max_score = max(action_activations.values()) if action_activations else 0.0
        assert boost_dash_score >= max_score, (
            f"BOOST_DASH は最高スコアと同等であるべき: {boost_dash_score} vs max {max_score}"
        )

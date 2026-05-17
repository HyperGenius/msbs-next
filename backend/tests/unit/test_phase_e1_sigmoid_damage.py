"""Tests for Phase E-1: シグモイドダメージ計算式.

検証項目:
- _sigmoid_attack / _sigmoid_defense の値域・単調増加性
- _build_combat_multiplier_cache のキャッシュ初期化
- _calculate_hit_base_damage における新計算式の適用
- クリティカルヒット時の防御軽減率無視
- PilotStats に sht / mel フィールドが追加されていること
"""

import math
from unittest.mock import patch

import pytest

from app.engine.calculator import PilotStats
from app.engine.combat import _sigmoid_attack, _sigmoid_defense
from app.engine.constants import (
    ATTACK_SIGMOID_K,
    ATTACK_SIGMOID_MIDPOINT,
    DEFENSE_SIGMOID_K,
    DEFENSE_SIGMOID_MIDPOINT,
    MAX_ATTACK_BONUS,
    MAX_DEFENSE_REDUCTION,
)
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_weapon(power: int = 100, weapon_type: str = "RANGED") -> Weapon:
    return Weapon(
        id="w1",
        name="Test Weapon",
        power=power,
        range=500,
        accuracy=100,
        weapon_type=weapon_type,
        is_melee=(weapon_type == "MELEE"),
        cooldown_sec=0.0,
    )


def _make_unit(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    armor: int = 0,
    hp: int = 1000,
    weapons: list | None = None,
) -> MobileSuit:
    if weapons is None:
        weapons = [_make_weapon()]
    return MobileSuit(
        name=name,
        max_hp=hp,
        current_hp=hp,
        armor=armor,
        mobility=1.0,
        position=position,
        weapons=weapons,
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
    )


# ---------------------------------------------------------------------------
# 1. PilotStats の sht / mel フィールド
# ---------------------------------------------------------------------------


class TestPilotStatsShtMel:
    """PilotStats に sht / mel フィールドが追加されていることを検証する."""

    def test_default_sht_mel_are_zero(self) -> None:
        """デフォルト値はゼロ."""
        stats = PilotStats()
        assert stats.sht == 0
        assert stats.mel == 0

    def test_can_set_sht_mel(self) -> None:
        """sht / mel に値を設定できる."""
        stats = PilotStats(sht=20, mel=15)
        assert stats.sht == 20
        assert stats.mel == 15

    def test_existing_fields_still_work(self) -> None:
        """既存フィールド（dex/intel/ref/tou/luk）が引き続き動作する."""
        stats = PilotStats(dex=1, intel=2, ref=3, tou=4, luk=5, sht=6, mel=7)
        assert stats.dex == 1
        assert stats.intel == 2
        assert stats.ref == 3
        assert stats.tou == 4
        assert stats.luk == 5
        assert stats.sht == 6
        assert stats.mel == 7


# ---------------------------------------------------------------------------
# 2. シグモイドヘルパー関数
# ---------------------------------------------------------------------------


class TestSigmoidFunctions:
    """_sigmoid_attack / _sigmoid_defense の数値的性質を検証する."""

    def test_sigmoid_attack_range_within_max(self) -> None:
        """攻撃補正率は 0〜MAX_ATTACK_BONUS の範囲内."""
        for score in [-100, -50, 0, 50, 100, 200]:
            val = _sigmoid_attack(float(score))
            assert 0.0 < val < MAX_ATTACK_BONUS, f"score={score}, val={val}"

    def test_sigmoid_defense_range_within_max(self) -> None:
        """防御軽減率は 0〜MAX_DEFENSE_REDUCTION の範囲内."""
        for score in [-100, 0, 50, 100, 200, 500]:
            val = _sigmoid_defense(float(score))
            assert 0.0 < val < MAX_DEFENSE_REDUCTION, f"score={score}, val={val}"

    def test_sigmoid_attack_monotone_increasing(self) -> None:
        """合計攻撃力が増えるほど攻撃補正率が増加する."""
        scores = [0.0, 10.0, 30.0, 50.0, 80.0, 120.0]
        values = [_sigmoid_attack(s) for s in scores]
        for i in range(len(values) - 1):
            assert values[i] < values[i + 1], f"score={scores[i]}: {values[i]} >= {values[i+1]}"

    def test_sigmoid_defense_monotone_increasing(self) -> None:
        """合計防御力が増えるほど防御軽減率が増加する."""
        scores = [0.0, 50.0, 100.0, 150.0, 200.0]
        values = [_sigmoid_defense(s) for s in scores]
        for i in range(len(values) - 1):
            assert values[i] < values[i + 1], f"score={scores[i]}: {values[i]} >= {values[i+1]}"

    def test_sigmoid_attack_at_midpoint_is_half_max(self) -> None:
        """midpoint において補正率は MAX_ATTACK_BONUS / 2."""
        val = _sigmoid_attack(ATTACK_SIGMOID_MIDPOINT)
        assert val == pytest.approx(MAX_ATTACK_BONUS / 2.0, rel=1e-6)

    def test_sigmoid_defense_at_midpoint_is_half_max(self) -> None:
        """midpoint において軽減率は MAX_DEFENSE_REDUCTION / 2."""
        val = _sigmoid_defense(DEFENSE_SIGMOID_MIDPOINT)
        assert val == pytest.approx(MAX_DEFENSE_REDUCTION / 2.0, rel=1e-6)

    def test_sigmoid_attack_formula_matches_manual_calculation(self) -> None:
        """手計算と一致することを確認する."""
        score = 80.0
        expected = MAX_ATTACK_BONUS / (
            1.0 + math.exp(-ATTACK_SIGMOID_K * (score - ATTACK_SIGMOID_MIDPOINT))
        )
        assert _sigmoid_attack(score) == pytest.approx(expected)

    def test_sigmoid_defense_formula_matches_manual_calculation(self) -> None:
        """手計算と一致することを確認する."""
        score = 120.0
        expected = MAX_DEFENSE_REDUCTION / (
            1.0 + math.exp(-DEFENSE_SIGMOID_K * (score - DEFENSE_SIGMOID_MIDPOINT))
        )
        assert _sigmoid_defense(score) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# 3. _build_combat_multiplier_cache
# ---------------------------------------------------------------------------


class TestBuildCombatMultiplierCache:
    """_build_combat_multiplier_cache() がキャッシュを正しく初期化することを検証する."""

    def test_cache_keys_exist_in_unit_resources(self) -> None:
        """BattleSimulator 初期化後に全ユニットのキャッシュキーが存在する."""
        player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), armor=50)
        enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=200, y=0, z=0), armor=100)
        sim = BattleSimulator(player, [enemy])

        for unit in sim.units:
            uid = str(unit.id)
            resources = sim.unit_resources[uid]
            assert "cached_ranged_attack_bonus" in resources, f"unit={unit.name}"
            assert "cached_melee_attack_bonus" in resources, f"unit={unit.name}"
            assert "cached_defense_reduction" in resources, f"unit={unit.name}"

    def test_cached_values_are_floats_in_range(self) -> None:
        """キャッシュ値が正しい浮動小数点数の範囲にある."""
        player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), armor=80)
        enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=200, y=0, z=0), armor=200)
        sim = BattleSimulator(player, [enemy])

        for unit in sim.units:
            uid = str(unit.id)
            r = sim.unit_resources[uid]
            assert 0.0 < r["cached_ranged_attack_bonus"] < MAX_ATTACK_BONUS
            assert 0.0 < r["cached_melee_attack_bonus"] < MAX_ATTACK_BONUS
            assert 0.0 < r["cached_defense_reduction"] < MAX_DEFENSE_REDUCTION

    def test_high_armor_unit_has_higher_defense_reduction(self) -> None:
        """装甲値が高いユニットほど防御軽減率が高い."""
        player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), armor=50)
        enemy_low = _make_unit("E-low", "ENEMY", "ET", Vector3(x=200, y=0, z=0), armor=10)
        enemy_high = _make_unit("E-high", "ENEMY", "ET2", Vector3(x=300, y=0, z=0), armor=200)
        sim = BattleSimulator(player, [enemy_low, enemy_high])

        low_def = sim.unit_resources[str(enemy_low.id)]["cached_defense_reduction"]
        high_def = sim.unit_resources[str(enemy_high.id)]["cached_defense_reduction"]
        assert high_def > low_def

    def test_player_pilot_sht_increases_ranged_attack_bonus(self) -> None:
        """プレイヤーの SHT が高いほど射撃攻撃補正率が高い."""
        player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=200, y=0, z=0))

        sim_no_sht = BattleSimulator(
            player, [enemy], player_pilot_stats=PilotStats(sht=0)
        )
        sim_high_sht = BattleSimulator(
            player, [enemy], player_pilot_stats=PilotStats(sht=50)
        )

        bonus_no_sht = sim_no_sht.unit_resources[str(player.id)]["cached_ranged_attack_bonus"]
        bonus_high_sht = sim_high_sht.unit_resources[str(player.id)]["cached_ranged_attack_bonus"]
        assert bonus_high_sht > bonus_no_sht

    def test_player_pilot_mel_increases_melee_attack_bonus(self) -> None:
        """プレイヤーの MEL が高いほど格闘攻撃補正率が高い."""
        player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=200, y=0, z=0))

        sim_no_mel = BattleSimulator(
            player, [enemy], player_pilot_stats=PilotStats(mel=0)
        )
        sim_high_mel = BattleSimulator(
            player, [enemy], player_pilot_stats=PilotStats(mel=50)
        )

        bonus_no_mel = sim_no_mel.unit_resources[str(player.id)]["cached_melee_attack_bonus"]
        bonus_high_mel = sim_high_mel.unit_resources[str(player.id)]["cached_melee_attack_bonus"]
        assert bonus_high_mel > bonus_no_mel

    def test_player_pilot_tou_increases_defense_reduction(self) -> None:
        """プレイヤーの TOU が高いほど（合計防御力が高く）防御軽減率が高い."""
        player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), armor=50)
        enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=200, y=0, z=0))

        sim_no_tou = BattleSimulator(
            player, [enemy], player_pilot_stats=PilotStats(tou=0)
        )
        sim_high_tou = BattleSimulator(
            player, [enemy], player_pilot_stats=PilotStats(tou=50)
        )

        def_no_tou = sim_no_tou.unit_resources[str(player.id)]["cached_defense_reduction"]
        def_high_tou = sim_high_tou.unit_resources[str(player.id)]["cached_defense_reduction"]
        assert def_high_tou > def_no_tou


# ---------------------------------------------------------------------------
# 4. _calculate_hit_base_damage の新計算式
# ---------------------------------------------------------------------------


class TestCalculateHitBaseDamageNewFormula:
    """_calculate_hit_base_damage() が新シグモイド計算式を使用することを検証する."""

    def _make_sim_with_units(
        self,
        attacker_armor: int = 0,
        target_armor: int = 0,
        pilot_stats: PilotStats | None = None,
    ) -> tuple[BattleSimulator, MobileSuit, MobileSuit]:
        player = _make_unit(
            "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), armor=attacker_armor
        )
        enemy = _make_unit(
            "Enemy", "ENEMY", "ET", Vector3(x=50, y=0, z=0), armor=target_armor
        )
        sim = BattleSimulator(
            player, [enemy], player_pilot_stats=pilot_stats or PilotStats()
        )
        return sim, player, enemy

    def test_non_crit_uses_sigmoid_formula(self) -> None:
        """非クリティカル時に weapon.power × (1+bonus) × (1-reduction) を使う."""
        sim, player, enemy = self._make_sim_with_units(target_armor=100)
        weapon = _make_weapon(power=100)
        log_base = "Test"

        # 非クリティカルを強制
        with patch("app.engine.combat.random.random", return_value=1.0):
            base_damage, msg = sim._calculate_hit_base_damage(player, enemy, weapon, log_base)

        assert "命中" in msg
        # キャッシュ値から期待値を計算
        resources = sim.unit_resources[str(player.id)]
        attack_bonus = resources["cached_ranged_attack_bonus"]
        resources_target = sim.unit_resources[str(enemy.id)]
        defense_reduction = resources_target["cached_defense_reduction"]
        expected = max(1, int(100 * (1.0 + attack_bonus) * (1.0 - defense_reduction)))
        assert base_damage == expected

    def test_high_armor_unit_takes_at_least_half_damage(self) -> None:
        """極めて高い装甲値でも weapon.power の 50% 以上のダメージが通る（シグモイド上限 50%）."""
        sim, player, enemy = self._make_sim_with_units(target_armor=9999)
        weapon = _make_weapon(power=200)

        with patch("app.engine.combat.random.random", return_value=1.0):
            base_damage, _ = sim._calculate_hit_base_damage(player, enemy, weapon, "")

        # defense_reduction の上限は MAX_DEFENSE_REDUCTION = 0.50
        # よって damage >= weapon.power * (1 - 0.50) = 100 (attack_bonus により実際はさらに高い)
        assert base_damage >= 100

    def test_old_formula_was_zero_but_new_formula_is_not(self) -> None:
        """旧来の減算式でダメージが 1 に固定されるケースで新式はより高いダメージを返す."""
        # weapon.power=50, armor=200 → 旧式: max(1, 50-200) = 1
        sim, player, enemy = self._make_sim_with_units(target_armor=200)
        weapon = _make_weapon(power=50)

        with patch("app.engine.combat.random.random", return_value=1.0):
            base_damage, _ = sim._calculate_hit_base_damage(player, enemy, weapon, "")

        # 新式は必ず > 1
        assert base_damage > 1

    def test_crit_ignores_defense_reduction(self) -> None:
        """クリティカルヒット時は防御軽減率を無視（weapon.power * 1.2 のみ）."""
        sim, player, enemy = self._make_sim_with_units(target_armor=500)
        weapon = _make_weapon(power=100)

        # クリティカルを強制
        with patch("app.engine.combat.random.random", return_value=0.0):
            base_damage, msg = sim._calculate_hit_base_damage(player, enemy, weapon, "")

        assert "クリティカル" in msg
        assert base_damage == int(100 * 1.2)

    def test_melee_weapon_uses_melee_attack_bonus(self) -> None:
        """MELEE 武器は cached_melee_attack_bonus を使用する."""
        player = _make_unit(
            "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0),
            weapons=[_make_weapon(power=100, weapon_type="MELEE")]
        )
        enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=30, y=0, z=0))
        # MEL を高く設定
        sim = BattleSimulator(
            player, [enemy], player_pilot_stats=PilotStats(mel=80, sht=0)
        )

        # 射撃補正率と格闘補正率が異なることを確認
        resources = sim.unit_resources[str(player.id)]
        assert resources["cached_melee_attack_bonus"] != resources["cached_ranged_attack_bonus"]

        # 非クリティカルでメレー武器を使用
        melee_w = _make_weapon(power=100, weapon_type="MELEE")
        with patch("app.engine.combat.random.random", return_value=1.0):
            base_damage, _ = sim._calculate_hit_base_damage(player, enemy, melee_w, "")

        melee_bonus = resources["cached_melee_attack_bonus"]
        target_def = sim.unit_resources[str(enemy.id)]["cached_defense_reduction"]
        expected = max(1, int(100 * (1.0 + melee_bonus) * (1.0 - target_def)))
        assert base_damage == expected

    def test_damage_minimum_is_1(self) -> None:
        """どんな条件でもダメージは最低 1."""
        sim, player, enemy = self._make_sim_with_units(target_armor=99999)
        weapon = _make_weapon(power=1)

        with patch("app.engine.combat.random.random", return_value=1.0):
            base_damage, _ = sim._calculate_hit_base_damage(player, enemy, weapon, "")

        assert base_damage >= 1

    def test_higher_sht_produces_more_damage(self) -> None:
        """SHT が高いパイロットほど射撃ダメージが高い."""
        player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=50, y=0, z=0))
        weapon = _make_weapon(power=100)

        sim_low = BattleSimulator(
            player, [enemy], player_pilot_stats=PilotStats(sht=0)
        )
        sim_high = BattleSimulator(
            player, [enemy], player_pilot_stats=PilotStats(sht=80)
        )

        with patch("app.engine.combat.random.random", return_value=1.0):
            dmg_low, _ = sim_low._calculate_hit_base_damage(player, enemy, weapon, "")
            dmg_high, _ = sim_high._calculate_hit_base_damage(player, enemy, weapon, "")

        assert dmg_high > dmg_low


# ---------------------------------------------------------------------------
# 5. 後方互換 / 境界テスト
# ---------------------------------------------------------------------------


class TestSigmoidDamageCompat:
    """後方互換性・境界条件を検証する."""

    def test_zero_armor_zero_tou_gives_near_full_damage(self) -> None:
        """装甲 0・TOU 0 のとき防御軽減率はほぼ 0（旧式で armor=0 の場合と近似）."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=50, y=0, z=0), armor=0)
        sim = BattleSimulator(player, [enemy])

        # armor=0 のとき defense_reduction は非常に小さい
        def_reduction = sim.unit_resources[str(enemy.id)]["cached_defense_reduction"]
        assert def_reduction < 0.05  # 5% 未満

    def test_defense_reduction_max_50_percent(self) -> None:
        """防御軽減率の上限は 50%。armor=∞ でも damage は 50% 以上."""
        # sigmoid の漸近値は MAX_DEFENSE_REDUCTION = 0.50 なので
        # 現実的な armor 範囲では defense_reduction <= 0.50
        very_high_armor = 100000
        val = _sigmoid_defense(float(very_high_armor))
        assert val <= MAX_DEFENSE_REDUCTION

    def test_attack_bonus_max_50_percent(self) -> None:
        """攻撃補正率の上限は 50%。SHT=∞ でも bonus <= 0.50."""
        very_high_sht = 100000
        val = _sigmoid_attack(float(very_high_sht))
        assert val <= MAX_ATTACK_BONUS

    def test_unit_pilot_stats_dict_contains_player(self) -> None:
        """unit_pilot_stats に player の ID が含まれている."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=200, y=0, z=0))
        stats = PilotStats(sht=10, mel=5, tou=20)
        sim = BattleSimulator(player, [enemy], player_pilot_stats=stats)

        assert str(player.id) in sim.unit_pilot_stats
        assert sim.unit_pilot_stats[str(player.id)] is stats

    def test_enemy_not_in_unit_pilot_stats_gets_default(self) -> None:
        """NPC（未登録ユニット）は unit_pilot_stats に存在せずデフォルト PilotStats を使う."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=200, y=0, z=0))
        sim = BattleSimulator(player, [enemy])

        # enemy は unit_pilot_stats に存在しない（デフォルト PilotStats() が使われる）
        assert str(enemy.id) not in sim.unit_pilot_stats

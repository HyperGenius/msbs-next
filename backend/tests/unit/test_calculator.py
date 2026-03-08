"""Tests for the battle calculator module (app/engine/calculator.py)."""

import random

import pytest

from app.engine.calculator import (
    PilotStats,
    calculate_critical_chance,
    calculate_damage_variance,
    calculate_hit_chance,
    calculate_initiative,
)


@pytest.fixture(autouse=True)
def _restore_random_state():
    """各テスト後にグローバルな random 状態を復元する.

    random.seed() の呼び出しが後続テストの乱数列に影響しないよう保護する。
    """
    state = random.getstate()
    yield
    random.setstate(state)


# ---------------------------------------------------------------------------
# calculate_hit_chance
# ---------------------------------------------------------------------------


def test_calculate_hit_chance_zero_stats() -> None:
    """ステータスがゼロのとき、入力値をそのまま返す（後方互換性）."""
    result = calculate_hit_chance(70.0)
    assert result == 70.0


def test_calculate_hit_chance_clamp_upper() -> None:
    """100 を超えた命中率は 100 にクランプされる."""
    result = calculate_hit_chance(95.0, attacker_dex=20)
    assert result == 100.0


def test_calculate_hit_chance_clamp_lower() -> None:
    """0 未満の命中率は 0 にクランプされる."""
    result = calculate_hit_chance(5.0, defender_int=50)
    assert result == 0.0


def test_calculate_hit_chance_dex_increases_hit() -> None:
    """DEX が高いほど命中率が上がる."""
    base = 50.0
    result_low = calculate_hit_chance(base, attacker_dex=5)
    result_high = calculate_hit_chance(base, attacker_dex=10)
    assert result_high > result_low > base


def test_calculate_hit_chance_int_decreases_hit() -> None:
    """防御側の INT が高いほど命中率が下がる."""
    base = 70.0
    result = calculate_hit_chance(base, defender_int=10)
    assert result < base


def test_calculate_hit_chance_dex_reduces_distance_penalty() -> None:
    """DEX は距離減衰ペナルティを緩和する."""
    # distance_from_optimal=100, decay_rate=0.1 → penalty = 10
    # hit_chance がすでにペナルティを差し引いた後の値として渡す
    # DEX なし時: 60.0
    base = 60.0
    result_no_dex = calculate_hit_chance(
        base, distance_from_optimal=100.0, decay_rate=0.1, attacker_dex=0
    )
    result_with_dex = calculate_hit_chance(
        base, distance_from_optimal=100.0, decay_rate=0.1, attacker_dex=10
    )
    assert result_with_dex > result_no_dex


# ---------------------------------------------------------------------------
# calculate_critical_chance
# ---------------------------------------------------------------------------


def test_calculate_critical_chance_zero_stats() -> None:
    """ステータスがゼロのとき、入力値をそのまま返す（後方互換性）."""
    result = calculate_critical_chance(0.05)
    assert result == pytest.approx(0.05)


def test_calculate_critical_chance_int_increases_crit() -> None:
    """INT が高いほどクリティカル率が上がる."""
    base = 0.05
    result = calculate_critical_chance(base, attacker_int=10)
    assert result > base


def test_calculate_critical_chance_tou_decreases_crit() -> None:
    """防御側の TOU が高いほど被クリティカル率が下がる."""
    base = 0.05
    result = calculate_critical_chance(base, defender_tou=10)
    assert result < base


def test_calculate_critical_chance_clamp() -> None:
    """クランプ: 0.0〜1.0 の範囲に収まる."""
    # 非常に高い INT でも 1.0 を超えない
    assert calculate_critical_chance(0.9, attacker_int=100) == pytest.approx(1.0)
    # 非常に高い TOU でも 0.0 未満にならない
    assert calculate_critical_chance(0.01, defender_tou=100) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# calculate_damage_variance
# ---------------------------------------------------------------------------


def test_calculate_damage_variance_zero_stats_no_perfect_evade() -> None:
    """ステータスがゼロのとき、乱数変動のみ適用（完全回避なし）."""
    random.seed(42)
    damage, perfect_evade = calculate_damage_variance(100)
    assert not perfect_evade
    assert damage > 0


def test_calculate_damage_variance_tou_attacker_adds_damage() -> None:
    """攻撃側の TOU は基礎ダメージに固定値を加算する."""
    random.seed(0)
    base = 50
    damage_no_tou, _ = calculate_damage_variance(base, attacker_tou=0)
    random.seed(0)
    damage_with_tou, _ = calculate_damage_variance(base, attacker_tou=10)
    # TOU 10 の場合は 10 ポイント多くなる（乱数シードが同じなので差は TOU × variance）
    assert damage_with_tou > damage_no_tou


def test_calculate_damage_variance_tou_defender_reduces_damage() -> None:
    """防御側の TOU はダメージを軽減する."""
    random.seed(42)
    damage_no_tou, _ = calculate_damage_variance(50, attacker_tou=0, defender_tou=0)
    random.seed(42)
    damage_with_tou, _ = calculate_damage_variance(50, attacker_tou=0, defender_tou=10)
    assert damage_with_tou < damage_no_tou


def test_calculate_damage_variance_dex_cuts_damage() -> None:
    """防御側の DEX は最終ダメージを割合カットする."""
    random.seed(42)
    damage_no_dex, _ = calculate_damage_variance(100, defender_dex=0)
    random.seed(42)
    damage_with_dex, _ = calculate_damage_variance(100, defender_dex=20)
    assert damage_with_dex < damage_no_dex


def test_calculate_damage_variance_perfect_evade_triggered() -> None:
    """防御側の LUK が高い場合、完全回避が発動する（確率的）."""
    # LUK=50 → 5% の完全回避確率
    # 1000 回試行して少なくとも1回は発動する
    evaded = False
    for _ in range(1000):
        damage, perfect_evade = calculate_damage_variance(100, defender_luk=50)
        if perfect_evade:
            assert damage == 0
            evaded = True
            break
    assert evaded


def test_calculate_damage_variance_luk_biases_variance_up() -> None:
    """攻撃側の LUK は乱数を最大値方向に偏らせる（大量試行で平均が上がる）."""
    n = 1000
    random.seed(0)
    damages_no_luk = [
        calculate_damage_variance(100, attacker_luk=0)[0] for _ in range(n)
    ]
    random.seed(0)
    damages_high_luk = [
        calculate_damage_variance(100, attacker_luk=10)[0] for _ in range(n)
    ]
    avg_no_luk = sum(damages_no_luk) / n
    avg_high_luk = sum(damages_high_luk) / n
    assert avg_high_luk > avg_no_luk


# ---------------------------------------------------------------------------
# calculate_initiative
# ---------------------------------------------------------------------------


def test_calculate_initiative_zero_ref() -> None:
    """REF がゼロのとき、mobility をそのまま返す（後方互換性）."""
    result = calculate_initiative(2.0, ref_stat=0)
    assert result == pytest.approx(2.0)


def test_calculate_initiative_ref_increases_value() -> None:
    """REF が高いほどイニシアチブ値が上がる."""
    base_mobility = 2.0
    result_low = calculate_initiative(base_mobility, ref_stat=5)
    result_high = calculate_initiative(base_mobility, ref_stat=10)
    assert result_high > result_low > base_mobility


def test_calculate_initiative_ref_formula() -> None:
    """REF=10 の場合、mobility * 1.20 になる."""
    result = calculate_initiative(2.0, ref_stat=10)
    assert result == pytest.approx(2.0 * 1.20)


# ---------------------------------------------------------------------------
# PilotStats dataclass
# ---------------------------------------------------------------------------


def test_pilot_stats_defaults() -> None:
    """PilotStats のデフォルト値はすべてゼロ."""
    stats = PilotStats()
    assert stats.dex == 0
    assert stats.intel == 0
    assert stats.ref == 0
    assert stats.tou == 0
    assert stats.luk == 0


def test_pilot_stats_custom_values() -> None:
    """PilotStats に値を設定できる."""
    stats = PilotStats(dex=5, intel=3, ref=7, tou=2, luk=4)
    assert stats.dex == 5
    assert stats.intel == 3
    assert stats.ref == 7
    assert stats.tou == 2
    assert stats.luk == 4

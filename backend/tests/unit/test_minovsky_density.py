"""ミノフスキー濃度（連続値）による索敵・命中率補正のテスト (Issue #575)."""

from unittest.mock import patch

import numpy as np
import pytest

from app.engine.battle_utils import strip_debug_fields
from app.engine.constants import (
    DETECTION_FALLOFF_EXPONENT,
    DETECTION_FALLOFF_EXPONENT_MINOVSKY,
    SPECIAL_ENVIRONMENT_EFFECTS,
)
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon

# ---------------------------------------------------------------------------
# テストヘルパー
# ---------------------------------------------------------------------------


def _make_weapon(weapon_type: str = "RANGED", is_melee: bool = False) -> Weapon:
    return Weapon(
        id="test_weapon",
        name="Test Weapon",
        power=100,
        range=1000.0,
        accuracy=60,
        type="BEAM",
        weapon_type=weapon_type,
        is_melee=is_melee,
        optimal_range=300.0,
        decay_rate=0.01,
        cooldown_sec=0.0,
        max_ammo=999,
    )


def _make_unit(
    name: str,
    side: str,
    position: Vector3,
    sensor_range: float = 1000.0,
    weapon: Weapon | None = None,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=10000,
        current_hp=10000,
        armor=0,
        mobility=0.0,
        position=position,
        weapons=[weapon or _make_weapon()],
        side=side,
        team_id=f"{side}_TEAM",
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        max_speed=0.0,
        acceleration=0.0,
        sensor_range=sensor_range,
    )


def _make_sim(
    distance: float = 300.0,
    minovsky_density: float | None = None,
    special_effects: list[str] | None = None,
    weapon: Weapon | None = None,
) -> tuple[BattleSimulator, MobileSuit, MobileSuit]:
    """X軸上に distance だけ離れた 1対1 のシミュレーターを作る.

    ターゲットは背後（REAR）から撃たれる向きにして、命中率が上限に張り付かないようにする。
    """
    player = _make_unit("Player", "PLAYER", Vector3(x=0, y=0, z=0), weapon=weapon)
    enemy = _make_unit("Enemy", "ENEMY", Vector3(x=distance, y=0, z=0))
    sim = BattleSimulator(
        player,
        [enemy],
        special_effects=special_effects,
        minovsky_density=minovsky_density,
    )
    sim.unit_resources[str(enemy.id)]["body_heading_deg"] = 0.0
    return sim, player, enemy


# ---------------------------------------------------------------------------
# 濃度の決め方
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("minovsky_density", "special_effects", "expected"),
    [
        (None, None, 0.0),
        (None, ["MINOVSKY"], 1.0),
        (0.3, None, 0.3),
        (0.2, ["MINOVSKY"], 0.2),  # 引数の濃度が special_effects より優先される
        (-0.5, None, 0.0),
        (1.5, None, 1.0),
    ],
)
def test_minovsky_density_resolution(
    minovsky_density: float | None,
    special_effects: list[str] | None,
    expected: float,
) -> None:
    """引数 → special_effects → 0.0 の順で濃度が決まり、[0, 1] にクランプされる."""
    sim, _, _ = _make_sim(
        minovsky_density=minovsky_density, special_effects=special_effects
    )
    assert sim.minovsky_density == expected


# ---------------------------------------------------------------------------
# 索敵
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("m", "expected_multiplier", "expected_exponent"),
    [(0.0, 1.00, 2.0), (0.3, 0.85, 2.3), (0.6, 0.70, 2.6), (1.0, 0.50, 3.0)],
)
def test_detection_params_follow_density(
    m: float, expected_multiplier: float, expected_exponent: float
) -> None:
    """索敵範囲の倍率 1 − 0.5·m、減衰指数 2 + m になる."""
    sim, _, _ = _make_sim(minovsky_density=m)
    multiplier, exponent = sim._minovsky_detection_params()
    assert multiplier == pytest.approx(expected_multiplier)
    assert exponent == pytest.approx(expected_exponent)


def test_detection_params_without_minovsky_are_unchanged() -> None:
    """濃度 0.0 のとき、索敵パラメータは従来の通常環境と完全に一致する."""
    sim, _, _ = _make_sim()
    assert sim._minovsky_detection_params() == (1.0, DETECTION_FALLOFF_EXPONENT)


def test_detection_params_with_minovsky_effect_are_unchanged() -> None:
    """special_effects: ["MINOVSKY"] のとき、従来の MINOVSKY と同じ範囲・指数になる."""
    sim, _, _ = _make_sim(special_effects=["MINOVSKY"])
    assert sim._minovsky_detection_params() == (
        SPECIAL_ENVIRONMENT_EFFECTS["MINOVSKY"]["sensor_range_multiplier"],
        DETECTION_FALLOFF_EXPONENT_MINOVSKY,
    )


@pytest.mark.parametrize(("distance", "detected"), [(690.0, True), (710.0, False)])
def test_detection_range_shrinks_with_density(distance: float, detected: bool) -> None:
    """濃度 0.6 では索敵範囲 1000m が 700m に縮む."""
    sim, _, enemy = _make_sim(distance=distance, minovsky_density=0.6)
    with patch("app.engine.targeting.random.random", return_value=0.0):
        sim._detection_phase()
    assert (enemy.id in sim.team_detected_units["PLAYER_TEAM"]) is detected


def test_detection_probability_uses_density_exponent() -> None:
    """発見確率 P = 1 − (d / d_eff)^k が濃度に応じた k で計算される."""
    m = 0.6
    distance = 350.0
    sim, _, enemy = _make_sim(distance=distance, minovsky_density=m)
    expected_prob = 1.0 - (distance / 700.0) ** 2.6

    with patch(
        "app.engine.targeting.random.random", return_value=expected_prob - 0.001
    ):
        sim._detection_phase()
    assert enemy.id in sim.team_detected_units["PLAYER_TEAM"]

    sim2, _, enemy2 = _make_sim(distance=distance, minovsky_density=m)
    with patch(
        "app.engine.targeting.random.random", return_value=expected_prob + 0.001
    ):
        sim2._detection_phase()
    assert enemy2.id not in sim2.team_detected_units["PLAYER_TEAM"]


@pytest.mark.parametrize(("m", "is_dense"), [(0.3, False), (0.5, True), (1.0, True)])
def test_detection_log_mentions_dense_minovsky_above_threshold(
    m: float, is_dense: bool
) -> None:
    """濃度がしきい値 0.5 以上のときだけ「濃密なミノフスキー粒子の中、」の文言になる."""
    sim, _, _ = _make_sim(distance=100.0, minovsky_density=m)
    with patch("app.engine.targeting.random.random", return_value=0.0):
        sim._detection_phase()
    detection_logs = [log for log in sim.logs if log.action_type == "DETECTION"]
    assert detection_logs
    assert ("濃密なミノフスキー粒子の中、" in detection_logs[0].message) is is_dense


# ---------------------------------------------------------------------------
# 射撃の命中率
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("m", "distance", "expected"),
    [
        (0.0, 150.0, 1.00),
        (0.0, 600.0, 1.00),
        (0.3, 150.0, 0.97),
        (0.3, 300.0, 0.94),
        (0.3, 600.0, 0.88),
        (0.6, 150.0, 0.94),
        (0.6, 300.0, 0.88),
        (0.6, 600.0, 0.76),
        (1.0, 150.0, 0.90),
        (1.0, 300.0, 0.80),
        (1.0, 600.0, 0.60),
        (1.0, 1200.0, 0.60),  # 600m 以上は一定
    ],
)
def test_ranged_hit_multiplier_follows_density(
    m: float, distance: float, expected: float
) -> None:
    """射撃の命中率倍率が 1 − 0.4·m·min(1, d / 600m) になる."""
    sim, _, _ = _make_sim(minovsky_density=m)
    multiplier = sim._get_minovsky_hit_multiplier(_make_weapon(), distance)
    assert multiplier == pytest.approx(expected)


@pytest.mark.parametrize(
    "weapon",
    [_make_weapon(weapon_type="MELEE"), _make_weapon(is_melee=True)],
    ids=["weapon_type_melee", "is_melee_flag"],
)
def test_melee_weapon_is_not_affected(weapon: Weapon) -> None:
    """格闘武器の命中率倍率は濃度に関わらず 1.0."""
    sim, _, _ = _make_sim(minovsky_density=1.0)
    assert sim._get_minovsky_hit_multiplier(weapon, 600.0) == 1.0


def test_hit_chance_without_minovsky_is_unchanged() -> None:
    """濃度 0.0 を明示しても、指定しない場合と命中率が完全に一致する."""
    sim_default, player, enemy = _make_sim(distance=400.0)
    sim_zero, player0, enemy0 = _make_sim(distance=400.0, minovsky_density=0.0)
    weapon = _make_weapon()

    hit_default, _, _ = sim_default._calculate_hit_chance(player, enemy, weapon, 400.0)
    hit_zero, _, _ = sim_zero._calculate_hit_chance(player0, enemy0, weapon, 400.0)
    assert hit_zero == hit_default


def test_ranged_hit_chance_is_multiplied_by_density() -> None:
    """濃度 1.0・300m の射撃は、命中率が濃度 0.0 の 0.8 倍になる."""
    weapon = _make_weapon()
    sim0, player0, enemy0 = _make_sim(distance=300.0, minovsky_density=0.0)
    sim1, player1, enemy1 = _make_sim(distance=300.0, minovsky_density=1.0)

    hit0, _, _ = sim0._calculate_hit_chance(player0, enemy0, weapon, 300.0)
    hit1, _, _ = sim1._calculate_hit_chance(player1, enemy1, weapon, 300.0)
    assert 0.0 < hit0 < 100.0
    assert hit1 == pytest.approx(hit0 * 0.8)


def test_melee_hit_chance_is_not_affected_by_density() -> None:
    """格闘武器の命中率は濃度 1.0 でも変わらない."""
    weapon = _make_weapon(weapon_type="MELEE")
    sim0, player0, enemy0 = _make_sim(distance=50.0, minovsky_density=0.0)
    sim1, player1, enemy1 = _make_sim(distance=50.0, minovsky_density=1.0)

    hit0, _, _ = sim0._calculate_hit_chance(player0, enemy0, weapon, 50.0)
    hit1, _, _ = sim1._calculate_hit_chance(player1, enemy1, weapon, 50.0)
    assert hit1 == hit0


# ---------------------------------------------------------------------------
# 攻撃ログのデバッグ用フィールド
# ---------------------------------------------------------------------------


def _attack_once(sim: BattleSimulator, player: MobileSuit, enemy: MobileSuit) -> None:
    distance = float(
        np.linalg.norm(enemy.position.to_numpy() - player.position.to_numpy())
    )
    sim._process_attack(
        player, enemy, distance, player.position.to_numpy(), player.weapons[0]
    )


@pytest.mark.parametrize("roll", [0.0, 100.0], ids=["hit", "miss"])
def test_attack_log_records_minovsky_hit_multiplier(roll: float) -> None:
    """射撃の ATTACK / MISS ログにミノフスキーの命中率倍率が残る."""
    sim, player, enemy = _make_sim(distance=300.0, minovsky_density=1.0)
    with patch("app.engine.combat.random.uniform", return_value=roll):
        _attack_once(sim, player, enemy)

    attack_logs = [log for log in sim.logs if log.action_type in ("ATTACK", "MISS")]
    assert len(attack_logs) == 1
    assert attack_logs[0].minovsky_hit_multiplier == pytest.approx(0.8)


def test_attack_log_has_no_minovsky_multiplier_without_minovsky() -> None:
    """濃度 0.0 のとき、攻撃ログの倍率フィールドは None."""
    sim, player, enemy = _make_sim(distance=300.0)
    with patch("app.engine.combat.random.uniform", return_value=0.0):
        _attack_once(sim, player, enemy)

    attack_logs = [log for log in sim.logs if log.action_type in ("ATTACK", "MISS")]
    assert len(attack_logs) == 1
    assert attack_logs[0].minovsky_hit_multiplier is None


def test_strip_debug_fields_removes_minovsky_multiplier() -> None:
    """DB 保存用のログからはミノフスキーの命中率倍率が除去される."""
    sim, player, enemy = _make_sim(distance=300.0, minovsky_density=1.0)
    with patch("app.engine.combat.random.uniform", return_value=0.0):
        _attack_once(sim, player, enemy)

    stripped = strip_debug_fields(sim.logs)
    assert stripped
    assert all("minovsky_hit_multiplier" not in log for log in stripped)

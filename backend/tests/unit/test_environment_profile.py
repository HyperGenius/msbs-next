"""環境タイプの効果と地形適正による補正のテスト."""

import random
import uuid
from unittest.mock import patch

import numpy as np
import pytest

from app.engine.combat import _part_hit_rng
from app.engine.constants import (
    TERRAIN_ADAPTABILITY_HIT_BONUS,
    TERRAIN_ADAPTABILITY_MODIFIERS,
)
from app.engine.environment import EnvironmentProfile
from app.engine.simulation import BattleSimulator
from app.models.models import BattleField, MobileSuit, Vector3, Weapon

FOREST = EnvironmentProfile(
    environment_id="FOREST",
    sensor_range_multiplier=0.8,
    ranged_accuracy_penalty=0.2,
    ranged_penalty_ref_distance=400.0,
    default_obstacle_density="DENSE",
    default_terrain_grade="A",
)

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
    terrain_adaptability: dict[str, str] | None = None,
    weapon: Weapon | None = None,
) -> MobileSuit:
    unit = MobileSuit(
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
        max_speed=100.0,
        acceleration=0.0,
        sensor_range=1000.0,
    )
    if terrain_adaptability is not None:
        unit.terrain_adaptability = terrain_adaptability
    return unit


def _make_sim(
    distance: float = 300.0,
    environment_profile: EnvironmentProfile | None = None,
    player_terrain: dict[str, str] | None = None,
    enemy_terrain: dict[str, str] | None = None,
    weapon: Weapon | None = None,
    minovsky_density: float | None = None,
) -> tuple[BattleSimulator, MobileSuit, MobileSuit]:
    """X軸上に distance だけ離れた 1対1 のシミュレーターを作る.

    ターゲットは背後（REAR）から撃たれる向きにして、命中率が上限に張り付かないようにする。
    """
    player = _make_unit(
        "Player", "PLAYER", Vector3(x=0, y=0, z=0), player_terrain, weapon
    )
    enemy = _make_unit("Enemy", "ENEMY", Vector3(x=distance, y=0, z=0), enemy_terrain)
    sim = BattleSimulator(
        player,
        [enemy],
        environment_profile=environment_profile,
        minovsky_density=minovsky_density,
    )
    sim.unit_resources[str(enemy.id)]["body_heading_deg"] = 0.0
    return sim, player, enemy


# ---------------------------------------------------------------------------
# 索敵範囲
# ---------------------------------------------------------------------------


def _captured_effective_range(sim: BattleSimulator) -> float:
    captured: list[float] = []

    def _capture(unit, target, pos_unit, effective_sensor_range, falloff_exponent):
        captured.append(effective_sensor_range)

    with patch.object(sim, "_process_single_detection", side_effect=_capture):
        sim._detection_phase()
    return captured[0]


def test_sensor_range_multiplied_by_profile() -> None:
    """索敵範囲に環境タイプの倍率が掛かる."""
    sim, _, _ = _make_sim(environment_profile=FOREST)
    assert _captured_effective_range(sim) == pytest.approx(1000.0 * 0.8)


def test_sensor_range_multiplied_with_minovsky() -> None:
    """環境タイプの倍率はミノフスキーの倍率と掛け合わせる."""
    sim, _, _ = _make_sim(environment_profile=FOREST, minovsky_density=0.6)
    # ミノフスキー 0.6 の倍率は 1 − 0.5·0.6 = 0.7。
    assert _captured_effective_range(sim) == pytest.approx(1000.0 * 0.8 * 0.7)


def test_sensor_range_unchanged_without_profile() -> None:
    """プロファイルが無ければ索敵範囲は変わらない."""
    sim, _, _ = _make_sim()
    assert _captured_effective_range(sim) == pytest.approx(1000.0)


# ---------------------------------------------------------------------------
# 射撃の命中率
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("distance", "expected"),
    [(0.0, 1.0), (200.0, 0.9), (400.0, 0.8), (800.0, 0.8)],
)
def test_environment_hit_multiplier_by_distance(
    distance: float, expected: float
) -> None:
    """倍率は 1 − α·min(1, d / D) になり、基準距離以上で一定になる."""
    sim, _, _ = _make_sim(environment_profile=FOREST)
    assert sim._get_environment_hit_multiplier(
        _make_weapon(), distance
    ) == pytest.approx(expected)


@pytest.mark.parametrize(
    "weapon",
    [_make_weapon(weapon_type="MELEE"), _make_weapon(is_melee=True)],
)
def test_environment_hit_multiplier_skips_melee(weapon: Weapon) -> None:
    """格闘武器は射撃ペナルティの対象外."""
    sim, _, _ = _make_sim(environment_profile=FOREST)
    assert sim._get_environment_hit_multiplier(weapon, 400.0) == 1.0


def test_environment_hit_multiplier_without_profile() -> None:
    """プロファイルが無ければ倍率は 1.0."""
    sim, _, _ = _make_sim()
    assert sim._get_environment_hit_multiplier(_make_weapon(), 400.0) == 1.0


def test_hit_chance_reduced_in_forest() -> None:
    """森林では遠距離の射撃の命中率が倍率分だけ下がる."""
    base_sim, base_player, base_enemy = _make_sim(distance=400.0)
    forest_sim, forest_player, forest_enemy = _make_sim(
        distance=400.0, environment_profile=FOREST
    )
    weapon = base_player.weapons[0]
    base_hit, _, _ = base_sim._calculate_hit_chance(
        base_player, base_enemy, weapon, 400.0
    )
    forest_hit, _, _ = forest_sim._calculate_hit_chance(
        forest_player, forest_enemy, weapon, 400.0
    )
    assert 0.0 < base_hit < 100.0
    assert forest_hit == pytest.approx(base_hit * 0.8)


# ---------------------------------------------------------------------------
# 障害物密度
# ---------------------------------------------------------------------------


def test_obstacle_density_defaults_to_profile() -> None:
    """BattleField が密度を指定しないとき、環境タイプの既定値を使う."""
    player = _make_unit("Player", "PLAYER", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", Vector3(x=300, y=0, z=0))
    sim = BattleSimulator(
        player, [enemy], battlefield=BattleField(), environment_profile=FOREST
    )
    assert sim.battlefield.obstacle_density == "DENSE"


def test_obstacle_density_explicit_wins_over_profile() -> None:
    """戦域が密度を指定したときは、その値を使う."""
    player = _make_unit("Player", "PLAYER", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", Vector3(x=300, y=0, z=0))
    sim = BattleSimulator(
        player,
        [enemy],
        battlefield=BattleField(obstacle_density="NONE"),
        environment_profile=FOREST,
    )
    assert sim.battlefield.obstacle_density == "NONE"
    assert sim.obstacles == []


# ---------------------------------------------------------------------------
# 地形適正
# ---------------------------------------------------------------------------


def test_environment_id_comes_from_profile() -> None:
    """プロファイルの環境タイプIDを environment として使う."""
    sim, _, _ = _make_sim(environment_profile=FOREST)
    assert sim.environment == "FOREST"


@pytest.mark.parametrize("grade", ["S", "A", "B", "C", "D"])
def test_terrain_speed_modifier(grade: str) -> None:
    """速度の補正は地形適正ランクに応じて変わる."""
    sim, player, _ = _make_sim(
        environment_profile=FOREST, player_terrain={"FOREST": grade}
    )
    assert sim._get_terrain_modifier(player) == TERRAIN_ADAPTABILITY_MODIFIERS[grade]


def test_terrain_grade_falls_back_to_profile_default() -> None:
    """機体に環境のキーが無ければ、環境タイプの既定ランクを使う."""
    profile = EnvironmentProfile(environment_id="FOREST", default_terrain_grade="C")
    sim, player, _ = _make_sim(
        environment_profile=profile, player_terrain={"SPACE": "S"}
    )
    assert sim._get_terrain_grade(player) == "C"
    assert sim._get_terrain_modifier(player) == TERRAIN_ADAPTABILITY_MODIFIERS["C"]


def test_terrain_grade_falls_back_to_a_without_profile() -> None:
    """プロファイルが無ければ、キーが無いときのランクは A."""
    sim, player, _ = _make_sim(player_terrain={})
    assert sim._get_terrain_grade(player) == "A"


@pytest.mark.parametrize(
    ("attacker_grade", "defender_grade"),
    [("S", "A"), ("A", "C"), ("S", "D"), ("B", "S")],
)
def test_terrain_hit_bonus(attacker_grade: str, defender_grade: str) -> None:
    """命中率に 攻撃側の補正 − 防御側の補正 を加算する."""
    base_sim, base_player, base_enemy = _make_sim(
        environment_profile=FOREST,
        player_terrain={"FOREST": "A"},
        enemy_terrain={"FOREST": "A"},
    )
    sim, player, enemy = _make_sim(
        environment_profile=FOREST,
        player_terrain={"FOREST": attacker_grade},
        enemy_terrain={"FOREST": defender_grade},
    )
    weapon = player.weapons[0]
    base_hit, _, _ = base_sim._calculate_hit_chance(
        base_player, base_enemy, weapon, 300.0
    )
    hit, _, _ = sim._calculate_hit_chance(player, enemy, weapon, 300.0)
    expected_delta = (
        TERRAIN_ADAPTABILITY_HIT_BONUS[attacker_grade]
        - TERRAIN_ADAPTABILITY_HIT_BONUS[defender_grade]
    )
    assert hit == pytest.approx(base_hit + expected_delta)


# ---------------------------------------------------------------------------
# 回帰: プロファイルなし
# ---------------------------------------------------------------------------


def _run_seeded_battle(environment_profile: EnvironmentProfile | None) -> list:
    random.seed(576)
    np.random.seed(576)
    _part_hit_rng.seed(576)
    player = _make_unit("Player", "PLAYER", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", Vector3(x=600, y=0, z=0))
    # set の走査順が UUID で変わるため、ID も固定する。
    for index, unit in enumerate((player, enemy), start=1):
        unit.id = uuid.UUID(int=index)
        unit.acceleration = 30.0
    # 障害物・スポーン位置の生成はシードを取らない default_rng() を使うため固定する。
    with patch(
        "app.engine.simulation.np.random.default_rng",
        side_effect=lambda *_: np.random.Generator(np.random.PCG64(576)),
    ):
        sim = BattleSimulator(
            player,
            [enemy],
            battlefield=BattleField(),
            environment_profile=environment_profile,
        )
    for _ in range(500):
        if sim.is_finished:
            break
        sim.step()
    return [
        (log.timestamp, log.action_type, log.damage, log.message) for log in sim.logs
    ]


def test_no_profile_matches_neutral_profile() -> None:
    """プロファイルなしの戦闘は、効果なしのプロファイルと同じ結果になる."""
    neutral = EnvironmentProfile(
        environment_id="SPACE", default_obstacle_density="MEDIUM"
    )
    without_profile = _run_seeded_battle(None)
    assert any(action == "ATTACK" for _, action, _, _ in without_profile)
    assert without_profile == _run_seeded_battle(neutral)

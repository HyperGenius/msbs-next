"""小隊の陣形（後衛が前衛の後方に位置取る）のテスト."""

import numpy as np
import pytest

from app.engine.constants import (
    FORMATION_ATTRACTION_COEFF,
    FORMATION_MIN_GAP,
    FORMATION_VANGUARD_CONTACT_RANGE,
)
from app.engine.simulation import BattleSimulator
from app.engine.unit_roles import UnitAssignment
from app.models.models import MobileSuit, Obstacle, Vector3, Weapon
from app.services.battle_execution import seed_battle_rngs
from app.services.retreat_support_mission import build_retreat_support_mission

# 3 機のときのフィールドは 2000m 四方。境界の影響を受けない中央付近を使う。
_Z = 1000.0
# 狙撃機の目標交戦距離は 500m（射程 600m ÷ 1.2）、許容幅は 100m。
_SNIPER_DISTANCE = 500.0


def _melee_weapon() -> Weapon:
    return Weapon(
        id="saber",
        name="Saber",
        power=5,
        range=60,
        accuracy=80,
        weapon_type="MELEE",
        is_melee=True,
        fire_arc_deg=360,
    )


def _rifle() -> Weapon:
    return Weapon(
        id="long_rifle",
        name="Long Rifle",
        power=5,
        range=600,
        accuracy=80,
        optimal_range=_SNIPER_DISTANCE,
    )


def _make_unit(
    name: str, team_id: str, x: float, weapon: Weapon, mobility: float = 1.0
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=3000,
        current_hp=3000,
        armor=0,
        mobility=mobility,
        position=Vector3(x=x, y=0, z=_Z),
        weapons=[weapon],
        side="PLAYER" if team_id == "PT" else "ENEMY",
        team_id=team_id,
    )


def _setup(
    enemy_x: float = 300.0,
    vanguard_x: float = 1100.0,
    sniper_x: float = 900.0,
    sniper_squad: str = "SQ",
    with_squad: bool = True,
) -> tuple[BattleSimulator, MobileSuit, MobileSuit, MobileSuit]:
    """プレイヤー機 1 機と、前衛・狙撃の敵小隊を作る. 敵は x の小さい側にいる."""
    enemy = _make_unit("Enemy", "PT", enemy_x, _melee_weapon())
    vanguard = _make_unit("Vanguard", "ET", vanguard_x, _melee_weapon(), 1.5)
    sniper = _make_unit("Sniper", "ET", sniper_x, _rifle())
    assignments = (
        {
            str(vanguard.id): UnitAssignment(role="VANGUARD", squad_id="SQ"),
            str(sniper.id): UnitAssignment(role="SNIPER", squad_id=sniper_squad),
        }
        if with_squad
        else {}
    )
    sim = BattleSimulator(enemy, [vanguard, sniper], unit_assignments=assignments)
    return sim, enemy, vanguard, sniper


def _detect(sim: BattleSimulator, enemy: MobileSuit) -> None:
    sim.team_detected_units["ET"] = {enemy.id}


def _force(
    sim: BattleSimulator, sniper: MobileSuit, action: str = "MOVE"
) -> np.ndarray:
    engagement = sim._engagement_range(sniper, sniper.weapons[0])
    return sim._formation_force(sniper, sniper.position.to_numpy(), engagement, action)


# --- 陣形の位置 ---


def test_anchor_is_behind_vanguard_at_engagement_distance() -> None:
    """前衛が敵に近いとき、後衛は敵から目標交戦距離だけ離れた前衛の後方を目指す."""
    sim, enemy, vanguard, _ = _setup(vanguard_x=500.0)
    _detect(sim, enemy)

    anchor = sim._formation_anchor(sim._get_movement_grid(), vanguard, _SNIPER_DISTANCE)

    assert anchor is not None
    assert anchor.position[0] == pytest.approx(300.0 + _SNIPER_DISTANCE)
    assert anchor.position[2] == pytest.approx(_Z)


def test_anchor_keeps_min_gap_behind_far_vanguard() -> None:
    """前衛が敵から遠いとき、後衛は前衛の後方に最小の距離をあける."""
    sim, enemy, vanguard, _ = _setup(vanguard_x=1100.0)
    _detect(sim, enemy)

    anchor = sim._formation_anchor(sim._get_movement_grid(), vanguard, _SNIPER_DISTANCE)

    assert anchor is not None
    assert anchor.position[0] == pytest.approx(1100.0 + FORMATION_MIN_GAP)


def test_anchor_follows_vanguard_heading_without_detected_enemy() -> None:
    """索敵済みの敵がいなければ、前衛の胴体の向きの後方を目指す."""
    sim, _, vanguard, _ = _setup()
    sim.unit_resources[str(vanguard.id)]["body_heading_deg"] = 180.0

    anchor = sim._formation_anchor(sim._get_movement_grid(), vanguard, _SNIPER_DISTANCE)

    assert anchor is not None
    assert anchor.enemy_position is None
    assert anchor.position[0] == pytest.approx(1100.0 + FORMATION_MIN_GAP)


def test_anchor_is_none_while_vanguard_is_in_contact() -> None:
    """前衛が敵と接触しているあいだは、位置取りをしない."""
    sim, enemy, vanguard, _ = _setup(
        vanguard_x=300.0 + FORMATION_VANGUARD_CONTACT_RANGE / 2
    )
    _detect(sim, enemy)

    assert (
        sim._formation_anchor(sim._get_movement_grid(), vanguard, _SNIPER_DISTANCE)
        is None
    )


def test_anchor_stays_inside_map_bounds() -> None:
    """陣形の位置はマップ境界の内側に収める."""
    sim, enemy, vanguard, _ = _setup(vanguard_x=1900.0)
    _detect(sim, enemy)
    _, map_max = sim.map_bounds

    anchor = sim._formation_anchor(sim._get_movement_grid(), vanguard, _SNIPER_DISTANCE)

    assert anchor is not None
    assert anchor.position[0] < map_max


def test_anchor_is_moved_out_of_obstacle() -> None:
    """陣形の位置が障害物に掛かるときは、障害物の外へ移す."""
    sim, enemy, vanguard, _ = _setup(vanguard_x=500.0)
    _detect(sim, enemy)
    sim.obstacles = [
        Obstacle(
            obstacle_id="rock",
            position=Vector3(x=800.0, y=0, z=_Z),
            radius=50.0,
        )
    ]

    anchor = sim._formation_anchor(sim._get_movement_grid(), vanguard, _SNIPER_DISTANCE)

    assert anchor is not None
    distance = float(np.linalg.norm(anchor.position - np.array([800.0, 0.0, _Z])))
    assert distance >= 50.0


# --- 後衛への力 ---


def test_rear_ahead_of_vanguard_is_pulled_back() -> None:
    """前衛より前に出た狙撃機は、敵から離れる向き（前衛の後方）へ引かれる."""
    sim, enemy, _, sniper = _setup()
    _detect(sim, enemy)

    force = _force(sim, sniper)

    assert force[0] > 0.0
    assert float(np.linalg.norm(force)) == pytest.approx(FORMATION_ATTRACTION_COEFF)


def test_rear_inside_anchor_radius_is_not_pulled_toward_enemy() -> None:
    """陣形の位置より敵に近いときは、敵へ向かう力を出さずに回り込む."""
    sim, enemy, _, sniper = _setup(vanguard_x=500.0)
    _detect(sim, enemy)
    # 前衛と反対側の、敵から 450m の位置に置く。
    sniper.position = Vector3(x=300.0, y=0, z=_Z + 450.0)

    force = _force(sim, sniper, "ATTACK")
    to_enemy = enemy.position.to_numpy() - sniper.position.to_numpy()

    assert float(np.dot(force, to_enemy)) <= 1e-9
    assert float(np.linalg.norm(force)) > 0.0


def test_no_force_when_enemy_closes_in_on_rear() -> None:
    """敵に詰められた後衛は、位置取りより間合いの後退を優先する."""
    sim, enemy, _, sniper = _setup(sniper_x=600.0)
    _detect(sim, enemy)

    assert not np.any(_force(sim, sniper))


def test_no_force_while_fleeing() -> None:
    """逃走中の後衛は位置取りをしない."""
    sim, enemy, _, sniper = _setup()
    _detect(sim, enemy)
    sim.unit_resources[str(sniper.id)]["fleeing"] = True

    assert not np.any(_force(sim, sniper))


@pytest.mark.parametrize("action", ["RETREAT", "HIT_AND_AWAY", "DISENGAGE"])
def test_no_force_outside_attack_and_move(action: str) -> None:
    """攻撃・移動以外の行動では位置取りをしない."""
    sim, enemy, _, sniper = _setup()
    _detect(sim, enemy)

    assert not np.any(_force(sim, sniper, action))


def test_no_force_without_vanguard_in_squad() -> None:
    """同じ小隊に前衛がいなければ、今の振る舞いのまま."""
    sim, enemy, _, sniper = _setup(sniper_squad="OTHER")
    _detect(sim, enemy)

    assert not np.any(_force(sim, sniper))


def test_rear_returns_to_default_after_vanguard_is_destroyed() -> None:
    """前衛が撃破されると、同じステップの中でも位置取りをやめる."""
    sim, enemy, vanguard, sniper = _setup()
    _detect(sim, enemy)
    assert np.any(_force(sim, sniper))

    vanguard.current_hp = 0

    assert not np.any(_force(sim, sniper))


def test_rear_picks_remaining_vanguard_after_one_is_destroyed() -> None:
    """前衛が 2 機いる小隊では、残った前衛を基準に位置取りを決め直す."""
    enemy = _make_unit("Enemy", "PT", 300.0, _melee_weapon())
    near = _make_unit("Near", "ET", 1000.0, _melee_weapon())
    far = _make_unit("Far", "ET", 1500.0, _melee_weapon())
    sniper = _make_unit("Sniper", "ET", 1050.0, _rifle())
    sim = BattleSimulator(
        enemy,
        [near, far, sniper],
        unit_assignments={
            str(near.id): UnitAssignment(role="VANGUARD", squad_id="SQ"),
            str(far.id): UnitAssignment(role="VANGUARD", squad_id="SQ"),
            str(sniper.id): UnitAssignment(role="SNIPER", squad_id="SQ"),
        },
    )
    _detect(sim, enemy)
    # 近い前衛の後方（x=1100）は自機より後ろ、遠い前衛の後方（x=1600）はさらに後ろ。
    sniper.position = Vector3(x=1100.0, y=0, z=_Z)
    assert not np.any(np.abs(_force(sim, sniper)) > 1e-9)

    near.current_hp = 0

    assert _force(sim, sniper)[0] > 0.0


def test_units_without_squad_skip_formation() -> None:
    """小隊を持たないユニットだけの戦闘では、前衛の解決もしない."""
    sim, enemy, _, sniper = _setup(with_squad=False)
    _detect(sim, enemy)

    assert not np.any(_force(sim, sniper))
    for _ in range(5):
        sim.step()
    assert sim._squad_vanguards is None


# --- 戦闘での振る舞い ---


def test_sniper_stays_behind_vanguard_while_approaching() -> None:
    """前衛1機・狙撃1機の小隊で、狙撃機は前衛の後方を保ちながら撃つ."""
    seed_battle_rngs(1)
    sim, enemy, vanguard, sniper = _setup(vanguard_x=1600.0, sniper_x=1300.0)

    behind_steps = approach_steps = 0
    in_contact = False
    for _ in range(300):
        sim.step()
        pos_enemy = enemy.position.to_numpy()
        vanguard_dist = float(np.linalg.norm(vanguard.position.to_numpy() - pos_enemy))
        sniper_dist = float(np.linalg.norm(sniper.position.to_numpy() - pos_enemy))
        in_contact = in_contact or vanguard_dist < FORMATION_VANGUARD_CONTACT_RANGE
        if not in_contact and enemy.id in sim.team_detected_units.get("ET", set()):
            approach_steps += 1
            behind_steps += sniper_dist > vanguard_dist

    sniper_shots = [
        log
        for log in sim.logs
        if log.actor_id == sniper.id and log.action_type in ("ATTACK", "MISS")
    ]
    assert in_contact
    assert approach_steps > 0
    assert behind_steps / approach_steps >= 0.9
    assert sniper_shots


def test_retreat_support_pursuers_form_vanguard_and_sniper_squads() -> None:
    """撤退支援の追撃部隊は、格闘機と狙撃機で 1 小隊ずつ組む."""
    enemies = build_retreat_support_mission().enemy_unit_configs()

    squads: dict[str, list[str]] = {}
    for config in enemies:
        assert config.squad_id is not None
        squads.setdefault(config.squad_id, []).append(config.role or "")

    assert sorted(sorted(roles) for roles in squads.values()) == [
        ["SNIPER", "VANGUARD"],
        ["SNIPER", "VANGUARD"],
    ]

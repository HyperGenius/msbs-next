"""作戦マスターから作戦の戦闘を組み立てる処理のテスト."""

import pytest
from pydantic import ValidationError

from app.engine.objectives import (
    AnnihilationObjective,
    RetreatSupportObjective,
    build_objective,
)
from app.models.models import (
    MISSION_TEAM_ENEMY,
    MISSION_TEAM_PLAYER,
    BattleField,
    Mission,
    MissionLayout,
    MissionUnitConfig,
    MobileSuit,
    Vector3,
    Weapon,
)
from app.services.battle_execution import prepare_battle_units, run_battle
from app.services.mission_battle import (
    build_mission_battle,
    build_mission_unit,
    enemy_team_id,
)
from app.services.retreat_support_mission import build_retreat_support_mission
from app.services.theater_service import BattleConditions
from main import _build_enemies_from_config

# 既存の作戦マスター（scripts/seed/seed_missions.py）と同じ形の敵機
LEGACY_ENEMY = {
    "name": "ザクII #1",
    "max_hp": 80,
    "armor": 5,
    "mobility": 1.2,
    "position": {"x": 500, "y": -200, "z": 0},
    "terrain_adaptability": {
        "SPACE": "A",
        "GROUND": "B",
        "COLONY": "A",
        "UNDERWATER": "D",
    },
    "weapon": {
        "id": "zaku_mg_1",
        "name": "ザクマシンガン",
        "power": 15,
        "range": 400,
        "accuracy": 70,
        "type": "PHYSICAL",
        "optimal_range": 300.0,
        "decay_rate": 0.08,
        "max_ammo": 120,
        "en_cost": 0,
        "cool_down_turn": 0,
        "cooldown_sec": 0.3,
    },
}


def _player() -> MobileSuit:
    suit = MobileSuit(
        name="Hero",
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[Weapon(id="w1", name="Beam Rifle", power=100, range=500, accuracy=80)],
        side="PLAYER",
    )
    player, _ = prepare_battle_units(suit.model_dump(), [])
    return player


def _mission(**kwargs) -> Mission:  # type: ignore[no-untyped-def]
    fields = {
        "id": 7,
        "name": "撤退支援テスト",
        "environment": "GROUND",
        "enemy_config": {"enemies": [LEGACY_ENEMY]},
    }
    return Mission(**(fields | kwargs))


def test_legacy_mission_reads_as_annihilation() -> None:
    """作戦目標・友軍・配置の無い既存の作戦は、殲滅・友軍なし・既定の配置として読む."""
    mission = _mission()

    assert mission.objective_config().type == "ANNIHILATION"
    assert mission.ally_unit_configs() == []
    assert mission.layout_config() == MissionLayout()
    [enemy] = mission.enemy_unit_configs()
    assert enemy.name == "ザクII #1"
    assert enemy.role is None
    assert isinstance(
        build_objective(
            mission.objective_config().type, mission.objective_config().params
        ),
        AnnihilationObjective,
    )


def test_build_enemies_from_config_keeps_legacy_values() -> None:
    """ソロミッションの敵機は、共通化する前と同じ値で作る."""
    [enemy] = _build_enemies_from_config([LEGACY_ENEMY])

    assert enemy.name == "ザクII #1"
    assert (enemy.max_hp, enemy.current_hp, enemy.armor) == (80, 80, 5)
    assert enemy.mobility == 1.2
    assert enemy.position == Vector3(x=500, y=-200, z=0)
    assert enemy.terrain_adaptability["GROUND"] == "B"
    assert enemy.side == "ENEMY"
    [weapon] = enemy.weapons
    assert (weapon.id, weapon.name, weapon.power, weapon.range, weapon.accuracy) == (
        "zaku_mg_1",
        "ザクマシンガン",
        15,
        400,
        70,
    )
    # 共通化する前も、武器は id/name/power/range/accuracy 以外を既定値にしていた
    assert (
        weapon.optimal_range
        == Weapon(id="x", name="x", power=1, range=1, accuracy=1).optimal_range
    )


def test_build_enemies_from_config_uses_defaults() -> None:
    """項目を省略した敵機は既定値で作る."""
    [enemy] = _build_enemies_from_config([{}])

    assert (enemy.name, enemy.max_hp, enemy.armor) == ("ザクII", 80, 5)
    assert enemy.position == Vector3(x=500, y=0, z=0)
    assert enemy.weapons[0].power == 15


def test_mission_units_join_teams_with_roles() -> None:
    """友軍はプレイヤーのチーム、敵機は1つのチームに入り、ロールと小隊を割り当てる."""
    mission = _mission(
        allies_config=[{"name": "負傷機", "role": "WITHDRAW"}],
        enemy_config={
            "enemies": [
                {**LEGACY_ENEMY, "role": "VANGUARD", "squad_id": "alpha"},
                {**LEGACY_ENEMY, "name": "ザクII #2"},
            ]
        },
    )
    player = _player()

    setup = build_mission_battle(mission, [player], BattleConditions())

    ally, vanguard, plain = setup.mission_units
    assert (ally.side, ally.team_id) == ("PLAYER", player.team_id)
    assert vanguard.side == plain.side == "ENEMY"
    assert vanguard.team_id == plain.team_id == enemy_team_id(mission)
    assert setup.unit_assignments[str(ally.id)].role == "WITHDRAW"
    assert setup.unit_assignments[str(vanguard.id)].role == "VANGUARD"
    assert setup.unit_assignments[str(vanguard.id)].squad_id == "alpha"
    assert str(plain.id) not in setup.unit_assignments
    assert isinstance(setup.objective, AnnihilationObjective)


def test_other_players_join_first_player_team() -> None:
    """プレイヤーが複数いれば、全員を先頭のプレイヤーのチームに入れる."""
    first, second = _player(), _player()

    build_mission_battle(_mission(), [first, second], BattleConditions())

    assert second.team_id == first.team_id


def test_layout_maps_team_keys() -> None:
    """配置のチームのキーを、戦闘のチーム ID に置き換える."""
    mission = _mission(
        layout={
            "spawn_zones": [
                {
                    "team_id": MISSION_TEAM_PLAYER,
                    "center": {"x": 300, "y": 0, "z": 300},
                    "radius": 100,
                },
                {
                    "team_id": MISSION_TEAM_ENEMY,
                    "center": {"x": 1700, "y": 0, "z": 1700},
                    "radius": 150,
                },
            ],
            "retreat_points": [
                {
                    "position": {"x": 100, "y": 0, "z": 100},
                    "radius": 80,
                    "team_id": MISSION_TEAM_PLAYER,
                },
                {"position": {"x": 1000, "y": 0, "z": 1000}, "radius": 50},
            ],
        }
    )
    player = _player()
    conditions = BattleConditions(battlefield=BattleField(obstacle_density="DENSE"))

    setup = build_mission_battle(mission, [player], conditions)

    zones = {z.team_id: z for z in setup.conditions.battlefield.spawn_zones}
    assert zones[player.team_id].center == Vector3(x=300, y=0, z=300)
    assert zones[enemy_team_id(mission)].radius == 150
    # 戦域の障害物密度は残す
    assert setup.conditions.battlefield.obstacle_density == "DENSE"
    assert conditions.battlefield.spawn_zones == []
    own, shared = setup.retreat_points
    assert (own.team_id, own.radius) == (player.team_id, 80)
    assert shared.team_id is None


def test_environment_falls_back_to_mission_without_theater() -> None:
    """戦域の無い開催では作戦の環境で戦い、戦域があれば戦域の環境で戦う."""
    mission = _mission()

    without_theater = build_mission_battle(mission, [_player()], BattleConditions())
    with_theater = build_mission_battle(
        mission,
        [_player()],
        BattleConditions(theater_id="solomon", environment="SPACE"),
    )

    assert without_theater.conditions.environment == "GROUND"
    assert with_theater.conditions.environment == "SPACE"


def test_layout_rejects_unknown_team() -> None:
    """配置のチームは PLAYER か ENEMY だけ書ける."""
    with pytest.raises(ValidationError):
        MissionLayout.model_validate(
            {
                "retreat_points": [
                    {"position": {"x": 0, "y": 0, "z": 0}, "radius": 1, "team_id": "X"}
                ]
            }
        )


def test_unknown_role_and_objective_raise() -> None:
    """無いロールや作戦目標の種類は、組み立て時にエラーにする."""
    with pytest.raises(ValueError, match="unknown unit role"):
        build_mission_battle(
            _mission(allies_config=[{"role": "PILOT"}]),
            [_player()],
            BattleConditions(),
        )
    with pytest.raises(ValueError, match="unknown objective type"):
        build_mission_battle(
            _mission(objective={"type": "CAPTURE"}), [_player()], BattleConditions()
        )


def test_run_battle_passes_mission_setup_to_simulator() -> None:
    """作戦の撤退ポイント・ロール・目標を戦闘に渡す."""
    mission = _mission(
        allies_config=[{"name": "負傷機", "role": "WITHDRAW"}],
        layout={
            "retreat_points": [
                {
                    "position": {"x": 100, "y": 0, "z": 100},
                    "radius": 80,
                    "team_id": MISSION_TEAM_PLAYER,
                }
            ]
        },
    )
    player = _player()
    setup = build_mission_battle(mission, [player], BattleConditions())

    outcome = run_battle(
        player,
        setup.mission_units,
        setup.conditions,
        max_steps=1,
        objective=setup.objective,
        retreat_points=setup.retreat_points,
        unit_assignments=setup.unit_assignments,
    )

    simulator = outcome.simulator
    ally = setup.mission_units[0]
    assert simulator.retreat_points == setup.retreat_points
    assert simulator.unit_role(ally) == "WITHDRAW"
    assert ally.strategy_mode == "RETREAT"
    assert simulator.objective is setup.objective
    assert outcome.objective_result is not None


def test_retreat_support_mission_master_builds_a_battle() -> None:
    """撤退支援のマスターから、損傷した友軍・追撃部隊・専用の撤退ポイント・離脱目標を作る."""
    mission = build_retreat_support_mission()
    player = _player()
    player.team_id = "player-team"

    setup = build_mission_battle(mission, [player], BattleConditions())

    allies = [u for u in setup.mission_units if u.team_id == "player-team"]
    enemies = [u for u in setup.mission_units if u.team_id == enemy_team_id(mission)]
    assert len(allies) == 3
    assert len(enemies) == 4
    assert all(a.current_hp < a.max_hp for a in allies)
    assert all(setup.unit_assignments[str(a.id)].role == "WITHDRAW" for a in allies)
    assert "LEFT_ARM" not in allies[0].parts
    assert {setup.unit_assignments[str(e.id)].role for e in enemies} == {
        "VANGUARD",
        "SNIPER",
    }
    assert any(e.weapons[0].is_melee for e in enemies)
    [retreat_point] = setup.retreat_points
    assert retreat_point.team_id == "player-team"
    assert isinstance(setup.objective, RetreatSupportObjective)
    assert setup.objective.protected_unit_ids == {str(a.id) for a in allies}


def test_mission_unit_rejects_unknown_missing_part() -> None:
    """無い部位を欠損に書くと拒否する."""
    with pytest.raises(ValueError):
        build_mission_unit(MissionUnitConfig(missing_parts=["WING"]), "PLAYER")


def test_retreat_support_battle_runs_and_saves_progress() -> None:
    """撤退支援を最後まで実行すると、離脱数・友軍の数を含む結果が返る."""
    mission = build_retreat_support_mission()
    player = _player()
    player.team_id = "player-team"
    setup = build_mission_battle(mission, [player], BattleConditions())

    outcome = run_battle(
        player,
        setup.mission_units,
        setup.conditions,
        max_steps=3000,
        objective=setup.objective,
        retreat_points=setup.retreat_points,
        unit_assignments=setup.unit_assignments,
    )

    result = outcome.objective_result
    assert result is not None
    assert (result.required, result.total) == (2, 3)
    assert 0 <= result.progress <= 3
    assert outcome.player_win == result.is_success

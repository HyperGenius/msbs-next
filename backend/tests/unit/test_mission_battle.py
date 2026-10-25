"""作戦マスターから作戦の戦闘を組み立てる処理のテスト."""

import uuid

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.engine.constants import SHRINK_START_STEP
from app.engine.objectives import (
    AnnihilationObjective,
    RetreatSupportObjective,
    build_objective,
)
from app.engine.simulation import BattleSimulator
from app.models.models import (
    MISSION_TEAM_ENEMY,
    MISSION_TEAM_PLAYER,
    BattleField,
    MasterMobileSuit,
    Mission,
    MissionLayout,
    MissionUnitConfig,
    MobileSuit,
    Vector3,
    Weapon,
)
from app.services.battle_execution import prepare_battle_units, run_battle
from app.services.mission_battle import (
    MissionMasters,
    build_mission_battle,
    build_mission_unit,
    enemy_team_id,
)
from app.services.mission_master_loader import load_mission_masters
from app.services.retreat_support_mission import build_retreat_support_mission
from app.services.theater_service import BattleConditions
from main import _build_enemies_from_config
from scripts.master_data import (
    FIXTURE_DIR,
    MasterData,
    mission_masters_from_data,
    read_master_dir,
)

_FIXTURE_MASTERS: MasterData = read_master_dir(FIXTURE_DIR)

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


def _masters(mission: Mission) -> MissionMasters:
    return mission_masters_from_data(_FIXTURE_MASTERS, mission)


def _fixture_master(master_id: str) -> dict:
    return next(m for m in _FIXTURE_MASTERS["mobile_suits"] if m["id"] == master_id)


def _fixture_ace(ace_id: str) -> dict:
    return next(a for a in _FIXTURE_MASTERS["ace_pilots"] if a["id"] == ace_id)


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


def test_build_enemies_from_config_resolves_masters() -> None:
    """ソロミッションの敵機も機体マスターから作り、参照先が無ければ 500 にする."""
    mission = _mission(enemy_config={"enemies": [{"master_mobile_suit_id": "gouf"}]})

    [enemy] = _build_enemies_from_config(
        mission.enemy_config["enemies"], _masters(mission)
    )

    assert enemy.master_mobile_suit_id == "gouf"
    with pytest.raises(HTTPException) as excinfo:
        _build_enemies_from_config([{"master_mobile_suit_id": "no_such_suit"}])
    assert excinfo.value.status_code == 500


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


def test_mission_battlefield_has_no_area_shrink_and_uses_layout_field_size() -> None:
    """作戦ではエリア収縮を止める。配置にフィールドの辺長があれば、それを使う."""
    with_size = build_mission_battle(
        _mission(layout={"field_size": 3500}), [_player()], BattleConditions()
    )
    without_size = build_mission_battle(_mission(), [_player()], BattleConditions())

    assert with_size.conditions.battlefield.field_size == 3500
    assert with_size.conditions.battlefield.area_shrink is False
    assert without_size.conditions.battlefield.field_size is None
    assert without_size.conditions.battlefield.area_shrink is False


def test_simulator_uses_battlefield_field_size_without_shrink() -> None:
    """フィールドの辺長を指定すると、その大きさで戦い、収縮を止めると縮まない."""

    def bounds_after_shrink_start(area_shrink: bool) -> tuple[float, float]:
        # 決着すると収縮しないため、敵は倒れない HP にする。
        enemy = build_mission_unit(MissionUnitConfig(max_hp=100000), "ENEMY")
        enemy.position = Vector3(x=3400, y=0, z=3400)
        sim = BattleSimulator(
            _player(),
            [enemy],
            battlefield=BattleField(
                obstacle_density="NONE", field_size=3500, area_shrink=area_shrink
            ),
        )
        for _ in range(SHRINK_START_STEP + 1):
            sim.step()
        return sim.map_bounds

    assert bounds_after_shrink_start(False) == (0.0, 3500.0)
    assert bounds_after_shrink_start(True) != (0.0, 3500.0)


def test_mission_unit_max_speed_and_hold_fire() -> None:
    """作戦の機体の最高速度と、撃ち返さない設定を戦闘に渡す."""
    mission = _mission(
        allies_config=[
            {"name": "負傷機", "role": "WITHDRAW", "max_speed": 30, "hold_fire": True}
        ]
    )
    player = _player()

    setup = build_mission_battle(mission, [player], BattleConditions())

    [ally, enemy] = setup.mission_units
    assert ally.max_speed == 30
    assert enemy.max_speed == MobileSuit.model_fields["max_speed"].default
    assert setup.unit_assignments[str(ally.id)].hold_fire is True


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

    setup = build_mission_battle(
        mission, [player], BattleConditions(), masters=_masters(mission)
    )

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
    # 撤退機は撃ち返さず、追撃部隊より遅い。
    assert all(setup.unit_assignments[str(a.id)].hold_fire for a in allies)
    assert all(a.max_speed < e.max_speed for a in allies for e in enemies)
    # 配置はすべてフィールドの内側にある。
    field_size = setup.conditions.battlefield.field_size
    assert field_size is not None
    positions = [z.center for z in setup.conditions.battlefield.spawn_zones]
    for pos in [*positions, retreat_point.position]:
        assert 0 < pos.x < field_size and 0 < pos.z < field_size
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
    setup = build_mission_battle(
        mission, [player], BattleConditions(), masters=_masters(mission)
    )

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


def test_unit_id_namespace_fixes_mission_unit_ids() -> None:
    """名前空間を渡すと友軍・敵機の ID が作戦マスターでの位置で決まり、渡さなければ毎回変わる."""
    mission = build_retreat_support_mission()
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, "test")

    def ids(**kwargs) -> list[str]:  # type: ignore[no-untyped-def]
        player = _player()
        player.team_id = "player-team"
        setup = build_mission_battle(
            mission,
            [player],
            BattleConditions(),
            masters=_masters(mission),
            **kwargs,
        )
        assert set(setup.unit_assignments) <= {str(u.id) for u in setup.mission_units}
        return [str(u.id) for u in setup.mission_units]

    fixed = ids(unit_id_namespace=namespace)
    assert fixed == ids(unit_id_namespace=namespace)
    assert len(set(fixed)) == len(fixed)
    assert set(ids()).isdisjoint(ids())


def test_retreat_support_units_reference_masters() -> None:
    """撤退支援の友軍・敵機は機体マスターを参照し、直書きの値を持たない."""
    mission = build_retreat_support_mission()

    configs = [*mission.ally_unit_configs(), *mission.enemy_unit_configs()]
    assert all(c.master_mobile_suit_id is not None for c in configs)
    for raw in [*(mission.allies_config or []), *mission.enemy_config["enemies"]]:
        assert {"max_hp", "armor", "mobility", "weapon"}.isdisjoint(raw)


def test_master_unit_uses_master_specs_and_weapons() -> None:
    """機体マスター ID の機体は、機体マスターの性能・武器・地形適性で出る."""
    master = _fixture_master("gouf")
    mission = _mission(enemy_config={"enemies": [{"master_mobile_suit_id": "gouf"}]})

    setup = build_mission_battle(
        mission, [_player()], BattleConditions(), masters=_masters(mission)
    )

    [enemy] = setup.mission_units
    specs = master["specs"]
    assert enemy.name == master["name"]
    assert (enemy.max_hp, enemy.current_hp) == (specs["max_hp"], specs["max_hp"])
    assert (enemy.armor, enemy.mobility) == (specs["armor"], specs["mobility"])
    assert enemy.sensor_range == specs["sensor_range"]
    assert enemy.terrain_adaptability == specs["terrain_adaptability"]
    assert enemy.master_mobile_suit_id == "gouf"
    assert (
        enemy.weapon_slot_count
        == MasterMobileSuit.model_validate(master).weapon_slot_count
    )
    assert [(w.id, w.power, w.range) for w in enemy.weapons] == [
        (w["id"], w["power"], w["range"]) for w in specs["weapons"]
    ]
    # 武器マスターにある武器は、武器マスターの ID を持つ。
    weapon_ids = {w["id"] for w in _FIXTURE_MASTERS["weapons"]}
    for weapon in enemy.weapons:
        expected = weapon.id if weapon.id in weapon_ids else None
        assert weapon.master_weapon_id == expected
    assert not enemy.is_ace


def test_master_unit_overrides_name_hp_ratio_parts_and_role() -> None:
    """作戦側の表示名・開始時の HP の割合・欠損部位・ロール・小隊が効く."""
    mission = _mission(
        allies_config=[
            {
                "master_mobile_suit_id": "zaku_ii",
                "name": "撤退機 #1",
                "current_hp_ratio": 0.25,
                "missing_parts": ["LEFT_ARM"],
                "role": "WITHDRAW",
                "squad_id": "retreat",
            }
        ]
    )
    player = _player()

    setup = build_mission_battle(
        mission, [player], BattleConditions(), masters=_masters(mission)
    )

    ally = setup.mission_units[0]
    assert ally.name == "撤退機 #1"
    assert ally.current_hp == round(ally.max_hp * 0.25)
    assert ally.max_hp == _fixture_master("zaku_ii")["specs"]["max_hp"]
    assert "LEFT_ARM" in ally.missing_parts
    assert "LEFT_ARM" not in ally.parts
    for part in ally.parts.values():
        assert part.current_hp < part.max_hp
    assert ally.team_id == player.team_id
    assignment = setup.unit_assignments[str(ally.id)]
    assert (assignment.role, assignment.squad_id) == ("WITHDRAW", "retreat")


def test_hp_ratio_must_be_in_range_and_not_combined_with_current_hp() -> None:
    """開始時の HP の割合は 0 より大きく 1 以下で、current_hp とは併用できない."""
    for ratio in (0, -0.1, 1.5):
        with pytest.raises(ValidationError):
            MissionUnitConfig(current_hp_ratio=ratio)
    with pytest.raises(ValidationError):
        MissionUnitConfig(current_hp=10, current_hp_ratio=0.5)
    assert MissionUnitConfig(current_hp_ratio=1).current_hp_ratio == 1


def test_ace_unit_uses_ace_mobile_suit_and_pilot() -> None:
    """エース ID の敵機は、マッチングのエース機と同じ機体・パイロットで出る."""
    ace = _fixture_ace("ace_char_aznable")
    mission = _mission(
        enemy_config={"enemies": [{"ace_id": "ace_char_aznable", "role": "VANGUARD"}]}
    )

    setup = build_mission_battle(
        mission, [_player()], BattleConditions(), masters=_masters(mission)
    )

    [enemy] = setup.mission_units
    spec = ace["mobile_suit"]
    assert enemy.is_ace
    assert enemy.ace_id == "ace_char_aznable"
    assert enemy.name == spec["name"]
    assert enemy.pilot_name == ace["pilot_name"]
    assert enemy.personality == ace["personality"]
    assert (enemy.max_hp, enemy.armor) == (spec["max_hp"], spec["armor"])
    assert [w.id for w in enemy.weapons] == [w["id"] for w in spec["weapons"]]
    assert (enemy.bounty_exp, enemy.bounty_credits) == (
        ace["bounty_exp"],
        ace["bounty_credits"],
    )
    assert enemy.team_id == enemy_team_id(mission)


def test_ace_units_do_not_share_master_objects() -> None:
    """同じマスターから作ったエース機どうしで、武器と戦術を共有しない."""
    mission = _mission(enemy_config={"enemies": [{"ace_id": "ace_char_aznable"}]})
    masters = _masters(mission)
    [config] = mission.enemy_unit_configs()

    first = build_mission_unit(config, "ENEMY", masters=masters)
    second = build_mission_unit(config, "ENEMY", masters=masters)

    master_spec = masters.aces["ace_char_aznable"]["mobile_suit"]
    assert first.weapons[0] is not second.weapons[0]
    assert first.weapons[0] is not master_spec["weapons"][0]
    assert first.tactics is not master_spec["tactics"]


def test_ace_with_master_mobile_suit_swaps_only_the_mobile_suit() -> None:
    """エースに機体マスターを重ねると、機体だけが機体マスターになる."""
    ace = _fixture_ace("ace_char_aznable")
    master = _fixture_master("gelgoog")
    mission = _mission(
        enemy_config={
            "enemies": [
                {"ace_id": "ace_char_aznable", "master_mobile_suit_id": "gelgoog"}
            ]
        }
    )

    [enemy] = build_mission_battle(
        mission, [_player()], BattleConditions(), masters=_masters(mission)
    ).mission_units

    assert enemy.name == master["name"]
    assert enemy.max_hp == enemy.current_hp == master["specs"]["max_hp"]
    assert [w.id for w in enemy.weapons] == [
        w["id"] for w in master["specs"]["weapons"]
    ]
    assert enemy.master_mobile_suit_id == "gelgoog"
    assert enemy.is_ace
    assert enemy.pilot_name == ace["pilot_name"]
    assert enemy.personality == ace["personality"]
    assert enemy.tactics == ace["mobile_suit"]["tactics"]
    assert enemy.bounty_credits == ace["bounty_credits"]


def test_ace_cannot_be_an_ally() -> None:
    """エースは敵機にだけ置ける."""
    mission = _mission(allies_config=[{"ace_id": "ace_char_aznable"}])

    with pytest.raises(ValueError, match="ace must be an enemy"):
        build_mission_battle(
            mission, [_player()], BattleConditions(), masters=_masters(mission)
        )


def test_missing_reference_fails_to_build() -> None:
    """参照先のマスターが無いと、既定の機体にせず組み立てを失敗させる."""
    for enemy, message in (
        ({"master_mobile_suit_id": "no_such_suit"}, "unknown master mobile suit"),
        ({"ace_id": "no_such_ace"}, "unknown ace"),
    ):
        mission = _mission(enemy_config={"enemies": [enemy]})
        with pytest.raises(ValueError, match=message):
            build_mission_battle(
                mission, [_player()], BattleConditions(), masters=_masters(mission)
            )
    # マスターを渡さなければ、参照する機体は組み立てられない。
    with pytest.raises(ValueError, match="unknown master mobile suit"):
        build_mission_battle(
            build_retreat_support_mission(), [_player()], BattleConditions()
        )


def test_load_mission_masters_reads_referenced_rows(session) -> None:  # type: ignore[no-untyped-def]
    """DB から参照先だけを読み、JSON から読んだときと同じ機体を作る."""
    mission = _mission(
        enemy_config={
            "enemies": [
                {"master_mobile_suit_id": "gouf"},
                {"master_mobile_suit_id": "gouf"},
                {"ace_id": "ace_amuro_ray"},
                {"master_mobile_suit_id": "no_such_suit"},
            ]
        }
    )

    masters = load_mission_masters(session, mission)

    assert set(masters.mobile_suits) == {"gouf"}
    assert set(masters.aces) == {"ace_amuro_ray"}
    from_db = build_mission_unit(
        mission.enemy_unit_configs()[0], "ENEMY", masters=masters
    )
    from_json = build_mission_unit(
        mission.enemy_unit_configs()[0], "ENEMY", masters=_masters(mission)
    )
    assert from_db.model_dump(exclude={"id"}) == from_json.model_dump(exclude={"id"})

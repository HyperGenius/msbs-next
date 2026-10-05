"""battle_execution の単体テスト."""

import uuid

from app.engine.battle_utils import serialize_obstacles
from app.models.models import MobileSuit, Vector3, Weapon
from app.services.battle_execution import (
    alive_team_ids,
    build_result_view_fields,
    prepare_battle_units,
    resolve_team_id,
    run_battle,
    snapshot_to_mobile_suit,
)
from app.services.theater_service import BattleConditions


def _make_unit(name: str, team_id: str | None = None) -> MobileSuit:
    return MobileSuit(
        id=uuid.uuid4(),
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[Weapon(id="w1", name="Beam Rifle", power=100, range=500, accuracy=80)],
        side="PLAYER",
        team_id=team_id,
    )


def _snapshot(name: str, team_id: str | None = None) -> dict:
    return _make_unit(name, team_id).model_dump(mode="json")


# --- snapshot_to_mobile_suit ---


def test_snapshot_to_mobile_suit_restores_model_types() -> None:
    """JSON 由来のスナップショットから、モデルの型で機体を組み立てる."""
    snapshot = _snapshot("Hero")
    snapshot["pilot_name"] = "スナップショット固有のキー"
    expected_id = uuid.UUID(snapshot["id"])

    unit = snapshot_to_mobile_suit(snapshot)

    assert unit.id == expected_id
    assert isinstance(unit.position, Vector3)
    assert isinstance(unit.weapons[0], Weapon)
    assert unit.parts


def test_snapshot_to_mobile_suit_rewrites_given_snapshot() -> None:
    """渡したスナップショットの位置と武器をモデルの型に書き換える."""
    snapshot = _snapshot("Hero")

    snapshot_to_mobile_suit(snapshot)

    assert isinstance(snapshot["position"], Vector3)
    assert isinstance(snapshot["weapons"][0], Weapon)
    assert isinstance(snapshot["id"], uuid.UUID)


# --- チームの判定 ---


def test_resolve_team_id_falls_back_to_unit_id() -> None:
    """チーム未所属のユニットは、ユニット ID をチームとする."""
    solo = _make_unit("Solo")
    member = _make_unit("Member", team_id="team-a")

    assert resolve_team_id(solo) == str(solo.id)
    assert resolve_team_id(member) == "team-a"


def test_alive_team_ids_skips_destroyed_units() -> None:
    """HP が 0 のユニットのチームを含めない."""
    alive = _make_unit("Alive", team_id="team-a")
    destroyed = _make_unit("Destroyed", team_id="team-b")
    destroyed.current_hp = 0

    assert alive_team_ids([alive, destroyed]) == {"team-a"}


# --- prepare_battle_units ---


def test_prepare_battle_units_assigns_sides_and_teams() -> None:
    """先頭をプレイヤー機、残りを敵機にする."""
    player_snapshot = _snapshot("Hero")
    enemy_snapshots = [_snapshot("Rival", team_id="team-x"), _snapshot("NPC")]

    player, enemies = prepare_battle_units(player_snapshot, enemy_snapshots)

    assert player.name == "Hero"
    assert player.side == "PLAYER"
    assert player.team_id == str(player.id)
    assert [e.name for e in enemies] == ["Rival", "NPC"]
    assert {e.side for e in enemies} == {"ENEMY"}
    assert enemies[0].team_id == "team-x"
    assert enemies[1].team_id == str(enemies[1].id)


# --- run_battle ---


def test_run_battle_stops_at_max_steps() -> None:
    """決着しなくても `max_steps` で打ち切る."""
    player, enemies = prepare_battle_units(_snapshot("Hero"), [_snapshot("Enemy")])

    outcome = run_battle(player, enemies, max_steps=3)

    assert outcome.steps_used <= 3
    assert outcome.simulator.environment == "SPACE"


def test_run_battle_applies_conditions() -> None:
    """戦域の条件をシミュレーターに渡す."""
    player, enemies = prepare_battle_units(_snapshot("Hero"), [_snapshot("Enemy")])
    conditions = BattleConditions(environment="GROUND", minovsky_density=0.4)

    outcome = run_battle(player, enemies, conditions, max_steps=0)

    assert outcome.simulator.environment == "GROUND"
    assert outcome.simulator.minovsky_density == 0.4


def test_run_battle_judges_by_player_team() -> None:
    """プレイヤー機のチームが生き残っているかで勝敗を決める."""
    player, enemies = prepare_battle_units(
        _snapshot("Hero", team_id="team-a"),
        [_snapshot("Ally", team_id="team-a"), _snapshot("Enemy")],
    )
    player.current_hp = 0

    win = run_battle(player, enemies, max_steps=0)
    enemies[0].current_hp = 0
    lose = run_battle(player, enemies, max_steps=0)

    assert win.player_win is True
    assert lose.player_win is False
    assert win.steps_used == 0
    assert win.kills == 0


# --- build_result_view_fields ---


def test_build_result_view_fields_splits_player_and_enemies() -> None:
    """結果を受け取るユニットを player_info、残りを enemies_info にする."""
    player, enemies = prepare_battle_units(
        _snapshot("Hero"), [_snapshot("Rival"), _snapshot("NPC")]
    )
    simulator = run_battle(player, enemies, max_steps=0).simulator
    entry_unit = enemies[0].model_copy()

    fields = build_result_view_fields(entry_unit, [player, *enemies], simulator)

    assert fields["player_info"] == entry_unit.model_dump()
    assert [e["name"] for e in fields["enemies_info"]] == ["Hero", "NPC"]
    assert fields["obstacles_info"] == serialize_obstacles(simulator.obstacles)
    assert fields["map_bounds"] == list(simulator.map_bounds)

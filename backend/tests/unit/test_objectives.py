"""作戦目標の単体テスト."""

import uuid

from app.engine.objectives import (
    AnnihilationObjective,
    ObjectiveResult,
    ObjectiveStatus,
)
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


def _make_unit(name: str, team_id: str) -> MobileSuit:
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


def _resources(
    units: list[MobileSuit], statuses: dict[str, str] | None = None
) -> dict[str, dict[str, str]]:
    statuses = statuses or {}
    return {str(u.id): {"status": statuses.get(u.name, "ACTIVE")} for u in units}


# --- ObjectiveResult ---


def test_objective_result_is_success_only_for_success() -> None:
    """成功のときだけ `is_success` が真になる."""
    assert ObjectiveResult(ObjectiveStatus.SUCCESS).is_success is True
    assert ObjectiveResult(ObjectiveStatus.FAILURE).is_success is False
    assert ObjectiveResult(ObjectiveStatus.DRAW).is_success is False


# --- AnnihilationObjective.is_complete ---


def test_annihilation_continues_while_two_teams_are_active() -> None:
    """戦闘中のチームが 2 つ以上あれば終えない."""
    units = [_make_unit("A", "team-a"), _make_unit("B", "team-b")]

    assert AnnihilationObjective().is_complete(units, _resources(units)) is False


def test_annihilation_completes_when_one_team_remains() -> None:
    """戦闘中のチームが 1 つになったら終える."""
    a, b = _make_unit("A", "team-a"), _make_unit("B", "team-b")
    b.current_hp = 0
    units = [a, b]

    assert (
        AnnihilationObjective().is_complete(
            units, _resources(units, {"B": "DESTROYED"})
        )
        is True
    )


def test_annihilation_does_not_count_retreated_units_as_active() -> None:
    """撤退した機体は HP が残っていても戦闘中に数えない."""
    units = [_make_unit("A", "team-a"), _make_unit("B", "team-b")]

    assert (
        AnnihilationObjective().is_complete(
            units, _resources(units, {"B": "RETREATED"})
        )
        is True
    )


def test_annihilation_completes_when_no_team_remains() -> None:
    """戦闘中のチームが無くなっても終える."""
    units = [_make_unit("A", "team-a"), _make_unit("B", "team-b")]
    for unit in units:
        unit.current_hp = 0

    assert AnnihilationObjective().is_complete(units, _resources(units)) is True


# --- AnnihilationObjective.evaluate ---


def test_annihilation_succeeds_when_team_survives() -> None:
    """チームに HP の残る機体があれば成功とする."""
    a, ally, b = (
        _make_unit("A", "team-a"),
        _make_unit("Ally", "team-a"),
        _make_unit("B", "team-b"),
    )
    a.current_hp = 0
    b.current_hp = 0
    units = [a, ally, b]

    result = AnnihilationObjective().evaluate(units, _resources(units), "team-a")

    assert result.status == ObjectiveStatus.SUCCESS
    assert result.is_success is True


def test_annihilation_fails_when_team_is_destroyed() -> None:
    """チームの機体がすべて撃破されたら失敗とする."""
    a, b = _make_unit("A", "team-a"), _make_unit("B", "team-b")
    a.current_hp = 0
    units = [a, b]

    result = AnnihilationObjective().evaluate(units, _resources(units), "team-a")

    assert result.status == ObjectiveStatus.FAILURE


def test_annihilation_counts_retreated_units_as_survivors() -> None:
    """撤退した機体も生き残りに数える."""
    units = [_make_unit("A", "team-a"), _make_unit("B", "team-b")]
    resources = _resources(units, {"A": "RETREATED"})

    result = AnnihilationObjective().evaluate(units, resources, "team-a")

    assert result.is_success is True


def test_annihilation_succeeds_on_timeout_when_team_survives() -> None:
    """打ち切ったときも、生き残っていれば両チームとも成功とする."""
    units = [_make_unit("A", "team-a"), _make_unit("B", "team-b")]
    resources = _resources(units)
    objective = AnnihilationObjective()

    assert objective.is_complete(units, resources) is False
    assert objective.evaluate(units, resources, "team-a").is_success is True
    assert objective.evaluate(units, resources, "team-b").is_success is True


# --- BattleSimulator ---


def test_simulator_uses_annihilation_by_default() -> None:
    """作戦目標を渡さなければ殲滅を使う."""
    sim = BattleSimulator(_make_unit("A", "team-a"), [_make_unit("B", "team-b")])

    assert isinstance(sim.objective, AnnihilationObjective)


def test_simulator_finishes_when_objective_is_complete() -> None:
    """作戦目標が終了を求めれば、戦闘を終える."""

    class CompleteImmediately(AnnihilationObjective):
        def is_complete(self, units, unit_resources) -> bool:  # type: ignore[no-untyped-def]
            return True

    sim = BattleSimulator(
        _make_unit("A", "team-a"),
        [_make_unit("B", "team-b")],
        objective=CompleteImmediately(),
    )

    sim._check_objective_complete()

    assert sim.is_finished is True


def test_simulator_evaluates_objective_for_given_team() -> None:
    """指定したチームから見た結果を返す."""
    player, enemy = _make_unit("A", "team-a"), _make_unit("B", "team-b")
    sim = BattleSimulator(player, [enemy])
    enemy.current_hp = 0

    assert sim.evaluate_objective("team-a").is_success is True
    assert sim.evaluate_objective("team-b").is_success is False

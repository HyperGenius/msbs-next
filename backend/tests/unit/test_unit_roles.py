"""ユニットのロールと所属小隊の単体テスト."""

import pytest

from app.engine.simulation import BattleSimulator
from app.engine.strategy_controller import TeamMetrics, TeamStrategyController
from app.engine.unit_roles import UnitAssignment
from app.models.models import MobileSuit, RetreatPoint, Vector3, Weapon


def _make_unit(
    name: str,
    team_id: str,
    position: Vector3,
    hp: int = 1000,
    strategy_mode: str | None = None,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=hp,
        current_hp=hp,
        armor=0,
        mobility=1.0,
        position=position,
        weapons=[
            Weapon(id="rifle", name="Beam Rifle", power=20, range=500, accuracy=80)
        ],
        side="PLAYER",
        team_id=team_id,
        strategy_mode=strategy_mode,
    )


class _AlwaysDefensiveController(TeamStrategyController):
    def evaluate(self, team_metrics: TeamMetrics) -> str | None:
        return "DEFENSIVE"


def _withdraw(unit: MobileSuit, squad_id: str | None = None) -> dict:
    return {str(unit.id): UnitAssignment(role="WITHDRAW", squad_id=squad_id)}


# --- UnitAssignment ---


def test_assignment_rejects_unknown_role() -> None:
    """ロールの許容値に無い値は拒否する."""
    with pytest.raises(ValueError):
        UnitAssignment(role="RETREAT")


def test_assignment_accepts_no_role() -> None:
    """ロールなし・小隊だけの割り当てを作れる."""
    assert UnitAssignment(squad_id="SQ1").role is None


# --- BattleSimulator のロール・小隊 ---


def test_units_without_assignment_have_no_role_or_squad() -> None:
    """割り当ての無いユニットはロールも小隊も持たない."""
    player = _make_unit("Player", "TEAM_P", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "TEAM_E", Vector3(x=3000, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    assert sim.unit_role(player) is None
    assert sim.squad_id(player) is None


def test_simulator_returns_assigned_role_and_squad() -> None:
    """渡した割り当てのロールと小隊を返す."""
    player = _make_unit("Player", "TEAM_P", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "TEAM_E", Vector3(x=3000, y=0, z=0))
    sim = BattleSimulator(
        player,
        [enemy],
        unit_assignments={
            str(enemy.id): UnitAssignment(role="VANGUARD", squad_id="SQ1")
        },
    )

    assert sim.unit_role(enemy) == "VANGUARD"
    assert sim.squad_id(enemy) == "SQ1"
    assert not sim._is_withdrawing(enemy)


def test_withdraw_role_starts_in_retreat_mode() -> None:
    """撤退ポイントがあれば、撤退ロールは RETREAT で始まる."""
    player = _make_unit("Player", "TEAM_P", Vector3(x=0, y=0, z=0))
    ally = _make_unit("Ally", "TEAM_P", Vector3(x=0, y=0, z=200))
    enemy = _make_unit("Enemy", "TEAM_E", Vector3(x=3000, y=0, z=0))
    rp = RetreatPoint(position=Vector3(x=-1000, y=0, z=0), radius=100.0)
    sim = BattleSimulator(
        player, [ally, enemy], retreat_points=[rp], unit_assignments=_withdraw(ally)
    )

    assert sim._is_withdrawing(ally)
    assert ally.strategy_mode == "RETREAT"
    assert player.strategy_mode is None


def test_withdraw_role_is_ignored_without_retreat_points() -> None:
    """撤退ポイントが無い戦場では、撤退ロールを無視する."""
    player = _make_unit("Player", "TEAM_P", Vector3(x=0, y=0, z=0))
    ally = _make_unit("Ally", "TEAM_P", Vector3(x=0, y=0, z=200))
    enemy = _make_unit("Enemy", "TEAM_E", Vector3(x=3000, y=0, z=0))
    sim = BattleSimulator(player, [ally, enemy], unit_assignments=_withdraw(ally))

    assert not sim._is_withdrawing(ally)
    assert ally.strategy_mode is None


def test_withdraw_role_is_ignored_with_other_teams_retreat_point() -> None:
    """他チーム専用の撤退ポイントしか無いときも、撤退ロールを無視する."""
    player = _make_unit("Player", "TEAM_P", Vector3(x=0, y=0, z=0))
    ally = _make_unit("Ally", "TEAM_P", Vector3(x=0, y=0, z=200))
    enemy = _make_unit("Enemy", "TEAM_E", Vector3(x=3000, y=0, z=0))
    rp = RetreatPoint(
        position=Vector3(x=-1000, y=0, z=0), radius=100.0, team_id="TEAM_E"
    )
    sim = BattleSimulator(
        player, [ally, enemy], retreat_points=[rp], unit_assignments=_withdraw(ally)
    )

    assert not sim._is_withdrawing(ally)


def test_strategy_change_skips_withdraw_role() -> None:
    """チームの戦略が変わっても、撤退ロールは RETREAT のままにする."""
    player = _make_unit("Player", "TEAM_P", Vector3(x=0, y=0, z=0))
    ally = _make_unit("Ally", "TEAM_P", Vector3(x=0, y=0, z=200))
    enemy = _make_unit("Enemy", "TEAM_E", Vector3(x=3000, y=0, z=0))
    rp = RetreatPoint(position=Vector3(x=-1000, y=0, z=0), radius=100.0)
    sim = BattleSimulator(
        player,
        [ally, enemy],
        retreat_points=[rp],
        strategy_update_interval=1,
        unit_assignments=_withdraw(ally),
    )
    sim._strategy_controllers["TEAM_P"] = _AlwaysDefensiveController(
        team_id="TEAM_P", initial_strategy="AGGRESSIVE", update_interval=1
    )

    sim._strategy_phase()

    assert player.strategy_mode == "DEFENSIVE"
    assert ally.strategy_mode == "RETREAT"


def test_strategy_change_applies_to_withdraw_role_without_retreat_points() -> None:
    """撤退ポイントが無ければ、撤退ロールにもチームの戦略を適用する."""
    player = _make_unit("Player", "TEAM_P", Vector3(x=0, y=0, z=0))
    ally = _make_unit("Ally", "TEAM_P", Vector3(x=0, y=0, z=200))
    enemy = _make_unit("Enemy", "TEAM_E", Vector3(x=3000, y=0, z=0))
    sim = BattleSimulator(
        player,
        [ally, enemy],
        strategy_update_interval=1,
        unit_assignments=_withdraw(ally),
    )
    sim._strategy_controllers["TEAM_P"] = _AlwaysDefensiveController(
        team_id="TEAM_P", initial_strategy="AGGRESSIVE", update_interval=1
    )

    sim._strategy_phase()

    assert ally.strategy_mode == "DEFENSIVE"


# --- 撤退ロールの行動 ---


def test_withdraw_role_chooses_retreat_without_detected_enemies() -> None:
    """索敵済みの敵がいなくても、撤退ロールは RETREAT を選ぶ."""
    player = _make_unit("Player", "TEAM_P", Vector3(x=0, y=0, z=0))
    ally = _make_unit("Ally", "TEAM_P", Vector3(x=0, y=0, z=200))
    enemy = _make_unit("Enemy", "TEAM_E", Vector3(x=3000, y=0, z=0))
    rp = RetreatPoint(position=Vector3(x=-1000, y=0, z=0), radius=100.0)
    sim = BattleSimulator(
        player, [ally, enemy], retreat_points=[rp], unit_assignments=_withdraw(ally)
    )

    sim._ai_decision_phase(ally)
    sim._ai_decision_phase(player)

    assert sim.unit_resources[str(ally.id)]["current_action"] == "RETREAT"
    assert sim.unit_resources[str(player.id)]["current_action"] == "MOVE"


def test_withdraw_role_reaches_retreat_point_while_team_is_aggressive() -> None:
    """チームが AGGRESSIVE のままでも、撤退ロールは撤退ポイントで離脱する."""
    player = _make_unit(
        "Player", "TEAM_P", Vector3(x=0, y=0, z=0), strategy_mode="AGGRESSIVE"
    )
    ally = _make_unit("Ally", "TEAM_P", Vector3(x=0, y=0, z=200))
    enemy = _make_unit("Enemy", "TEAM_E", Vector3(x=3000, y=0, z=0))
    rp = RetreatPoint(position=Vector3(x=-600, y=0, z=200), radius=100.0)
    sim = BattleSimulator(
        player, [ally, enemy], retreat_points=[rp], unit_assignments=_withdraw(ally)
    )

    for _ in range(1000):
        if sim.unit_resources[str(ally.id)]["status"] == "RETREATED":
            break
        sim.step()

    assert sim.unit_resources[str(ally.id)]["status"] == "RETREATED"
    assert sim.unit_resources[str(player.id)]["status"] == "ACTIVE"
    assert sim._strategy_controllers["TEAM_P"].current_strategy == "AGGRESSIVE"
    assert any(
        log.action_type == "RETREAT_COMPLETE" and log.actor_id == ally.id
        for log in sim.logs
    )


def test_withdraw_role_fires_back_without_chasing() -> None:
    """撤退ロールは射程内の敵に撃ち返すが、敵へは寄らない."""
    player = _make_unit("Player", "TEAM_P", Vector3(x=-300, y=0, z=0))
    enemy = _make_unit("Enemy", "TEAM_E", Vector3(x=100, y=0, z=0), hp=100000)
    rp = RetreatPoint(position=Vector3(x=-3000, y=0, z=0), radius=100.0)
    sim = BattleSimulator(
        player, [enemy], retreat_points=[rp], unit_assignments=_withdraw(player)
    )
    for _ in range(50):
        sim.step()

    assert any(
        log.action_type in ("ATTACK", "MISS") and log.actor_id == player.id
        for log in sim.logs
    )
    assert not any(
        log.action_type == "MELEE_COMBO" and log.actor_id == player.id
        for log in sim.logs
    )
    assert player.position.x < -300


def test_withdraw_role_with_hold_fire_does_not_fire_back() -> None:
    """撃ち返さない設定の撤退ロールは、射程内の敵を撃たず、敵の方を向かない."""
    player = _make_unit("Player", "TEAM_P", Vector3(x=-300, y=0, z=0))
    enemy = _make_unit("Enemy", "TEAM_E", Vector3(x=100, y=0, z=0), hp=100000)
    rp = RetreatPoint(position=Vector3(x=-3000, y=0, z=0), radius=100.0)
    sim = BattleSimulator(
        player,
        [enemy],
        retreat_points=[rp],
        unit_assignments={
            str(player.id): UnitAssignment(role="WITHDRAW", hold_fire=True)
        },
    )
    for _ in range(50):
        sim.step()

    assert not any(
        log.action_type in ("ATTACK", "MISS") and log.actor_id == player.id
        for log in sim.logs
    )
    assert player.position.x < -300
    # 撤退ポイント（-x 方向）を向いたまま動く。
    heading = sim.unit_resources[str(player.id)]["body_heading_deg"] % 360
    assert abs(heading - 180) < 30


def test_hold_fire_is_ignored_without_withdraw_role() -> None:
    """撃ち返さない設定は撤退ロールにだけ効く."""
    player = _make_unit("Player", "TEAM_P", Vector3(x=-300, y=0, z=0))
    enemy = _make_unit("Enemy", "TEAM_E", Vector3(x=100, y=0, z=0), hp=100000)
    sim = BattleSimulator(
        player,
        [enemy],
        unit_assignments={str(player.id): UnitAssignment(hold_fire=True)},
    )
    for _ in range(50):
        sim.step()

    assert any(
        log.action_type in ("ATTACK", "MISS") and log.actor_id == player.id
        for log in sim.logs
    )

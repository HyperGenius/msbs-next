"""支援ターゲット選択（tactics.priority の SUPPORT / PROTECT）のテスト."""

import pytest

from app.core.npc_data import build_npc_tactics
from app.engine.constants import SUPPORT_THREAT_WINDOW_SEC
from app.engine.simulation import BattleSimulator
from app.engine.unit_roles import UnitAssignment
from app.models.models import MobileSuit, Vector3, Weapon
from app.services.mobile_suit_service import validate_tactics

_Z = 1000.0


def _rifle() -> Weapon:
    return Weapon(id="rifle", name="Rifle", power=5, range=600, accuracy=80)


def _unit(name: str, team_id: str, x: float, priority: str = "CLOSEST") -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=3000,
        current_hp=3000,
        armor=0,
        mobility=1.0,
        position=Vector3(x=x, y=0, z=_Z),
        weapons=[_rifle()],
        side="PLAYER" if team_id == "PT" else "ENEMY",
        team_id=team_id,
        tactics={"priority": priority, "range": "BALANCED"},
    )


def _setup(
    priority: str = "SUPPORT",
) -> tuple[BattleSimulator, MobileSuit, MobileSuit, MobileSuit, MobileSuit]:
    """敵チーム（x 小）の近い敵と遠い敵、味方チームの前衛と狙撃機を作る.

    near は狙撃機に近い敵、far は狙撃機から遠く前衛と交戦している敵。
    """
    near = _unit("Near", "PT", 700.0)
    far = _unit("Far", "PT", 300.0)
    vanguard = _unit("Vanguard", "ET", 1000.0)
    sniper = _unit("Sniper", "ET", 1100.0, priority)
    assignments = {
        str(vanguard.id): UnitAssignment(role="VANGUARD", squad_id="SQ"),
        str(sniper.id): UnitAssignment(role="SNIPER", squad_id="SQ"),
    }
    sim = BattleSimulator(near, [far, vanguard, sniper], unit_assignments=assignments)
    sim.team_detected_units["ET"] = {near.id, far.id}
    return sim, near, far, vanguard, sniper


def _attack(sim: BattleSimulator, attacker: MobileSuit, victim: MobileSuit) -> None:
    sim._record_attack_exchange(attacker, victim, 10)


@pytest.mark.parametrize("select", ["_select_target_legacy", "_select_target_fuzzy"])
def test_support_prefers_enemy_attacking_squadmate(select: str) -> None:
    """前衛を攻撃している敵を、近くにいる別の敵より優先して狙う."""
    sim, near, far, vanguard, sniper = _setup("SUPPORT")
    _attack(sim, far, vanguard)

    assert getattr(sim, select)(sniper) is far


def test_closest_ignores_attacks_on_allies() -> None:
    """SUPPORT でない機体は、味方への攻撃を見ずに選ぶ（従来どおり）."""
    sim, near, far, vanguard, sniper = _setup("CLOSEST")
    _attack(sim, far, vanguard)

    assert sim._select_target_legacy(sniper) is near


def test_support_falls_back_without_threat() -> None:
    """味方を攻撃している敵がいなければ CLOSEST と同じ選び方に戻る."""
    sim, near, _, _, sniper = _setup("SUPPORT")

    assert sim._select_target_legacy(sniper) is near


def test_support_ignores_stale_attack() -> None:
    """直近でない攻撃は無視する."""
    sim, near, far, vanguard, sniper = _setup("SUPPORT")
    _attack(sim, far, vanguard)
    sim.elapsed_time += SUPPORT_THREAT_WINDOW_SEC + 1.0
    sim._step_count += 1

    assert sim._select_target_legacy(sniper) is near


def test_support_only_considers_detected_enemies() -> None:
    """自チームが索敵していない敵は、味方を攻撃していても候補にしない."""
    sim, near, far, vanguard, sniper = _setup("SUPPORT")
    _attack(sim, far, vanguard)
    sim.team_detected_units["ET"] = {near.id}

    assert sim._select_target_legacy(sniper) is near


def test_support_uses_own_squad_only() -> None:
    """小隊がある機体は、別小隊の味方への攻撃を支援の対象にしない."""
    sim, near, far, vanguard, sniper = _setup("SUPPORT")
    sim.unit_assignments[str(vanguard.id)] = UnitAssignment(
        role="VANGUARD", squad_id="OTHER"
    )
    _attack(sim, far, vanguard)

    assert sim._select_target_legacy(sniper) is near


def test_protect_prefers_enemy_attacking_withdrawing_unit() -> None:
    """PROTECT は撤退ロールの味方を攻撃している敵を、前衛を攻撃する敵より優先する."""
    sim, near, far, vanguard, sniper = _setup("PROTECT")
    sim.unit_assignments[str(vanguard.id)] = UnitAssignment(role="WITHDRAW")
    sim.unit_assignments[str(sniper.id)] = UnitAssignment(role="SNIPER")
    escort_target = _unit("Other", "ET", 1050.0)
    sim.units.append(escort_target)
    sim.unit_resources[str(escort_target.id)] = dict(
        sim.unit_resources[str(vanguard.id)]
    )
    _attack(sim, near, escort_target)
    _attack(sim, far, vanguard)

    assert sim._select_target_legacy(sniper) is far


def test_protect_without_escort_acts_like_support() -> None:
    """護衛対象がいない戦場では SUPPORT と同じにする."""
    sim, near, far, vanguard, sniper = _setup("PROTECT")
    _attack(sim, far, vanguard)

    assert sim._select_target_legacy(sniper) is far


def test_support_logs_assist_message() -> None:
    """支援のためにターゲットを変えたことがバトルログに出る."""
    sim, _, far, vanguard, sniper = _setup("SUPPORT")
    _attack(sim, far, vanguard)

    sim._select_target_fuzzy(sniper)

    messages = [
        log.message for log in sim.logs if log.action_type == "TARGET_SELECTION"
    ]
    assert any("援護" in m for m in messages)


def test_npc_tactics_for_support_roles() -> None:
    """支援・狙撃ロールの NPC は priority が SUPPORT になる."""
    assert build_npc_tactics("AGGRESSIVE", "SNIPER")["priority"] == "SUPPORT"
    assert build_npc_tactics("CAUTIOUS", "SUPPORT")["priority"] == "SUPPORT"
    assert build_npc_tactics("AGGRESSIVE", "VANGUARD")["priority"] != "SUPPORT"


def test_validate_tactics_accepts_support_and_protect() -> None:
    """機体更新の戦術の検証が SUPPORT / PROTECT を受け付ける."""
    validate_tactics({"priority": "SUPPORT"})
    validate_tactics({"priority": "PROTECT"})
    with pytest.raises(ValueError):
        validate_tactics({"priority": "UNKNOWN"})

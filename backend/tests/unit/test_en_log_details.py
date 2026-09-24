"""EN 回復量（毎秒）と、EN 消費ログへの残量記録を検証する."""

from unittest.mock import patch

import pytest

from app.engine.constants import EN_DEPLETED_REASON_CODE, EN_SHORTAGE_REASON_CODE
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_weapon(en_cost: int = 0, max_ammo: int | None = None) -> Weapon:
    return Weapon(
        id="beam" if en_cost > 0 else "rifle",
        name="Beam Rifle" if en_cost > 0 else "Rifle",
        power=100,
        range=1000,
        accuracy=80,
        type="BEAM" if en_cost > 0 else "PHYSICAL",
        max_ammo=max_ammo,
        en_cost=en_cost,
        cooldown_sec=0.0,
    )


def _make_unit(
    name: str,
    side: str,
    position: Vector3,
    weapon: Weapon,
    max_en: int = 1000,
    en_recovery: int = 100,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=100000,
        current_hp=100000,
        side=side,
        team_id=f"{side}_TEAM",
        position=position,
        weapons=[weapon],
        max_en=max_en,
        en_recovery=en_recovery,
        sensor_range=5000,
    )


def _make_sim(
    weapon: Weapon, max_en: int = 1000, en_recovery: int = 100
) -> tuple[BattleSimulator, MobileSuit, MobileSuit]:
    player = _make_unit(
        "Player",
        "PLAYER",
        Vector3(x=0, y=0, z=0),
        weapon,
        max_en=max_en,
        en_recovery=en_recovery,
    )
    enemy = _make_unit("Enemy", "ENEMY", Vector3(x=300, y=0, z=0), _make_weapon())
    sim = BattleSimulator(player, [enemy])
    # 射撃弧と LOS の判定で攻撃が止まらないよう、条件を固定する。
    sim.obstacles = []
    sim.unit_resources[str(player.id)]["body_heading_deg"] = 0.0
    return sim, player, enemy


def _attack(sim: BattleSimulator, player: MobileSuit, enemy: MobileSuit) -> None:
    distance = 300.0
    sim._process_attack(
        player, enemy, distance, player.position.to_numpy(), player.weapons[0]
    )


def _actor_logs(sim: BattleSimulator, unit: MobileSuit, action_type: str) -> list:
    return [
        log
        for log in sim.logs
        if log.actor_id == unit.id and log.action_type == action_type
    ]


# ---------------------------------------------------------------------------
# EN 回復量
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dt", [0.1, 0.5, 1.0])
def test_en_recovery_is_per_second(dt: float) -> None:
    """EN は 1 ステップあたり en_recovery × dt だけ回復すること."""
    sim, player, _ = _make_sim(_make_weapon(en_cost=50), en_recovery=100)
    uid = str(player.id)
    sim.unit_resources[uid]["current_en"] = 200.0

    sim._refresh_phase(dt)

    assert sim.unit_resources[uid]["current_en"] == pytest.approx(200.0 + 100 * dt)


def test_en_recovery_capped_at_max_en() -> None:
    """EN 回復は max_en を超えないこと."""
    sim, player, _ = _make_sim(_make_weapon(en_cost=50), max_en=1000)
    uid = str(player.id)
    sim.unit_resources[uid]["current_en"] = 995.0

    sim._refresh_phase(0.1)

    assert sim.unit_resources[uid]["current_en"] == 1000


# ---------------------------------------------------------------------------
# 攻撃ログへの EN 残量記録
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("roll", "action_type"),
    [(0.0, "ATTACK"), (1000.0, "MISS")],
)
def test_en_weapon_attack_log_has_remaining_en(roll: float, action_type: str) -> None:
    """EN 武器の攻撃ログ（命中・ミスとも）に消費後の EN 残量が記録されること."""
    sim, player, enemy = _make_sim(_make_weapon(en_cost=80))
    sim.unit_resources[str(player.id)]["current_en"] = 500.0

    with patch("app.engine.combat.random.uniform", return_value=roll):
        _attack(sim, player, enemy)

    logs = _actor_logs(sim, player, action_type)
    assert len(logs) == 1
    assert logs[0].details == {"en": 420}


def test_non_en_weapon_attack_log_has_no_details() -> None:
    """EN を消費しない武器の攻撃ログには details が付かないこと."""
    sim, player, enemy = _make_sim(_make_weapon(en_cost=0))

    with patch("app.engine.combat.random.uniform", return_value=0.0):
        _attack(sim, player, enemy)

    logs = _actor_logs(sim, player, "ATTACK")
    assert len(logs) == 1
    assert logs[0].details is None


def test_en_shortage_wait_log_has_reason_code() -> None:
    """EN 不足で攻撃できない WAIT ログに reason_code が付くこと."""
    sim, player, enemy = _make_sim(_make_weapon(en_cost=80))
    sim.unit_resources[str(player.id)]["current_en"] = 10.0

    _attack(sim, player, enemy)

    logs = _actor_logs(sim, player, "WAIT")
    assert len(logs) == 1
    assert logs[0].details == {"reason_code": EN_SHORTAGE_REASON_CODE}


def test_ammo_shortage_wait_log_has_no_reason_code() -> None:
    """EN 以外の理由による WAIT ログには details が付かないこと."""
    sim, player, enemy = _make_sim(_make_weapon(en_cost=0, max_ammo=5))
    weapon = player.weapons[0]
    weapon_state = sim._get_or_init_weapon_state(
        weapon, sim.unit_resources[str(player.id)]
    )
    weapon_state["current_ammo"] = 0

    _attack(sim, player, enemy)

    logs = _actor_logs(sim, player, "WAIT")
    assert len(logs) == 1
    assert logs[0].details is None


# ---------------------------------------------------------------------------
# ブーストログへの EN 残量記録
# ---------------------------------------------------------------------------


def test_boost_start_log_has_remaining_en() -> None:
    """BOOST_START ログに開始時の EN 残量が記録されること."""
    sim, player, enemy = _make_sim(_make_weapon(en_cost=0))
    enemy.position = Vector3(x=2000, y=0, z=0)
    with patch("app.engine.targeting.random.random", return_value=0.0):
        sim._detection_phase()
    sim._step_count += 1

    uid = str(player.id)
    sim.unit_resources[uid]["current_action"] = "BOOST_DASH"
    sim.unit_resources[uid]["boost_cooldown_remaining"] = 0.0
    sim.unit_resources[uid]["current_en"] = 654.4

    sim._action_phase(player, 0.1)

    logs = _actor_logs(sim, player, "BOOST_START")
    assert len(logs) == 1
    assert logs[0].details == {"en": 654}


def test_boost_end_by_en_depletion_has_reason_code() -> None:
    """EN 枯渇による BOOST_END ログに EN 残量と reason_code が付くこと."""
    sim, player, enemy = _make_sim(_make_weapon(en_cost=0))
    enemy.position = Vector3(x=5000, y=0, z=0)
    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = True
    sim.unit_resources[uid]["current_en"] = 0.0

    sim._check_boost_cancel(player, enemy, 0.1)

    logs = _actor_logs(sim, player, "BOOST_END")
    assert len(logs) == 1
    assert logs[0].details["en"] == 0
    assert logs[0].details["reason_code"] == EN_DEPLETED_REASON_CODE


def test_boost_end_by_other_reason_has_no_reason_code() -> None:
    """EN 枯渇以外の BOOST_END ログには reason_code が付かないこと."""
    sim, player, enemy = _make_sim(_make_weapon(en_cost=0))
    enemy.position = Vector3(x=5000, y=0, z=0)
    uid = str(player.id)
    sim.unit_resources[uid]["is_boosting"] = True
    sim.unit_resources[uid]["boost_elapsed"] = 999.0
    sim.unit_resources[uid]["current_en"] = 300.0

    sim._check_boost_cancel(player, enemy, 0.1)

    logs = _actor_logs(sim, player, "BOOST_END")
    assert len(logs) == 1
    assert logs[0].details["en"] == 300
    assert "reason_code" not in logs[0].details

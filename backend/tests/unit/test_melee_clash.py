"""鍔迫り合い（正面同士の同時格闘）のテスト.

検証項目:
    1. 発生条件（両機が互いを狙う格闘・攻撃の時間差・正面同士・確率・再発までの時間）
    2. 鍔迫り合いの効果（ダメージなし・再使用待ち・ログ・交戦記録）
    3. 押し離しの向きと距離（押す力の弱い側が大きく飛ばされる）
    4. 押し離しの移動（慣性モデルに乗せる・マップの外に出さない・格闘後の再配置をしない）
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.npc_data import BATTLE_CHATTER
from app.engine import melee_clash
from app.engine.constants import (
    MELEE_CLASH_COOLDOWN_SEC,
    MELEE_CLASH_KNOCKBACK_SEC,
    MELEE_CLASH_PUSH_SHARE_MAX,
    MELEE_CLASH_SEPARATION_MAX,
    MELEE_CLASH_SEPARATION_MIN,
    MELEE_CLASH_WINDOW_SEC,
)
from app.engine.melee_clash import advance_knockback, push_shares, start_knockback
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon

_CENTER = 1000.0
_DISTANCE = 80.0
_DT = 0.1


class _FixedRandom:
    """`melee_clash` が使う乱数を固定する. 他のモジュールの乱数には影響しない."""

    def __init__(self, roll: float) -> None:
        self.roll = roll

    def random(self) -> float:
        return self.roll

    def uniform(self, low: float, high: float) -> float:
        return (low + high) / 2.0


def _saber(power: int = 200) -> Weapon:
    return Weapon(
        id="saber",
        name="Beam Saber",
        power=power,
        range=150,
        accuracy=85,
        type="BEAM",
        optimal_range=100.0,
        is_melee=True,
        weapon_type="MELEE",
    )


def _rifle() -> Weapon:
    return Weapon(
        id="rifle",
        name="Beam Rifle",
        power=300,
        range=600,
        accuracy=80,
        type="BEAM",
        optimal_range=400.0,
    )


def _make_unit(name: str, side: str, weapons: list[Weapon], x: float) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=0,
        mobility=1.0,
        position=Vector3(x=x, y=0, z=_CENTER),
        weapons=weapons,
        side=side,
        team_id=f"{side}_TEAM",
        max_en=1000,
        en_recovery=0,
        sensor_range=2000,
        tactics={"priority": "CLOSEST"},
    )


def _setup(
    enemy_weapons: list[Weapon] | None = None,
) -> tuple[BattleSimulator, MobileSuit, MobileSuit]:
    """正面で向き合い、どちらもサーベルで攻撃しようとしている 2 機を作る.

    プレイヤーは +x を、敵は -x を向く。
    """
    player = _make_unit("Player", "PLAYER", [_saber()], _CENTER)
    enemy = _make_unit(
        "Enemy", "ENEMY", enemy_weapons or [_saber()], _CENTER + _DISTANCE
    )
    sim = BattleSimulator(player, [enemy])
    sim.team_detected_units[player.team_id] = {enemy.id}
    sim.team_detected_units[enemy.team_id] = {player.id}
    for unit, heading in ((player, 0.0), (enemy, 180.0)):
        resources = sim.unit_resources[str(unit.id)]
        resources["current_action"] = "ATTACK"
        resources["active_weapon_id"] = unit.weapons[0].id
        resources["body_heading_deg"] = heading
    return sim, player, enemy


@pytest.fixture
def always_clash(monkeypatch: pytest.MonkeyPatch) -> None:
    """条件がそろえば必ず鍔迫り合いにする."""
    monkeypatch.setattr(melee_clash, "random", _FixedRandom(0.0))


@pytest.fixture
def never_clash(monkeypatch: pytest.MonkeyPatch) -> None:
    """条件がそろっても鍔迫り合いにしない."""
    monkeypatch.setattr(melee_clash, "random", _FixedRandom(0.999))


def _attack(sim: BattleSimulator, actor: MobileSuit, target: MobileSuit) -> bool:
    distance = float(
        np.linalg.norm(target.position.to_numpy() - actor.position.to_numpy())
    )
    return sim._process_attack(
        actor, target, distance, actor.position.to_numpy(), actor.weapons[0]
    )


def _clash_logs(sim: BattleSimulator) -> list:
    return [log for log in sim.logs if log.action_type == "MELEE_CLASH"]


def _cooldown(sim: BattleSimulator, unit: MobileSuit) -> float:
    states = sim.unit_resources[str(unit.id)]["weapon_states"]
    return states[unit.weapons[0].id]["cooldown_remaining_sec"]


# ---------------------------------------------------------------------------
# 1. 発生条件
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("always_clash")
def test_clash_occurs_when_both_melee_from_the_front() -> None:
    """正面同士で両機が同時に格闘すると鍔迫り合いになること."""
    sim, player, enemy = _setup()

    assert _attack(sim, player, enemy) is True

    assert len(_clash_logs(sim)) == 1


@pytest.mark.usefixtures("always_clash")
def test_clash_occurs_when_opponent_cooldown_is_within_window() -> None:
    """相手の格闘が時間差の範囲内に出せるなら、同時の攻撃とみなすこと."""
    sim, player, enemy = _setup()
    sim.unit_resources[str(enemy.id)]["weapon_states"]["saber"][
        "cooldown_remaining_sec"
    ] = MELEE_CLASH_WINDOW_SEC

    _attack(sim, player, enemy)

    assert len(_clash_logs(sim)) == 1


def _opponent_cooling_down(sim: BattleSimulator, enemy: MobileSuit) -> None:
    sim.unit_resources[str(enemy.id)]["weapon_states"]["saber"][
        "cooldown_remaining_sec"
    ] = MELEE_CLASH_WINDOW_SEC + 0.1


def _opponent_moving(sim: BattleSimulator, enemy: MobileSuit) -> None:
    sim.unit_resources[str(enemy.id)]["current_action"] = "MOVE"


def _opponent_switching_weapon(sim: BattleSimulator, enemy: MobileSuit) -> None:
    sim.unit_resources[str(enemy.id)]["weapon_switch_lock_remaining_sec"] = 1.0


def _opponent_facing_away(sim: BattleSimulator, enemy: MobileSuit) -> None:
    sim.unit_resources[str(enemy.id)]["body_heading_deg"] = 0.0


def _actor_facing_away(sim: BattleSimulator, enemy: MobileSuit) -> None:
    sim.unit_resources[str(sim.player.id)]["body_heading_deg"] = 180.0


def _opponent_targets_someone_else(sim: BattleSimulator, enemy: MobileSuit) -> None:
    original = sim._select_target_fuzzy
    sim._select_target_fuzzy = lambda unit: (  # type: ignore[method-assign]
        None if unit is enemy else original(unit)
    )


@pytest.mark.usefixtures("always_clash")
@pytest.mark.parametrize(
    "arrange",
    [
        _opponent_cooling_down,
        _opponent_moving,
        _opponent_switching_weapon,
        _opponent_facing_away,
        _actor_facing_away,
        _opponent_targets_someone_else,
    ],
)
def test_no_clash_unless_all_conditions_hold(arrange) -> None:
    """条件が 1 つでも欠けたら、通常の命中判定をすること."""
    sim, player, enemy = _setup()
    arrange(sim, enemy)

    _attack(sim, player, enemy)

    assert _clash_logs(sim) == []
    assert any(log.action_type in ("ATTACK", "MISS") for log in sim.logs)


@pytest.mark.usefixtures("always_clash")
def test_no_clash_when_opponent_holds_ranged_weapon() -> None:
    """相手が射撃武器を構えているなら鍔迫り合いにならないこと."""
    sim, player, enemy = _setup(enemy_weapons=[_rifle(), _saber()])

    _attack(sim, player, enemy)

    assert _clash_logs(sim) == []


@pytest.mark.usefixtures("always_clash")
def test_no_clash_with_ranged_attack() -> None:
    """自機が射撃武器で攻撃するときは鍔迫り合いにならないこと."""
    sim, player, enemy = _setup()
    player.weapons = [_rifle()]

    _attack(sim, player, enemy)

    assert _clash_logs(sim) == []


@pytest.mark.usefixtures("never_clash")
def test_no_clash_when_chance_roll_fails() -> None:
    """条件がそろっても、確率に外れたら通常の命中判定をすること."""
    sim, player, enemy = _setup()

    _attack(sim, player, enemy)

    assert _clash_logs(sim) == []
    assert sim.unit_resources[str(player.id)]["knockback"] is None


@pytest.mark.usefixtures("always_clash")
def test_no_clash_again_until_cooldown_passes() -> None:
    """鍔迫り合いの後は、一定時間たつまで次の鍔迫り合いを起こさないこと."""
    sim, player, enemy = _setup()
    _attack(sim, player, enemy)

    def ready_and_attack(elapsed: float) -> None:
        sim.elapsed_time = elapsed
        for unit in (player, enemy):
            resources = sim.unit_resources[str(unit.id)]
            resources["weapon_states"]["saber"]["cooldown_remaining_sec"] = 0.0
            resources["knockback"] = None
        _attack(sim, player, enemy)

    ready_and_attack(MELEE_CLASH_COOLDOWN_SEC - 0.1)
    assert len(_clash_logs(sim)) == 1

    ready_and_attack(MELEE_CLASH_COOLDOWN_SEC)
    assert len(_clash_logs(sim)) == 2


# ---------------------------------------------------------------------------
# 2. 鍔迫り合いの効果
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("always_clash")
def test_clash_deals_no_damage_and_consumes_both_attacks() -> None:
    """ダメージを与えず、両機の格闘を再使用待ちにすること."""
    sim, player, enemy = _setup()

    _attack(sim, player, enemy)

    assert player.current_hp == player.max_hp
    assert enemy.current_hp == enemy.max_hp
    assert not any(log.action_type in ("ATTACK", "MISS") for log in sim.logs)
    assert _cooldown(sim, player) > 0.0
    assert _cooldown(sim, enemy) > 0.0


@pytest.mark.usefixtures("always_clash")
def test_clash_log_has_both_weapons_and_push_distances() -> None:
    """ログに両機の武器と押し離しの距離を残すこと."""
    sim, player, enemy = _setup()

    _attack(sim, player, enemy)

    log = _clash_logs(sim)[0]
    assert log.actor_id == player.id
    assert log.target_id == enemy.id
    assert log.weapon_name == "Beam Saber"
    assert "鍔迫り合い" in log.message
    assert log.details is not None
    assert log.details["target_weapon_name"] == "Beam Saber"
    total = log.details["actor_push_m"] + log.details["target_push_m"]
    assert MELEE_CLASH_SEPARATION_MIN <= total <= MELEE_CLASH_SEPARATION_MAX


@pytest.mark.usefixtures("always_clash")
def test_clash_is_recorded_as_one_exchange() -> None:
    """交戦記録に、両機が 1 回ずつ外した攻撃として残すこと."""
    sim, player, enemy = _setup()
    sim._ai_decision_phase(player)
    sim._ai_decision_phase(enemy)
    player_record = sim.unit_resources[str(player.id)]["engagement"]
    enemy_record = sim.unit_resources[str(enemy.id)]["engagement"]
    for unit in (player, enemy):
        resources = sim.unit_resources[str(unit.id)]
        resources["current_action"] = "ATTACK"
        resources["active_weapon_id"] = "saber"

    _attack(sim, player, enemy)

    for record in (player_record, enemy_record):
        assert record.attacks == 1
        assert record.attacks_since_hit == 1
        assert record.attacked == 1
        assert record.hits == 0


def test_clash_chatter_exists_for_every_personality() -> None:
    """どの性格にも鍔迫り合いのセリフがあること."""
    for personality, chatter in BATTLE_CHATTER.items():
        assert chatter.get("clash"), personality


# ---------------------------------------------------------------------------
# 3. 押し離しの向きと距離
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("always_clash")
def test_clash_pushes_units_in_opposite_directions() -> None:
    """両機を互いに離れる向きへ押し、速度を 0 にすること."""
    sim, player, enemy = _setup()

    _attack(sim, player, enemy)

    player_resources = sim.unit_resources[str(player.id)]
    enemy_resources = sim.unit_resources[str(enemy.id)]
    # プレイヤーは敵の -x 側にいる。
    assert player_resources["knockback"].velocity[0] < 0.0
    assert enemy_resources["knockback"].velocity[0] > 0.0
    assert np.allclose(player_resources["velocity_vec"], 0.0)
    assert np.allclose(enemy_resources["velocity_vec"], 0.0)


@pytest.mark.usefixtures("always_clash")
def test_weaker_unit_is_pushed_farther() -> None:
    """押す力の弱い側（威力の低い武器）が大きく飛ばされること."""
    sim, player, enemy = _setup(enemy_weapons=[_saber(power=100)])

    _attack(sim, player, enemy)

    details = _clash_logs(sim)[0].details
    assert details["target_push_m"] > details["actor_push_m"]


def test_push_shares_split_by_power_and_are_clamped() -> None:
    """押す力が同じなら半分ずつ、差が大きくても上限で抑えること."""
    assert push_shares(100.0, 100.0) == pytest.approx((0.5, 0.5))

    weak, strong = push_shares(100.0, 300.0)
    assert weak > strong
    assert weak + strong == pytest.approx(1.0)

    assert push_shares(1.0, 1000.0)[0] == pytest.approx(MELEE_CLASH_PUSH_SHARE_MAX)


def test_knockback_travels_the_given_distance_and_stops() -> None:
    """押し離しは指定した距離だけ進み、指定した時間で止まること."""
    knockback = start_knockback(
        np.array([1.0, 0.0, 0.0]), 50.0, MELEE_CLASH_KNOCKBACK_SEC
    )
    total = np.zeros(3)
    steps = 0
    current = knockback
    while current is not None:
        displacement, current = advance_knockback(current, _DT)
        total += displacement
        steps += 1

    assert total[0] == pytest.approx(50.0)
    assert total[2] == pytest.approx(0.0)
    assert steps == pytest.approx(MELEE_CLASH_KNOCKBACK_SEC / _DT, abs=1)


# ---------------------------------------------------------------------------
# 4. 押し離しの移動
# ---------------------------------------------------------------------------


def test_knockback_is_applied_through_inertia_model() -> None:
    """押し離しは瞬間移動ではなく、移動のたびに少しずつ位置へ加えること."""
    sim, player, _enemy = _setup()
    resources = sim.unit_resources[str(player.id)]
    resources["knockback"] = start_knockback(
        np.array([-1.0, 0.0, 0.0]), 50.0, MELEE_CLASH_KNOCKBACK_SEC
    )
    player.max_speed = 0.0
    start_x = player.position.x

    sim._apply_inertia(player, np.array([1.0, 0.0, 0.0]), _DT)
    first_step = start_x - player.position.x
    assert 0.0 < first_step < 50.0

    for _ in range(int(MELEE_CLASH_KNOCKBACK_SEC / _DT)):
        sim._apply_inertia(player, np.array([1.0, 0.0, 0.0]), _DT)
    assert start_x - player.position.x == pytest.approx(50.0)
    assert resources["knockback"] is None


def test_knockback_stops_at_map_boundary() -> None:
    """押し離しでマップの外へ出さないこと."""
    sim, player, _enemy = _setup()
    map_min, _map_max = sim.map_bounds
    player.position = Vector3(x=map_min + 5.0, y=0, z=_CENTER)
    player.max_speed = 0.0
    sim.unit_resources[str(player.id)]["knockback"] = start_knockback(
        np.array([-1.0, 0.0, 0.0]), 50.0, MELEE_CLASH_KNOCKBACK_SEC
    )

    for _ in range(int(MELEE_CLASH_KNOCKBACK_SEC / _DT) + 1):
        sim._apply_inertia(player, np.array([1.0, 0.0, 0.0]), _DT)

    assert player.position.x == pytest.approx(map_min)


@pytest.mark.usefixtures("always_clash")
def test_engage_melee_clash_does_not_reposition_next_to_target() -> None:
    """ENGAGE_MELEE の鍔迫り合いでは、格闘命中後の再配置をしないこと."""
    sim, player, enemy = _setup()
    sim.unit_resources[str(player.id)]["current_action"] = "ENGAGE_MELEE"
    start = player.position.to_numpy()

    sim._process_engage_melee(player, enemy, start, player.weapons[0])

    assert len(_clash_logs(sim)) == 1
    assert np.allclose(player.position.to_numpy(), start)


@pytest.mark.usefixtures("always_clash")
def test_units_separate_after_clash_in_simulation() -> None:
    """シミュレーションを進めると、鍔迫り合いの後に両機の間隔が開くこと."""
    sim, player, enemy = _setup()

    for _ in range(50):
        sim.step(_DT)
        if _clash_logs(sim):
            break
    assert _clash_logs(sim), "鍔迫り合いが起きなかった"
    at_clash = float(
        np.linalg.norm(player.position.to_numpy() - enemy.position.to_numpy())
    )

    for _ in range(int(MELEE_CLASH_KNOCKBACK_SEC / _DT)):
        sim.step(_DT)

    after = float(
        np.linalg.norm(player.position.to_numpy() - enemy.position.to_numpy())
    )
    assert after - at_clash >= MELEE_CLASH_SEPARATION_MIN / 2.0

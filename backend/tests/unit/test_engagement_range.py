"""交戦距離（間合い）制御と敵との最小間隔のテスト."""

import numpy as np
import pytest

from app.engine.constants import (
    ATTACK_TARGET_ATTRACTION_COEFF,
    ENEMY_MIN_SEPARATION,
    ENGAGEMENT_BAND_FORCE_RATIO,
    ENGAGEMENT_RANGE_STRATEGY_MULTIPLIERS,
    ENGAGEMENT_RANGE_TOLERANCE_RATIO,
    MELEE_ENGAGEMENT_RANGE_MIN,
    STRAFE_ATTRACTION_COEFF,
)
from app.engine.movement import EngagementRange, MovementMixin
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Obstacle, Vector3, Weapon

# 2 機のときのフィールドは 2000m 四方。境界の影響を受けない中央付近を使う。
_CENTER = 1000.0


@pytest.fixture(autouse=True)
def _no_flanking(monkeypatch: pytest.MonkeyPatch) -> None:
    """フランキングを発動させない.

    スキルなしでも確率で発動し、移動方向が敵の背後へ向くため。
    """
    monkeypatch.setattr("app.engine.movement.random.random", lambda: 1.0)


def _make_weapon(
    range_: float = 600.0,
    optimal_range: float = 400.0,
    is_melee: bool = False,
    max_ammo: int | None = None,
) -> Weapon:
    return Weapon(
        id="w1",
        name="Test Weapon",
        power=100,
        range=range_,
        accuracy=80,
        optimal_range=optimal_range,
        is_melee=is_melee,
        max_ammo=max_ammo,
    )


def _make_unit(
    name: str,
    side: str,
    team_id: str,
    x: float,
    z: float = _CENTER,
    weapons: list[Weapon] | None = None,
    strategy_mode: str | None = None,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=0,
        mobility=1.0,
        position=Vector3(x=x, y=0, z=z),
        weapons=weapons if weapons is not None else [_make_weapon()],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        strategy_mode=strategy_mode,
    )


def _setup(
    player_x: float,
    enemy_x: float,
    player_weapons: list[Weapon] | None = None,
    strategy_mode: str | None = None,
) -> tuple[BattleSimulator, MobileSuit, MobileSuit]:
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        player_x,
        weapons=player_weapons,
        strategy_mode=strategy_mode,
    )
    # 脅威度による斥力が出ないよう、敵の武器は弱くする。
    enemy = _make_unit(
        "Enemy",
        "ENEMY",
        "ET",
        enemy_x,
        weapons=[Weapon(id="ew", name="Weak", power=1, range=600, accuracy=80)],
    )
    sim = BattleSimulator(player, [enemy])
    return sim, player, enemy


def _radial(direction: np.ndarray, unit: MobileSuit, target: MobileSuit) -> float:
    """移動方向のうちターゲットへ向かう成分を返す（正なら接近）."""
    to_target = target.position.to_numpy() - unit.position.to_numpy()
    return float(np.dot(direction, to_target / np.linalg.norm(to_target)))


# ---------------------------------------------------------------------------
# 目標交戦距離
# ---------------------------------------------------------------------------


class TestEngagementRange:
    """`_engagement_range()` の目標交戦距離."""

    def test_uses_optimal_range_with_tolerance(self) -> None:
        """最適距離を目標とし、その 20% を許容幅にする."""
        sim, player, _ = _setup(_CENTER, _CENTER + 400)
        engagement = sim._engagement_range(player, player.weapons[0])

        assert engagement is not None
        assert engagement.distance == pytest.approx(400.0)
        assert engagement.tolerance == pytest.approx(
            400.0 * ENGAGEMENT_RANGE_TOLERANCE_RATIO
        )

    @pytest.mark.parametrize("mode", sorted(ENGAGEMENT_RANGE_STRATEGY_MULTIPLIERS))
    def test_strategy_multiplier(self, mode: str) -> None:
        """戦略モードの倍率を目標距離に掛ける."""
        sim, player, _ = _setup(_CENTER, _CENTER + 400, strategy_mode=mode)
        engagement = sim._engagement_range(player, player.weapons[0])

        assert engagement is not None
        assert engagement.distance == pytest.approx(
            400.0 * ENGAGEMENT_RANGE_STRATEGY_MULTIPLIERS[mode]
        )

    def test_far_edge_stays_within_weapon_range(self) -> None:
        """最適距離が射程に近い武器でも、許容幅の外側の端は射程内に収まる."""
        weapon = _make_weapon(range_=400.0, optimal_range=380.0)
        sim, player, _ = _setup(_CENTER, _CENTER + 400, player_weapons=[weapon])
        engagement = sim._engagement_range(player, weapon)

        assert engagement is not None
        assert engagement.far == pytest.approx(400.0)

    def test_melee_weapon_has_lower_bound(self) -> None:
        """格闘武器の目標距離は下限より短くならない."""
        weapon = _make_weapon(range_=50.0, optimal_range=5.0, is_melee=True)
        sim, player, _ = _setup(_CENTER, _CENTER + 30, player_weapons=[weapon])
        engagement = sim._engagement_range(player, weapon)

        assert engagement is not None
        assert engagement.distance == pytest.approx(MELEE_ENGAGEMENT_RANGE_MIN)

    def test_none_without_weapon(self) -> None:
        """武器が無いときは目標距離を持たない."""
        sim, player, _ = _setup(_CENTER, _CENTER + 400, player_weapons=[])

        assert sim._engagement_range(player, None) is None

    def test_none_when_out_of_ammo(self) -> None:
        """弾切れの武器は間合いの基準にしない."""
        weapon = _make_weapon(max_ammo=10)
        sim, player, _ = _setup(_CENTER, _CENTER + 400, player_weapons=[weapon])
        resources = sim.unit_resources[str(player.id)]
        sim._get_or_init_weapon_state(weapon, resources)["current_ammo"] = 0

        assert sim._engagement_range(player, weapon) is None

    def test_kept_while_cooling_down(self) -> None:
        """再使用待ちの間も間合いを保つ."""
        weapon = _make_weapon()
        sim, player, _ = _setup(_CENTER, _CENTER + 400, player_weapons=[weapon])
        resources = sim.unit_resources[str(player.id)]
        sim._get_or_init_weapon_state(weapon, resources)["cooldown_remaining_sec"] = 2.0

        assert sim._engagement_range(player, weapon) is not None


# ---------------------------------------------------------------------------
# 間合いのばね
# ---------------------------------------------------------------------------


class TestEngagementSpring:
    """`_engagement_spring()` の力の向きと大きさ."""

    _ENGAGEMENT = EngagementRange(400.0, 80.0)

    def _spring(self, dist: float) -> np.ndarray:
        return MovementMixin._engagement_spring(
            np.zeros(3),
            np.array([dist, 0.0, 0.0]),
            self._ENGAGEMENT,
            ATTACK_TARGET_ATTRACTION_COEFF,
        )

    def test_pulls_when_far(self) -> None:
        """許容幅より十分遠いと、引力係数いっぱいで引き寄せる."""
        force = self._spring(800.0)

        assert force[0] == pytest.approx(ATTACK_TARGET_ATTRACTION_COEFF)

    def test_pushes_when_near(self) -> None:
        """許容幅より十分近いと、引力係数いっぱいで押し戻す."""
        force = self._spring(100.0)

        assert force[0] == pytest.approx(-ATTACK_TARGET_ATTRACTION_COEFF)

    def test_zero_at_target_distance(self) -> None:
        """目標距離ちょうどでは力が無い."""
        assert np.allclose(self._spring(400.0), 0.0)

    @pytest.mark.parametrize("dist", [330.0, 370.0, 430.0, 470.0])
    def test_weaker_than_strafe_inside_band(self, dist: float) -> None:
        """許容幅の中では、周回の力より弱い力で目標距離へ寄せる."""
        force = self._spring(dist)

        assert abs(force[0]) <= (
            ATTACK_TARGET_ATTRACTION_COEFF * ENGAGEMENT_BAND_FORCE_RATIO + 1e-9
        )
        assert abs(force[0]) < STRAFE_ATTRACTION_COEFF
        assert np.sign(force[0]) == np.sign(dist - 400.0)

    def test_continuous_at_band_edge(self) -> None:
        """許容幅の端で力が跳ねない."""
        inside = self._spring(480.0 - 1e-6)
        outside = self._spring(480.0 + 1e-6)

        assert inside[0] == pytest.approx(outside[0], abs=1e-6)


# ---------------------------------------------------------------------------
# ポテンシャルフィールドでの移動方向
# ---------------------------------------------------------------------------


class TestPotentialFieldEngagement:
    """間合いを反映したポテンシャルフィールドの移動方向."""

    def test_attack_approaches_when_far(self) -> None:
        """ATTACK 中、目標距離より遠いとターゲットへ近づく."""
        sim, player, enemy = _setup(_CENTER - 400, _CENTER + 400)
        sim.unit_resources[str(player.id)]["current_action"] = "ATTACK"

        direction = sim._calculate_potential_field(player, target=enemy)

        assert _radial(direction, player, enemy) > 0.9

    def test_attack_backs_off_when_near(self) -> None:
        """ATTACK 中、目標距離より近いとターゲットから離れる."""
        sim, player, enemy = _setup(_CENTER - 50, _CENTER + 50)
        sim.unit_resources[str(player.id)]["current_action"] = "ATTACK"

        direction = sim._calculate_potential_field(player, target=enemy)

        assert _radial(direction, player, enemy) < 0.0

    def test_attack_circles_inside_band(self) -> None:
        """許容幅の中では、ターゲットの周りを回る動きが主になる."""
        sim, player, enemy = _setup(_CENTER - 210, _CENTER + 210)
        sim.unit_resources[str(player.id)]["current_action"] = "ATTACK"

        direction = sim._calculate_potential_field(player, target=enemy)

        assert abs(_radial(direction, player, enemy)) < 0.5

    def test_records_engagement_range(self) -> None:
        """計算した目標交戦距離を `unit_resources` に残す."""
        sim, player, enemy = _setup(_CENTER - 200, _CENTER + 200)
        sim.unit_resources[str(player.id)]["current_action"] = "ATTACK"

        sim._calculate_potential_field(player, target=enemy)

        engagement = sim.unit_resources[str(player.id)]["engagement_range"]
        assert engagement == EngagementRange(400.0, 80.0)

    def test_attack_without_usable_weapon_keeps_approaching(self) -> None:
        """弾切れで間合いの基準が無いときは、従来どおり近づく."""
        weapon = _make_weapon(max_ammo=10)
        sim, player, enemy = _setup(_CENTER - 50, _CENTER + 50, player_weapons=[weapon])
        resources = sim.unit_resources[str(player.id)]
        sim._get_or_init_weapon_state(weapon, resources)["current_ammo"] = 0
        resources["current_action"] = "ATTACK"

        direction = sim._calculate_potential_field(player, target=enemy)

        # ストレイフの接線成分が加わるため、真っすぐには向かわない。
        assert _radial(direction, player, enemy) > 0.8
        assert resources["engagement_range"] is None

    def test_attack_approaches_when_line_of_sight_blocked(self) -> None:
        """射線が障害物で遮られているときは、近すぎても間合いを取らず近づく."""
        # 障害物の斥力が届かない位置に置く。
        sim, player, enemy = _setup(_CENTER - 200, _CENTER)
        sim.obstacles = [
            Obstacle(
                obstacle_id="wall",
                position=Vector3(x=_CENTER - 100, y=0, z=_CENTER),
                radius=20.0,
            )
        ]
        sim.unit_resources[str(player.id)]["current_action"] = "ATTACK"

        direction = sim._calculate_potential_field(player, target=enemy)

        assert _radial(direction, player, enemy) > 0.0

    def test_move_backs_off_from_detected_enemy_in_range(self) -> None:
        """MOVE 中、射程内の索敵済みの敵が近すぎると離れる."""
        sim, player, enemy = _setup(_CENTER - 50, _CENTER + 50)
        sim.team_detected_units["PT"].add(enemy.id)
        sim.unit_resources[str(player.id)]["current_action"] = "MOVE"

        direction = sim._calculate_potential_field(player, target=None)

        assert _radial(direction, player, enemy) < 0.0

    def test_move_approaches_undetected_enemy(self) -> None:
        """MOVE 中、未索敵の敵には従来どおり近づく."""
        sim, player, enemy = _setup(_CENTER - 50, _CENTER + 50)
        sim.team_detected_units["PT"].discard(enemy.id)
        sim.unit_resources[str(player.id)]["current_action"] = "MOVE"

        direction = sim._calculate_potential_field(player, target=None)

        assert _radial(direction, player, enemy) > 0.9

    def test_back_off_does_not_push_into_boundary(self) -> None:
        """境界際で後退するときは、境界へ向かわず壁沿いに動く."""
        sim, player, enemy = _setup(_CENTER, _CENTER)
        map_min, _ = sim.map_bounds
        player.position = Vector3(x=map_min + 20.0, y=0, z=_CENTER)
        enemy.position = Vector3(x=map_min + 120.0, y=0, z=_CENTER)
        sim.unit_resources[str(player.id)]["current_action"] = "ATTACK"

        direction = sim._calculate_potential_field(player, target=enemy)

        assert direction[0] >= 0.0


# ---------------------------------------------------------------------------
# 敵との最小間隔
# ---------------------------------------------------------------------------


class TestEnemySeparation:
    """`_enemy_separation_repulsion()` の最小間隔."""

    def test_pushes_away_inside_min_separation(self) -> None:
        """最小間隔より近い敵から離れる向きの力が働く."""
        sim, player, enemy = _setup(_CENTER, _CENTER + ENEMY_MIN_SEPARATION / 2)

        force = sim._enemy_separation_repulsion(player, player.position.to_numpy())

        assert force[0] < 0.0
        assert force[2] == pytest.approx(0.0)

    def test_zero_outside_min_separation(self) -> None:
        """最小間隔より遠い敵からは力が働かない."""
        sim, player, _ = _setup(_CENTER, _CENTER + ENEMY_MIN_SEPARATION + 1.0)

        force = sim._enemy_separation_repulsion(player, player.position.to_numpy())

        assert np.allclose(force, 0.0)

    def test_ignores_allies(self) -> None:
        """味方は最小間隔の対象にしない."""
        player = _make_unit("Player", "PLAYER", "PT", _CENTER)
        ally = _make_unit("Ally", "PLAYER", "PT", _CENTER + 2.0)
        enemy = _make_unit("Enemy", "ENEMY", "ET", _CENTER + 500.0)
        sim = BattleSimulator(player, [enemy])
        sim.units.append(ally)

        force = sim._enemy_separation_repulsion(player, player.position.to_numpy())

        assert np.allclose(force, 0.0)

    def test_overlapping_units_split_in_opposite_directions(self) -> None:
        """完全に重なった 2 機は逆向きに押し出される."""
        sim, player, enemy = _setup(_CENTER, _CENTER)

        force_player = sim._enemy_separation_repulsion(
            player, player.position.to_numpy()
        )
        force_enemy = sim._enemy_separation_repulsion(enemy, enemy.position.to_numpy())

        assert np.linalg.norm(force_player) > 0.0
        assert np.allclose(force_player, -force_enemy)

    def test_overrides_attack_attraction_when_overlapping(self) -> None:
        """弾切れで近づき続ける状態でも、最小間隔より内側には入らない."""
        weapon = _make_weapon(max_ammo=10)
        sim, player, enemy = _setup(_CENTER, _CENTER + 2.0, player_weapons=[weapon])
        resources = sim.unit_resources[str(player.id)]
        sim._get_or_init_weapon_state(weapon, resources)["current_ammo"] = 0
        resources["current_action"] = "ATTACK"

        direction = sim._calculate_potential_field(player, target=enemy)

        assert _radial(direction, player, enemy) < 0.0

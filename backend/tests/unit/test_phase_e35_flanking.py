"""Phase E-3.5: フランキングパッシブスキルのテスト."""

from unittest.mock import patch

import numpy as np
import pytest

from app.core.npc_data import ACE_PILOTS
from app.core.skills import SKILL_MASTER_DATA
from app.engine.constants import (
    DEFAULT_BOOST_EN_COST,
    FLANKING_ACTIVATION_PROBS,
    FLANKING_ATTRACTION_WEIGHT,
    FLANKING_ENERGY_COST_RATE,
    FLANKING_OFFSET_DISTANCE,
)
from app.engine.simulation import BattleSimulator, _resolve_flanking_skill_level
from app.models.models import MobileSuit, Vector3, Weapon

# ---------------------------------------------------------------------------
# テストヘルパー
# ---------------------------------------------------------------------------


def _make_weapon() -> Weapon:
    return Weapon(
        id="test_weapon",
        name="Test Rifle",
        power=100,
        range=600.0,
        accuracy=80,
        type="BEAM",
        optimal_range=300.0,
        decay_rate=0.05,
        cooldown_sec=0.0,
        max_ammo=999,
    )


def _make_unit(
    name: str,
    side: str,
    position: Vector3,
    personality: str | None = None,
    is_ace: bool = False,
    ace_id: str | None = None,
    max_en: float = 2000.0,
) -> MobileSuit:
    team_id = "PLAYER_TEAM" if side == "PLAYER" else "ENEMY_TEAM"
    return MobileSuit(
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=0,
        mobility=1.0,
        position=position,
        weapons=[_make_weapon()],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        max_speed=100.0,
        acceleration=30.0,
        sensor_range=10000.0,
        personality=personality,
        is_ace=is_ace,
        ace_id=ace_id,
        max_en=max_en,
    )


def _make_sim(
    player_flanking: int = 0,
    player_en: float = 2000.0,
    enemy_personality: str | None = None,
) -> tuple[MobileSuit, MobileSuit, BattleSimulator]:
    """BattleSimulator の標準フィクスチャ."""
    player = _make_unit(
        "Player",
        "PLAYER",
        Vector3(x=0.0, y=0.0, z=500.0),
        max_en=player_en,
    )
    enemy = _make_unit(
        "Enemy",
        "ENEMY",
        Vector3(x=0.0, y=0.0, z=0.0),
        personality=enemy_personality,
    )
    skills = {"flanking": player_flanking} if player_flanking > 0 else {}
    sim = BattleSimulator(player, [enemy], player_skills=skills)
    sim.team_detected_units["PLAYER_TEAM"].add(enemy.id)
    sim.team_detected_units["ENEMY_TEAM"].add(player.id)
    return player, enemy, sim


# ---------------------------------------------------------------------------
# TestFlankingConstants: 定数値とスキルマスタデータの確認
# ---------------------------------------------------------------------------


class TestFlankingConstants:
    """フランキング関連定数と SKILL_MASTER_DATA エントリの値を検証する."""

    def test_flanking_offset_distance(self) -> None:
        """FLANKING_OFFSET_DISTANCE が 30.0 であること."""
        assert FLANKING_OFFSET_DISTANCE == 30.0

    def test_flanking_attraction_weight(self) -> None:
        """FLANKING_ATTRACTION_WEIGHT が 1.5 であること."""
        assert FLANKING_ATTRACTION_WEIGHT == 1.5

    def test_flanking_energy_cost_rate(self) -> None:
        """FLANKING_ENERGY_COST_RATE が 1.5 であること."""
        assert FLANKING_ENERGY_COST_RATE == 1.5

    def test_flanking_activation_probs_values(self) -> None:
        """各スキルレベルの発動確率が仕様通りであること."""
        assert FLANKING_ACTIVATION_PROBS[0] == pytest.approx(0.05)
        assert FLANKING_ACTIVATION_PROBS[1] == pytest.approx(0.30)
        assert FLANKING_ACTIVATION_PROBS[2] == pytest.approx(0.60)
        assert FLANKING_ACTIVATION_PROBS[3] == pytest.approx(0.90)

    def test_flanking_skill_in_master_data(self) -> None:
        """Flanking スキルが SKILL_MASTER_DATA に登録されていること."""
        assert "flanking" in SKILL_MASTER_DATA

    def test_flanking_skill_max_level(self) -> None:
        """Flanking スキルの最大レベルが 3 であること."""
        assert SKILL_MASTER_DATA["flanking"]["max_level"] == 3

    def test_flanking_skill_id(self) -> None:
        """Flanking スキルの ID が正しいこと."""
        assert SKILL_MASTER_DATA["flanking"]["id"] == "flanking"


# ---------------------------------------------------------------------------
# TestFlankingSkillLevelResolution: スキルレベル解決
# ---------------------------------------------------------------------------


class TestFlankingSkillLevelResolution:
    """unit_resources["flanking_skill_level"] の解決ロジックを検証する."""

    def test_player_gets_flanking_from_player_skills(self) -> None:
        """プレイヤーは player_skills["flanking"] の値を参照すること."""
        player, enemy, sim = _make_sim(player_flanking=2)
        assert sim.unit_resources[str(player.id)]["flanking_skill_level"] == 2

    def test_player_default_flanking_is_zero(self) -> None:
        """player_skills に flanking がない場合はレベル 0 になること."""
        player, enemy, sim = _make_sim(player_flanking=0)
        assert sim.unit_resources[str(player.id)]["flanking_skill_level"] == 0

    def test_aggressive_npc_gets_level_1(self) -> None:
        """personality=AGGRESSIVE の通常 NPC はレベル 1 になること."""
        player, enemy, sim = _make_sim(enemy_personality="AGGRESSIVE")
        assert sim.unit_resources[str(enemy.id)]["flanking_skill_level"] == 1

    def test_cautious_npc_gets_level_0(self) -> None:
        """personality=CAUTIOUS の通常 NPC はレベル 0 になること."""
        player, enemy, sim = _make_sim(enemy_personality="CAUTIOUS")
        assert sim.unit_resources[str(enemy.id)]["flanking_skill_level"] == 0

    def test_sniper_npc_gets_level_0(self) -> None:
        """personality=SNIPER の通常 NPC はレベル 0 になること."""
        player, enemy, sim = _make_sim(enemy_personality="SNIPER")
        assert sim.unit_resources[str(enemy.id)]["flanking_skill_level"] == 0

    def test_no_personality_npc_gets_level_0(self) -> None:
        """personality=None の通常 NPC はレベル 0 になること."""
        player, enemy, sim = _make_sim(enemy_personality=None)
        assert sim.unit_resources[str(enemy.id)]["flanking_skill_level"] == 0

    def test_ace_npc_aggressive_gets_level_3(self) -> None:
        """AGGRESSIVE エース（シャア）は flanking Lv.3 になること."""
        player = _make_unit("Player", "PLAYER", Vector3(x=0.0, y=0.0, z=500.0))
        ace_enemy = _make_unit(
            "Char",
            "ENEMY",
            Vector3(x=0.0, y=0.0, z=0.0),
            personality="AGGRESSIVE",
            is_ace=True,
            ace_id="ace_char_aznable",
        )
        sim = BattleSimulator(player, [ace_enemy])
        assert sim.unit_resources[str(ace_enemy.id)]["flanking_skill_level"] == 3

    def test_ace_npc_non_aggressive_gets_level_2(self) -> None:
        """非 AGGRESSIVE エース（アムロ）は flanking Lv.2 になること."""
        player = _make_unit("Player", "PLAYER", Vector3(x=0.0, y=0.0, z=500.0))
        ace_enemy = _make_unit(
            "Amuro",
            "ENEMY",
            Vector3(x=0.0, y=0.0, z=0.0),
            personality="CAUTIOUS",
            is_ace=True,
            ace_id="ace_amuro_ray",
        )
        sim = BattleSimulator(player, [ace_enemy])
        assert sim.unit_resources[str(ace_enemy.id)]["flanking_skill_level"] == 2

    def test_resolve_flanking_helper_player(self) -> None:
        """_resolve_flanking_skill_level がプレイヤーのスキルを正しく返すこと."""
        player = _make_unit("P", "PLAYER", Vector3(x=0.0, y=0.0, z=0.0))
        level = _resolve_flanking_skill_level(
            player, is_player=True, player_skills={"flanking": 3}
        )
        assert level == 3

    def test_resolve_flanking_helper_no_skills(self) -> None:
        """_resolve_flanking_skill_level が player_skills=None のとき 0 を返すこと."""
        player = _make_unit("P", "PLAYER", Vector3(x=0.0, y=0.0, z=0.0))
        level = _resolve_flanking_skill_level(
            player, is_player=True, player_skills=None
        )
        assert level == 0


# ---------------------------------------------------------------------------
# TestFlankingAttractionVector: ベクトル計算
# ---------------------------------------------------------------------------


class TestFlankingAttractionVector:
    """_flanking_attraction() のベクトル計算・条件分岐を検証する."""

    def test_no_flanking_force_when_level_0_and_roll_above_threshold(self) -> None:
        """Lv.0（確率 5%）のとき random=0.1（> 0.05）では発動しないこと."""
        player, enemy, sim = _make_sim(player_flanking=0)
        with patch("app.engine.movement.random.random", return_value=0.1):
            force = sim._flanking_attraction(player, enemy, dt=0.1)
        assert np.allclose(force, np.zeros(3))

    def test_flanking_force_nonzero_when_level3_activated(self) -> None:
        """Lv.3 で random=0.0（< 0.9）のとき非ゼロベクトルを返すこと."""
        player, enemy, sim = _make_sim(player_flanking=3)
        with patch("app.engine.movement.random.random", return_value=0.0):
            force = sim._flanking_attraction(player, enemy, dt=0.1)
        assert not np.allclose(force, np.zeros(3))

    def test_flanking_force_zero_when_en_insufficient(self) -> None:
        """EN 不足時はゼロベクトルを返してフォールバックすること."""
        player, enemy, sim = _make_sim(player_flanking=3, player_en=0.0)
        sim.unit_resources[str(player.id)]["current_en"] = 0.0
        with patch("app.engine.movement.random.random", return_value=0.0):
            force = sim._flanking_attraction(player, enemy, dt=0.1)
        assert np.allclose(force, np.zeros(3))

    def test_flanking_rear_direction_geometry(self) -> None:
        """Target が heading=0（+X 向き）のとき後方引力が -X 方向になること."""
        player = _make_unit("Player", "PLAYER", Vector3(x=200.0, y=0.0, z=0.0))
        enemy = _make_unit("Enemy", "ENEMY", Vector3(x=0.0, y=0.0, z=0.0))
        sim = BattleSimulator(player, [enemy], player_skills={"flanking": 3})
        sim.team_detected_units["PLAYER_TEAM"].add(enemy.id)
        sim.team_detected_units["ENEMY_TEAM"].add(player.id)

        # enemy の body_heading_deg = 0 (デフォルト) → 正面=+X, 後方=-X
        sim.unit_resources[str(enemy.id)]["body_heading_deg"] = 0.0

        with patch("app.engine.movement.random.random", return_value=0.0):
            force = sim._flanking_attraction(player, enemy, dt=0.1)

        # 後方ポイントは (-30, 0, 0)、プレイヤーは (200, 0, 0) → 力は -X 方向
        assert force[0] < 0.0
        assert abs(force[2]) < abs(force[0])  # Z 成分は X 成分より小さい

    def test_flanking_force_zero_when_not_activated(self) -> None:
        """random=1.0（> 0.9）のとき Lv.3 でも発動しないこと."""
        player, enemy, sim = _make_sim(player_flanking=3)
        with patch("app.engine.movement.random.random", return_value=1.0):
            force = sim._flanking_attraction(player, enemy, dt=0.1)
        assert np.allclose(force, np.zeros(3))


# ---------------------------------------------------------------------------
# TestFlankingEnergyConsumption: EN 消費
# ---------------------------------------------------------------------------


class TestFlankingEnergyConsumption:
    """フランキング発動時の EN 消費量を検証する."""

    def test_flanking_consumes_en_when_activated(self) -> None:
        """発動時に FLANKING_ENERGY_COST_RATE * boost_en_cost * dt を消費すること."""
        player, enemy, sim = _make_sim(player_flanking=3, player_en=2000.0)
        en_before = sim.unit_resources[str(player.id)]["current_en"]
        dt = 0.1
        expected_cost = FLANKING_ENERGY_COST_RATE * DEFAULT_BOOST_EN_COST * dt

        with patch("app.engine.movement.random.random", return_value=0.0):
            sim._flanking_attraction(player, enemy, dt=dt)

        en_after = sim.unit_resources[str(player.id)]["current_en"]
        assert en_after == pytest.approx(en_before - expected_cost)

    def test_flanking_does_not_consume_en_when_not_activated(self) -> None:
        """未発動時は EN が変化しないこと."""
        player, enemy, sim = _make_sim(player_flanking=3, player_en=2000.0)
        en_before = sim.unit_resources[str(player.id)]["current_en"]

        with patch("app.engine.movement.random.random", return_value=1.0):
            sim._flanking_attraction(player, enemy, dt=0.1)

        en_after = sim.unit_resources[str(player.id)]["current_en"]
        assert en_after == pytest.approx(en_before)

    def test_flanking_does_not_consume_en_when_insufficient(self) -> None:
        """EN=0 の場合は消費せずゼロのまま返すこと."""
        player, enemy, sim = _make_sim(player_flanking=3, player_en=0.0)
        sim.unit_resources[str(player.id)]["current_en"] = 0.0

        with patch("app.engine.movement.random.random", return_value=0.0):
            sim._flanking_attraction(player, enemy, dt=0.1)

        assert sim.unit_resources[str(player.id)]["current_en"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# TestFlankingIntegration: 統合テスト
# ---------------------------------------------------------------------------


class TestFlankingIntegration:
    """フランキングスキルのシステム全体としての挙動を検証する."""

    def test_flanking_does_not_activate_during_retreat(self) -> None:
        """RETREAT 行動中はフランキングが発動せず EN が消費されないこと."""
        player, enemy, sim = _make_sim(player_flanking=3)
        sim.unit_resources[str(player.id)]["current_action"] = "RETREAT"
        en_before = sim.unit_resources[str(player.id)]["current_en"]

        with patch("app.engine.movement.random.random", return_value=0.0):
            sim._calculate_potential_field(player, enemy, dt=0.1)

        assert sim.unit_resources[str(player.id)]["current_en"] == pytest.approx(
            en_before
        )

    def test_flanking_level3_drains_more_en_per_step_than_level0(self) -> None:
        """Lv.3（常時発動）は Lv.0（常時不発動）より EN 消費が多いこと."""
        n_steps = 50
        dt = 0.1
        expected_per_step = FLANKING_ENERGY_COST_RATE * DEFAULT_BOOST_EN_COST * dt

        # Lv.3: random=0.0 で常に発動 (0.0 <= 0.90)
        player3, enemy3, sim3 = _make_sim(player_flanking=3, player_en=10000.0)
        en_start3 = sim3.unit_resources[str(player3.id)]["current_en"]
        with patch("app.engine.movement.random.random", return_value=0.0):
            for _ in range(n_steps):
                sim3._flanking_attraction(player3, enemy3, dt=dt)
        en_consumed3 = en_start3 - sim3.unit_resources[str(player3.id)]["current_en"]

        # Lv.0: random=1.0 で常に不発動 (1.0 > 0.05)
        player0, enemy0, sim0 = _make_sim(player_flanking=0, player_en=10000.0)
        en_start0 = sim0.unit_resources[str(player0.id)]["current_en"]
        with patch("app.engine.movement.random.random", return_value=1.0):
            for _ in range(n_steps):
                sim0._flanking_attraction(player0, enemy0, dt=dt)
        en_consumed0 = en_start0 - sim0.unit_resources[str(player0.id)]["current_en"]

        assert en_consumed3 == pytest.approx(n_steps * expected_per_step)
        assert en_consumed0 == pytest.approx(0.0)
        assert en_consumed3 > en_consumed0

    def test_ace_pilots_have_flanking_skills(self) -> None:
        """全エースパイロットに flanking スキルが定義されていること."""
        for ace in ACE_PILOTS:
            assert "skills" in ace, f"{ace['id']} に skills キーがない"
            assert "flanking" in ace["skills"], f"{ace['id']} に flanking スキルがない"
            level = ace["skills"]["flanking"]
            assert 2 <= level <= 3, f"{ace['id']} の flanking レベルが範囲外: {level}"

    def test_aggressive_ace_has_flanking_level3(self) -> None:
        """AGGRESSIVE エースは flanking Lv.3 を持つこと."""
        aggressive_aces = [a for a in ACE_PILOTS if a["personality"] == "AGGRESSIVE"]
        for ace in aggressive_aces:
            assert ace["skills"]["flanking"] == 3, (
                f"{ace['id']} は AGGRESSIVE なので flanking Lv.3 のはず"
            )

    def test_calculate_potential_field_accepts_dt(self) -> None:
        """_calculate_potential_field が dt に応じた EN を消費すること."""
        player, enemy, sim = _make_sim(player_flanking=3, player_en=2000.0)
        sim.unit_resources[str(player.id)]["current_action"] = "ATTACK"
        en_before = sim.unit_resources[str(player.id)]["current_en"]

        dt = 0.5
        expected_cost = FLANKING_ENERGY_COST_RATE * DEFAULT_BOOST_EN_COST * dt

        with patch("app.engine.movement.random.random", return_value=0.0):
            sim._calculate_potential_field(player, enemy, dt=dt)

        en_after = sim.unit_resources[str(player.id)]["current_en"]
        assert en_after == pytest.approx(en_before - expected_cost)

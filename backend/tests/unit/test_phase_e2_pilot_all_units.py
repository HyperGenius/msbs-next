"""Tests for Phase E-2: パイロット能力の全ユニット適用.

検証項目:
- _personality_pilot_stats() の各 personality 値
- 全 enemy が unit_pilot_stats に登録されること
- npc_pilot_stats オーバーライドが優先されること
- エースが通常 NPC より高い攻撃補正キャッシュを持つこと
- NPC vs NPC バトルがエラーなく完走すること
"""

from app.engine.calculator import PilotStats
from app.engine.simulation import BattleSimulator, _personality_pilot_stats
from app.models.models import MobileSuit, Vector3, Weapon  # noqa: F401

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_weapon(power: int = 100, weapon_type: str = "RANGED") -> Weapon:
    return Weapon(
        id="w1",
        name="Test Weapon",
        power=power,
        range=500,
        accuracy=100,
        weapon_type=weapon_type,
        is_melee=(weapon_type == "MELEE"),
        cooldown_sec=0.0,
    )


def _make_unit(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    armor: int = 0,
    hp: int = 1000,
    personality: str | None = None,
    is_ace: bool = False,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=hp,
        current_hp=hp,
        armor=armor,
        mobility=1.0,
        position=position,
        weapons=[_make_weapon()],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        personality=personality,
        is_ace=is_ace,
    )


# ---------------------------------------------------------------------------
# 1. _personality_pilot_stats()
# ---------------------------------------------------------------------------


class TestPersonalityPilotStats:
    """_personality_pilot_stats() の各 personality 値を検証する."""

    def test_aggressive_defaults(self) -> None:
        """AGGRESSIVE: mel=4, ref=4 が高い近接格闘型."""
        stats = _personality_pilot_stats("AGGRESSIVE")
        assert stats.sht == 3
        assert stats.mel == 4
        assert stats.intel == 2
        assert stats.ref == 4
        assert stats.tou == 3
        assert stats.luk == 1

    def test_cautious_defaults(self) -> None:
        """CAUTIOUS: intel=4 が高い慎重型."""
        stats = _personality_pilot_stats("CAUTIOUS")
        assert stats.sht == 3
        assert stats.mel == 1
        assert stats.intel == 4
        assert stats.ref == 2
        assert stats.tou == 2
        assert stats.luk == 3

    def test_sniper_defaults(self) -> None:
        """SNIPER: sht=6 が最大の射撃特化型."""
        stats = _personality_pilot_stats("SNIPER")
        assert stats.sht == 6
        assert stats.mel == 1
        assert stats.intel == 3
        assert stats.ref == 1
        assert stats.tou == 1
        assert stats.luk == 2

    def test_none_personality_returns_all_ones(self) -> None:
        """None: 全スタット 1 の素人パイロット."""
        stats = _personality_pilot_stats(None)
        assert stats.sht == 1
        assert stats.mel == 1
        assert stats.intel == 1
        assert stats.ref == 1
        assert stats.tou == 1
        assert stats.luk == 1

    def test_unknown_personality_falls_back_to_ones(self) -> None:
        """未定義 personality は None 扱いにフォールバックする."""
        stats = _personality_pilot_stats("BERSERKER")
        assert stats.sht == 1
        assert stats.mel == 1


# ---------------------------------------------------------------------------
# 2. unit_pilot_stats への NPC 全員登録
# ---------------------------------------------------------------------------


class TestUnitPilotStatsPopulation:
    """全 enemy が unit_pilot_stats に登録されることを検証する."""

    def test_all_enemies_registered_after_init(self) -> None:
        """複数 enemy が全員 unit_pilot_stats に登録される."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        e1 = _make_unit("E1", "ENEMY", "ET", Vector3(x=200, y=0, z=0))
        e2 = _make_unit("E2", "ENEMY", "ET", Vector3(x=400, y=0, z=0))
        sim = BattleSimulator(player, [e1, e2])

        assert str(e1.id) in sim.unit_pilot_stats
        assert str(e2.id) in sim.unit_pilot_stats

    def test_enemy_without_personality_gets_all_ones(self) -> None:
        """personality=None の NPC は全スタット 1 で登録される."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit(
            "E", "ENEMY", "ET", Vector3(x=200, y=0, z=0), personality=None
        )
        sim = BattleSimulator(player, [enemy])

        stats = sim.unit_pilot_stats[str(enemy.id)]
        assert stats.sht == 1
        assert stats.mel == 1

    def test_aggressive_enemy_gets_aggressive_stats(self) -> None:
        """AGGRESSIVE personality の NPC は mel=4 で登録される."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit(
            "E", "ENEMY", "ET", Vector3(x=200, y=0, z=0), personality="AGGRESSIVE"
        )
        sim = BattleSimulator(player, [enemy])

        stats = sim.unit_pilot_stats[str(enemy.id)]
        assert stats.mel == 4

    def test_sniper_enemy_gets_sniper_stats(self) -> None:
        """SNIPER personality の NPC は sht=6 で登録される."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit(
            "E", "ENEMY", "ET", Vector3(x=200, y=0, z=0), personality="SNIPER"
        )
        sim = BattleSimulator(player, [enemy])

        stats = sim.unit_pilot_stats[str(enemy.id)]
        assert stats.sht == 6

    def test_npc_pilot_stats_override_takes_precedence(self) -> None:
        """npc_pilot_stats で渡した値が personality デフォルトより優先される."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit(
            "E", "ENEMY", "ET", Vector3(x=200, y=0, z=0), personality="AGGRESSIVE"
        )
        ace_stats = PilotStats(sht=13, mel=11, intel=15, ref=14, tou=9, luk=12)
        sim = BattleSimulator(
            player, [enemy], npc_pilot_stats={str(enemy.id): ace_stats}
        )

        assert sim.unit_pilot_stats[str(enemy.id)] is ace_stats

    def test_player_stats_unchanged(self) -> None:
        """プレイヤーの unit_pilot_stats は player_pilot_stats と同一オブジェクト."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        enemy = _make_unit("E", "ENEMY", "ET", Vector3(x=200, y=0, z=0))
        pilot = PilotStats(sht=10, mel=5, intel=8, ref=6, tou=7, luk=4)
        sim = BattleSimulator(player, [enemy], player_pilot_stats=pilot)

        assert sim.unit_pilot_stats[str(player.id)] is pilot


# ---------------------------------------------------------------------------
# 3. エースのキャッシュが通常 NPC より高い
# ---------------------------------------------------------------------------


class TestAceStatsApplied:
    """エース NPC のステータスが combat multiplier cache に反映されることを検証する."""

    def test_ace_has_higher_ranged_attack_bonus_than_default(self) -> None:
        """高 SHT のエースは通常 NPC より cached_ranged_attack_bonus が大きい."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        ace = _make_unit("Ace", "ENEMY", "ET", Vector3(x=200, y=0, z=0), is_ace=True)
        normal = _make_unit("Normal", "ENEMY", "ET", Vector3(x=400, y=0, z=0))

        ace_stats = PilotStats(sht=13, mel=11, intel=15, ref=14, tou=9, luk=12)
        sim = BattleSimulator(
            player, [ace, normal], npc_pilot_stats={str(ace.id): ace_stats}
        )

        ace_bonus = sim.unit_resources[str(ace.id)]["cached_ranged_attack_bonus"]
        normal_bonus = sim.unit_resources[str(normal.id)]["cached_ranged_attack_bonus"]
        assert ace_bonus > normal_bonus


# ---------------------------------------------------------------------------
# 4. NPC vs NPC および全体的な戦闘
# ---------------------------------------------------------------------------


class TestNpcVsNpcCombatWithStats:
    """NPC 同士の戦闘がステータス適用済みで正しく動作することを検証する."""

    def test_sniper_npc_has_higher_ranged_bonus_than_default(self) -> None:
        """SNIPER (sht=6) は default NPC (sht=1) より cached_ranged_attack_bonus が大きい."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        sniper = _make_unit(
            "Sniper", "ENEMY", "ET", Vector3(x=200, y=0, z=0), personality="SNIPER"
        )
        default_npc = _make_unit(
            "Default", "ENEMY", "ET", Vector3(x=400, y=0, z=0), personality=None
        )
        sim = BattleSimulator(player, [sniper, default_npc])

        sniper_bonus = sim.unit_resources[str(sniper.id)]["cached_ranged_attack_bonus"]
        default_bonus = sim.unit_resources[str(default_npc.id)][
            "cached_ranged_attack_bonus"
        ]
        assert sniper_bonus > default_bonus

    def test_simulation_with_npc_stats_runs_without_error(self) -> None:
        """全 NPC にステータスが設定された状態でシミュレーションがエラーなく完走する."""
        player = _make_unit("P", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
        aggressive = _make_unit(
            "Agg", "ENEMY", "ET", Vector3(x=200, y=0, z=0), personality="AGGRESSIVE"
        )
        cautious = _make_unit(
            "Cau", "ENEMY", "ET", Vector3(x=300, y=0, z=50), personality="CAUTIOUS"
        )
        sim = BattleSimulator(player, [aggressive, cautious])

        for _ in range(50):
            if sim.is_finished:
                break
            sim.step()

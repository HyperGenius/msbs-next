"""Tests for hit-part determination and part-based HP model (Issue #503)."""

from unittest.mock import patch

from app.engine.combat import determine_hit_part
from app.engine.simulation import BattleSimulator
from app.models.models import (
    ALL_PART_NAMES,
    MobileSuit,
    PartState,
    Vector3,
    Weapon,
    build_default_parts,
)


def _make_unit(
    name: str = "Unit",
    side: str = "PLAYER",
    max_hp: int = 200,
    armor: int = 20,
    missing_parts: list[str] | None = None,
    position: Vector3 | None = None,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=max_hp,
        current_hp=max_hp,
        armor=armor,
        mobility=1.0,
        position=position or Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(id="w1", name="Rifle", power=30, range=400, accuracy=80),
        ],
        side=side,
        missing_parts=missing_parts or [],
    )


# ---------------------------------------------------------------------------
# build_default_parts / normalize_parts
# ---------------------------------------------------------------------------


class TestBuildDefaultParts:
    """build_default_parts() の単体テスト."""

    def test_generates_all_parts_by_default(self):
        """欠損部位を指定しない場合、全部位が生成される."""
        parts = build_default_parts(max_hp=200, armor=20)
        assert set(parts.keys()) == set(ALL_PART_NAMES)

    def test_part_hp_sums_to_overall_max_hp(self):
        """各部位のmax_hpの合計は機体全体のmax_hpと一致する（丸め誤差は許容）."""
        parts = build_default_parts(max_hp=200, armor=20)
        total = sum(p.max_hp for p in parts.values())
        assert abs(total - 200) <= len(ALL_PART_NAMES)

    def test_missing_parts_are_excluded(self):
        """missing_partsに指定した部位はpartsに含まれない."""
        parts = build_default_parts(
            max_hp=200, armor=20, missing_parts=["RIGHT_LEG", "LEFT_LEG"]
        )
        assert "RIGHT_LEG" not in parts
        assert "LEFT_LEG" not in parts
        assert "TORSO" in parts

    def test_current_hp_starts_at_max_hp(self):
        """生成直後は各部位のcurrent_hpはmax_hpと等しい."""
        parts = build_default_parts(max_hp=200, armor=20)
        for part in parts.values():
            assert part.current_hp == part.max_hp
            assert part.destroyed is False


class TestNormalizeParts:
    """MobileSuit.normalize_parts() の単体テスト."""

    def test_generates_parts_when_empty(self):
        """parts未設定の機体はnormalize_parts()で自動生成される."""
        unit = _make_unit()
        assert unit.parts == {}
        unit.normalize_parts()
        assert set(unit.parts.keys()) == set(ALL_PART_NAMES)

    def test_coerces_raw_dicts_into_partstate(self):
        """DBからのORM読み込みを模した生dictをPartStateへ変換する."""
        unit = _make_unit()
        unit.parts = {
            "HEAD": {"max_hp": 20, "current_hp": 10, "armor": 20, "destroyed": False}
        }
        unit.normalize_parts()
        assert isinstance(unit.parts["HEAD"], PartState)
        assert unit.parts["HEAD"].current_hp == 10

    def test_respects_missing_parts_on_generation(self):
        """missing_parts指定時、自動生成される部位からも除外される."""
        unit = _make_unit(missing_parts=["RIGHT_LEG", "LEFT_LEG"])
        unit.normalize_parts()
        assert "RIGHT_LEG" not in unit.parts
        assert "LEFT_LEG" not in unit.parts


# ---------------------------------------------------------------------------
# determine_hit_part
# ---------------------------------------------------------------------------


class TestDetermineHitPart:
    """determine_hit_part() の単体テスト (Issue #505 Phase 4 本実装)."""

    def test_returns_none_when_no_eligible_parts(self):
        """partsが空の場合はNoneを返す（撃破済み機体等のエッジケース）."""
        attacker = _make_unit(name="Attacker")
        target = _make_unit(name="Target")
        target.parts = {}
        weapon = attacker.weapons[0]
        assert determine_hit_part(attacker, target, weapon, "FRONT", 100.0) is None

    def test_only_returns_eligible_non_destroyed_parts(self):
        """欠損部位・破壊済み部位は選択されない."""
        attacker = _make_unit(name="Attacker")
        target = _make_unit(name="Target", missing_parts=["RIGHT_LEG", "LEFT_LEG"])
        target.normalize_parts()
        target.parts["HEAD"] = PartState(
            max_hp=20, current_hp=0, armor=20, destroyed=True
        )
        weapon = attacker.weapons[0]

        for _ in range(50):
            hit_part = determine_hit_part(attacker, target, weapon, "FRONT", 100.0)
            assert hit_part is not None
            assert hit_part not in ("RIGHT_LEG", "LEFT_LEG", "HEAD")
            assert hit_part in target.parts

    def test_unknown_sector_falls_back_to_front_side_weights(self):
        """未知のセクタ文字列を渡してもKeyErrorにならずFRONT_SIDE相当の重みで選択される."""
        attacker = _make_unit(name="Attacker")
        target = _make_unit(name="Target")
        target.normalize_parts()
        weapon = attacker.weapons[0]
        hit_part = determine_hit_part(attacker, target, weapon, "UNKNOWN_SECTOR", 100.0)
        assert hit_part in target.parts

    def test_weapon_aim_distribution_biases_hit_part_selection(self):
        """武器のaim_distributionを頭部100%にすると、頭部への命中が支配的になる."""
        attacker = _make_unit(name="Attacker")
        target = _make_unit(name="Target")
        target.normalize_parts()
        weapon = Weapon(
            id="head_hunter",
            name="Head Hunter",
            power=10,
            range=100,
            accuracy=100,
            aim_distribution={
                "HEAD": 1.0,
                "TORSO": 0.0,
                "RIGHT_ARM": 0.0,
                "LEFT_ARM": 0.0,
                "RIGHT_LEG": 0.0,
                "LEFT_LEG": 0.0,
            },
        )

        # 距離0（減衰なし）なら常に頭部を狙う
        results = {
            determine_hit_part(attacker, target, weapon, "FRONT_SIDE", 0.0)
            for _ in range(50)
        }
        assert results == {"HEAD"}

    def test_distance_decay_shifts_high_difficulty_part_hits_toward_torso(self):
        """遠距離では頭部狙いの武器でも、実際の命中は胴体などへ寄る."""
        attacker = _make_unit(name="Attacker")
        target = _make_unit(name="Target")
        target.normalize_parts()
        weapon = Weapon(
            id="head_hunter",
            name="Head Hunter",
            power=10,
            range=100,
            accuracy=100,
            aim_distribution={
                "HEAD": 0.5,
                "TORSO": 0.5,
                "RIGHT_ARM": 0.0,
                "LEFT_ARM": 0.0,
                "RIGHT_LEG": 0.0,
                "LEFT_LEG": 0.0,
            },
        )

        head_hits_near = sum(
            1
            for _ in range(400)
            if determine_hit_part(attacker, target, weapon, "FRONT_SIDE", 0.0) == "HEAD"
        )
        head_hits_far = sum(
            1
            for _ in range(400)
            if determine_hit_part(attacker, target, weapon, "FRONT_SIDE", 2000.0)
            == "HEAD"
        )

        # 遠距離では難易度の高い部位(頭部)への実命中割合が近距離より明確に下がる
        assert head_hits_far < head_hits_near

    def test_missing_part_allocation_is_proportionally_redistributed(self):
        """狙う部位配分に含まれる欠損部位の配分は、実在部位へ自動的に再配分される."""
        attacker = _make_unit(name="Attacker")
        target = _make_unit(name="Target", missing_parts=["RIGHT_LEG", "LEFT_LEG"])
        target.normalize_parts()
        # RIGHT_LEG/LEFT_LEGにも配分しているが、targetには存在しない
        weapon = Weapon(
            id="balanced",
            name="Balanced",
            power=10,
            range=100,
            accuracy=100,
            aim_distribution={
                "HEAD": 0.0,
                "TORSO": 0.0,
                "RIGHT_ARM": 0.0,
                "LEFT_ARM": 0.0,
                "RIGHT_LEG": 0.5,
                "LEFT_LEG": 0.5,
            },
        )

        # 全配分が欠損部位に割り当てられているため、安全策の均等重みにフォールバックする
        results = {
            determine_hit_part(attacker, target, weapon, "FRONT_SIDE", 100.0)
            for _ in range(80)
        }
        assert results.issubset(set(target.parts.keys()))
        assert len(results) > 1

    def test_no_aim_distribution_falls_back_to_default(self):
        """武器にaim_distributionが無い（旧データ等）場合はデフォルト配分で選択される."""
        attacker = _make_unit(name="Attacker")
        target = _make_unit(name="Target")
        target.normalize_parts()
        weapon = attacker.weapons[0]
        weapon.aim_distribution = {}

        hit_part = determine_hit_part(attacker, target, weapon, "FRONT_SIDE", 100.0)
        assert hit_part in target.parts


# ---------------------------------------------------------------------------
# 統合: _process_hit を通じた部位ダメージ適用
# ---------------------------------------------------------------------------


class TestPartDamageApplication:
    """CombatMixin._process_hit() が命中部位に実際にダメージを適用することを検証する."""

    def test_hit_reduces_hit_part_hp_without_affecting_overall_hp_formula(self):
        """命中時、決定された部位のcurrent_hpが減少し、全体HPも従来通り減少する."""
        player = _make_unit(
            name="Player", side="PLAYER", position=Vector3(x=0, y=0, z=0)
        )
        enemy = _make_unit(
            name="Enemy", side="ENEMY", position=Vector3(x=100, y=0, z=0)
        )
        sim = BattleSimulator(player, [enemy])
        weapon = enemy.weapons[0]
        snapshot = Vector3.from_numpy(enemy.position.to_numpy())

        overall_hp_before = player.current_hp
        parts_before = {k: v.current_hp for k, v in player.parts.items()}

        with patch("app.engine.combat.determine_hit_part", return_value="TORSO"):
            with patch(
                "random.random", return_value=0.99
            ):  # クリティカル・完全回避を回避
                sim._process_hit(
                    enemy,
                    player,
                    weapon,
                    "test attack",
                    snapshot,
                    attack_sector="FRONT_SIDE",
                    distance=100.0,
                )

        assert player.current_hp < overall_hp_before
        damage_dealt = overall_hp_before - player.current_hp
        assert player.parts["TORSO"].current_hp == parts_before["TORSO"] - damage_dealt
        # 他の部位はダメージを受けない
        for name, hp_before in parts_before.items():
            if name != "TORSO":
                assert player.parts[name].current_hp == hp_before

    def test_part_hp_does_not_go_negative_and_marks_destroyed(self):
        """部位の残りHPを超えるダメージを受けても0未満にならず、destroyedがTrueになる."""
        player = _make_unit(name="Player", side="PLAYER", max_hp=1000, armor=0)
        enemy = _make_unit(name="Enemy", side="ENEMY", max_hp=1000, armor=0)
        sim = BattleSimulator(player, [enemy])
        heavy_weapon = Weapon(
            id="w_heavy", name="Heavy Cannon", power=9999, range=400, accuracy=100
        )
        snapshot = Vector3.from_numpy(enemy.position.to_numpy())

        with patch("app.engine.combat.determine_hit_part", return_value="HEAD"):
            with patch("random.random", return_value=0.99):
                sim._process_hit(
                    enemy,
                    player,
                    heavy_weapon,
                    "test attack",
                    snapshot,
                    attack_sector="FRONT_SIDE",
                    distance=100.0,
                )

        assert player.parts["HEAD"].current_hp == 0
        assert player.parts["HEAD"].destroyed is True

    def test_missing_parts_never_appear_as_hit_part_over_many_attacks(self):
        """欠損部位を持つ機体への実戦闘ログで、欠損部位が一度もhit_partに現れない."""
        player = _make_unit(
            name="Player",
            side="PLAYER",
            position=Vector3(x=0, y=0, z=0),
            missing_parts=["RIGHT_LEG", "LEFT_LEG"],
        )
        enemy = _make_unit(name="Enemy", side="ENEMY", position=Vector3(x=80, y=0, z=0))
        sim = BattleSimulator(player, [enemy])

        for _ in range(80):
            if sim.is_finished:
                break
            sim.step()

        hit_parts_seen = {
            log.hit_part
            for log in sim.logs
            if log.action_type == "ATTACK" and log.target_id == player.id
        }
        assert "RIGHT_LEG" not in hit_parts_seen
        assert "LEFT_LEG" not in hit_parts_seen


class TestWeaponSlotRoleLogging:
    """CombatMixin._process_hit() が武器スロット部位ロールをログへ記録することを検証する (Issue #504)."""

    def test_attack_log_carries_weapon_slot_role_of_firing_weapon(self):
        """actor.weapons内でのindexに対応する部位ロールがATTACKログに記録される."""
        player = _make_unit(
            name="Player", side="PLAYER", position=Vector3(x=0, y=0, z=0)
        )
        enemy = _make_unit(
            name="Enemy", side="ENEMY", position=Vector3(x=100, y=0, z=0)
        )
        enemy.weapons = [
            Weapon(id="right_w", name="Right Rifle", power=30, range=400, accuracy=80),
            Weapon(id="left_w", name="Left Rifle", power=30, range=400, accuracy=80),
        ]
        sim = BattleSimulator(player, [enemy])
        snapshot = Vector3.from_numpy(enemy.position.to_numpy())

        with patch("app.engine.combat.determine_hit_part", return_value="TORSO"):
            with patch("random.random", return_value=0.99):
                sim._process_hit(
                    enemy,
                    player,
                    enemy.weapons[1],
                    "test attack",
                    snapshot,
                    attack_sector="FRONT_SIDE",
                    distance=100.0,
                )

        attack_logs = [log for log in sim.logs if log.action_type == "ATTACK"]
        assert len(attack_logs) == 1
        assert attack_logs[0].weapon_slot_role == "LEFT_ARM"

    def test_attack_log_weapon_slot_role_is_none_when_weapon_not_in_actor_weapons(self):
        """actor.weaponsに存在しない武器（テスト用ダミー等）の場合はNoneになる."""
        player = _make_unit(
            name="Player", side="PLAYER", position=Vector3(x=0, y=0, z=0)
        )
        enemy = _make_unit(
            name="Enemy", side="ENEMY", position=Vector3(x=100, y=0, z=0)
        )
        sim = BattleSimulator(player, [enemy])
        snapshot = Vector3.from_numpy(enemy.position.to_numpy())
        unrelated_weapon = Weapon(
            id="not_in_list", name="Unrelated", power=30, range=400, accuracy=80
        )

        with patch("app.engine.combat.determine_hit_part", return_value="TORSO"):
            with patch("random.random", return_value=0.99):
                sim._process_hit(
                    enemy,
                    player,
                    unrelated_weapon,
                    "test attack",
                    snapshot,
                    attack_sector="FRONT_SIDE",
                    distance=100.0,
                )

        attack_logs = [log for log in sim.logs if log.action_type == "ATTACK"]
        assert attack_logs[0].weapon_slot_role is None

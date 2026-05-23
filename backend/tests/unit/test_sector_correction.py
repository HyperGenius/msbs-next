"""Phase E-3: 攻撃角度セクタ補正のテスト."""

import math

import numpy as np
import pytest

from app.engine.combat import calculate_attack_sector
from app.engine.constants import SECTOR_ACCURACY_MODIFIERS
from app.engine.simulation import BattleSimulator
from app.models.models import BattleLog, MobileSuit, Vector3, Weapon

# ---------------------------------------------------------------------------
# テストヘルパー
# ---------------------------------------------------------------------------


def _make_weapon(power: int = 100, accuracy: int = 80) -> Weapon:
    return Weapon(
        id="test_weapon",
        name="Test Beam Rifle",
        power=power,
        range=600.0,
        accuracy=accuracy,
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
    hp: int = 1000,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=hp,
        current_hp=hp,
        armor=0,
        mobility=0.0,
        position=position,
        weapons=[_make_weapon()],
        side=side,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        max_speed=0.0,
        acceleration=0.0,
        sensor_range=10000.0,
    )


# ---------------------------------------------------------------------------
# calculate_attack_sector ユニットテスト
# ---------------------------------------------------------------------------


def _pos(x: float, z: float) -> np.ndarray:
    return np.array([x, 0.0, z])


class TestCalculateAttackSector:
    """calculate_attack_sector() の各セクタ判定を検証する."""

    def test_front_sector(self) -> None:
        """正面攻撃 → FRONT."""
        # ターゲットは (0,0,0) で heading=0 (正の X 方向を向く)
        # 攻撃者はターゲットの正面 (x 正方向) にいる → FRONT
        sector = calculate_attack_sector(
            attacker_pos=_pos(100.0, 0.0),
            target_pos=_pos(0.0, 0.0),
            target_heading_deg=0.0,
        )
        assert sector == "FRONT"

    def test_rear_sector(self) -> None:
        """背後攻撃 → REAR."""
        # 攻撃者はターゲットの背後 (x 負方向) にいる → REAR
        sector = calculate_attack_sector(
            attacker_pos=_pos(-100.0, 0.0),
            target_pos=_pos(0.0, 0.0),
            target_heading_deg=0.0,
        )
        assert sector == "REAR"

    def test_front_side_sector(self) -> None:
        """側面前 → FRONT_SIDE."""
        # heading=0 (X 方向), 攻撃者は真横 (Z=100) → 90° → FRONT_SIDE
        sector = calculate_attack_sector(
            attacker_pos=_pos(0.0, 100.0),
            target_pos=_pos(0.0, 0.0),
            target_heading_deg=0.0,
        )
        assert sector == "FRONT_SIDE"

    def test_rear_side_sector(self) -> None:
        """側面後 → REAR_SIDE."""
        # heading=0, 攻撃者は 135° 方向 → REAR_SIDE
        angle_rad = math.radians(135)
        attacker_x = math.cos(angle_rad) * 100.0  # 相対ベクトル (dx=attacker-target)
        attacker_z = math.sin(angle_rad) * 100.0
        sector = calculate_attack_sector(
            attacker_pos=_pos(attacker_x, attacker_z),
            target_pos=_pos(0.0, 0.0),
            target_heading_deg=0.0,
        )
        assert sector == "REAR_SIDE"

    def test_boundary_front_to_front_side(self) -> None:
        """60° ちょうど → FRONT (境界値)."""
        angle_rad = math.radians(60)
        attacker_x = math.cos(angle_rad) * 100.0
        attacker_z = math.sin(angle_rad) * 100.0
        sector = calculate_attack_sector(
            attacker_pos=_pos(attacker_x, attacker_z),
            target_pos=_pos(0.0, 0.0),
            target_heading_deg=0.0,
        )
        assert sector == "FRONT"

    def test_heading_rotated(self) -> None:
        """ターゲットの heading が 180° のとき、攻撃者が x 正方向 → REAR."""
        # heading=180° → ターゲットは x 負方向を向く
        # 攻撃者が x 正方向 (背後になる) → REAR
        sector = calculate_attack_sector(
            attacker_pos=_pos(100.0, 0.0),
            target_pos=_pos(0.0, 0.0),
            target_heading_deg=180.0,
        )
        assert sector == "REAR"


# ---------------------------------------------------------------------------
# セクタ命中率補正の統合テスト
# ---------------------------------------------------------------------------


class TestSectorAccuracyModifier:
    """セクタ補正が命中率に適用されることを検証する."""

    def _setup_sim(
        self, player_pos: Vector3, enemy_pos: Vector3, enemy_heading: float = 0.0
    ) -> tuple[BattleSimulator, MobileSuit, MobileSuit]:
        player = _make_unit("Player", "PLAYER", player_pos)
        enemy = _make_unit("Enemy", "ENEMY", enemy_pos)
        sim = BattleSimulator(player, [enemy])
        # エネミーの body_heading_deg を手動設定
        sim.unit_resources[str(enemy.id)]["body_heading_deg"] = enemy_heading
        return sim, player, enemy

    def test_front_hit_chance_lower_than_rear(self) -> None:
        """正面攻撃の命中率は背後攻撃より低い."""
        weapon = _make_weapon()
        distance = 100.0

        # 正面攻撃: player(200,0,0) → enemy(0,0,0) heading=0 → FRONT
        sim_front, player_front, enemy_front = self._setup_sim(
            Vector3(x=200, y=0, z=0),
            Vector3(x=0, y=0, z=0),
            enemy_heading=0.0,
        )
        hit_front, _, sector_front = sim_front._calculate_hit_chance(
            player_front, enemy_front, weapon, distance
        )
        assert sector_front == "FRONT"

        # 背後攻撃: player(-200,0,0) → enemy(0,0,0) heading=0 → REAR
        sim_rear, player_rear, enemy_rear = self._setup_sim(
            Vector3(x=-200, y=0, z=0),
            Vector3(x=0, y=0, z=0),
            enemy_heading=0.0,
        )
        hit_rear, _, sector_rear = sim_rear._calculate_hit_chance(
            player_rear, enemy_rear, weapon, distance
        )
        assert sector_rear == "REAR"

        assert hit_front < hit_rear

    def test_sector_accuracy_modifier_applied(self) -> None:
        """FRONT の命中率が FRONT_SIDE の命中率の 0.35 倍であることを確認する.

        クランプを避けるため accuracy を低く設定し、どちらも < 100 になることを保証する。
        """
        weapon = _make_weapon(accuracy=30)  # 低命中率で 100% クランプを回避
        distance = 300.0

        sim_front, pf, ef = self._setup_sim(
            Vector3(x=1, y=0, z=0),
            Vector3(x=0, y=0, z=0),
            enemy_heading=0.0,
        )
        hit_front, _, sector_front = sim_front._calculate_hit_chance(
            pf, ef, weapon, distance
        )
        assert sector_front == "FRONT"

        sim_side, ps, es = self._setup_sim(
            Vector3(x=0, y=0, z=1),
            Vector3(x=0, y=0, z=0),
            enemy_heading=0.0,
        )
        hit_side, _, sector_side = sim_side._calculate_hit_chance(
            ps, es, weapon, distance
        )
        assert sector_side == "FRONT_SIDE"

        # FRONT_SIDE はセクタ補正なし (×1.0); FRONT は ×0.35
        expected_ratio = (
            SECTOR_ACCURACY_MODIFIERS["FRONT"] / SECTOR_ACCURACY_MODIFIERS["FRONT_SIDE"]
        )
        actual_ratio = hit_front / hit_side
        assert actual_ratio == pytest.approx(expected_ratio, rel=1e-4)


# ---------------------------------------------------------------------------
# セクタダメージ補正の統合テスト
# ---------------------------------------------------------------------------


class TestSectorDamageModifier:
    """セクタ補正がダメージに適用されることを検証する."""

    def test_rear_damage_higher_than_front_side(self) -> None:
        """背後攻撃のダメージは FRONT_SIDE より高い."""
        # 多数回シミュレーションして平均ダメージを比較
        player_pos_rear = Vector3(x=-200, y=0, z=0)  # REAR セクタ
        player_pos_side = Vector3(x=0, y=0, z=200)  # FRONT_SIDE セクタ
        enemy_pos = Vector3(x=0, y=0, z=0)

        def run_attacks(player_pos: Vector3, n: int = 100) -> float:
            total_damage = 0
            for _ in range(n):
                player = _make_unit("P", "PLAYER", player_pos)
                enemy = _make_unit("E", "ENEMY", enemy_pos, hp=999999)
                sim = BattleSimulator(player, [enemy])
                sim.unit_resources[str(enemy.id)]["body_heading_deg"] = 0.0
                for _step in range(3):
                    sim.step()
                damage_logs: list[BattleLog] = [
                    log for log in sim.logs if log.action_type == "ATTACK"
                ]
                total_damage += sum(log.damage or 0 for log in damage_logs)
            return total_damage

        total_rear = run_attacks(player_pos_rear)
        total_side = run_attacks(player_pos_side)
        # REAR (1.5x) > FRONT_SIDE (1.0x)
        assert total_rear > total_side


# ---------------------------------------------------------------------------
# BattleLog の attack_sector 記録テスト
# ---------------------------------------------------------------------------


def test_battle_log_records_attack_sector() -> None:
    """命中ログに attack_sector が記録されること."""
    # player は enemy の背後から攻撃 → REAR
    player = _make_unit("Player", "PLAYER", Vector3(x=-500, y=0, z=0), hp=10000)
    enemy = _make_unit("Enemy", "ENEMY", Vector3(x=0, y=0, z=0), hp=1)

    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(enemy.id)]["body_heading_deg"] = 0.0

    max_steps = 50
    for _ in range(max_steps):
        if sim.is_finished:
            break
        sim.step()

    attack_logs = [log for log in sim.logs if log.action_type == "ATTACK"]
    assert len(attack_logs) > 0, "少なくとも 1 回の命中ログがあること"

    for log in attack_logs:
        assert log.attack_sector is not None, "attack_sector が None でないこと"
        assert log.attack_sector in ("FRONT", "FRONT_SIDE", "REAR_SIDE", "REAR"), (
            f"attack_sector の値が不正: {log.attack_sector}"
        )


def test_miss_log_does_not_have_attack_sector() -> None:
    """ミスログには attack_sector が記録されないこと."""
    # 命中率を極限まで下げて MISS を強制させる（正面 + 距離遠い）
    player = _make_unit("Player", "PLAYER", Vector3(x=10000, y=0, z=0), hp=10000)
    enemy = _make_unit("Enemy", "ENEMY", Vector3(x=0, y=0, z=0), hp=10000)

    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(enemy.id)]["body_heading_deg"] = 0.0

    max_steps = 5
    for _ in range(max_steps):
        sim.step()

    miss_logs = [log for log in sim.logs if log.action_type == "MISS"]
    for log in miss_logs:
        assert log.attack_sector is None, (
            "MISS ログには attack_sector が記録されないこと"
        )

# backend/app/engine/movement.py
"""移動・慣性・ポテンシャルフィールド処理のミックスイン."""

import math
import random

import numpy as np

from app.engine.constants import (
    ALLY_REPULSION_RADIUS,
    BOUNDARY_MARGIN,
    DEFAULT_BOOST_COOLDOWN,
    DEFAULT_BOOST_MAX_DURATION,
    DEFAULT_BOOST_SPEED_MULTIPLIER,
    HIGH_THREAT_THRESHOLD,
    MELEE_BOOST_ARRIVAL_RANGE,
    MOVE_LOG_MIN_DIST,
    OBSTACLE_MARGIN,
    OBSTACLE_REPULSION_COEFF,
    RETREAT_ATTRACTION_COEFF,
    SPECIAL_ENVIRONMENT_EFFECTS,
    TERRAIN_ADAPTABILITY_MODIFIERS,
)
from app.models.models import BattleLog, MobileSuit, RetreatPoint, Vector3


class MovementMixin:
    """移動・慣性・ポテンシャルフィールド処理のミックスイン."""

    # BattleSimulator が提供するインスタンス属性 (mypy 向け型宣言のみ; 実体は simulation.py)
    units: list[MobileSuit]

    def _threat_enemy_repulsion(
        self,
        unit: MobileSuit,
        pos_unit: np.ndarray,
        weapon_range: float,
    ) -> np.ndarray:
        """高脅威敵（自機射程外）への斥力ベクトルを返す."""
        force = np.zeros(3)
        all_enemies = [
            u
            for u in self.units
            if u.current_hp > 0 and u.team_id != unit.team_id  # type: ignore[attr-defined]
        ]
        for enemy in all_enemies:
            vec_to_enemy = enemy.position.to_numpy() - pos_unit
            dist = float(np.linalg.norm(vec_to_enemy))
            threat_score = self._calculate_attack_power(enemy) / max(  # type: ignore[attr-defined]
                1.0, float(unit.max_hp)
            )
            if threat_score > HIGH_THREAT_THRESHOLD and dist > weapon_range:
                force += 1.5 * (-vec_to_enemy) / max(dist, 1.0)
        return force

    def _ally_repulsion(self, unit: MobileSuit, pos_unit: np.ndarray) -> np.ndarray:
        """味方ユニットへの弱い斥力ベクトルを返す（密集防止）."""
        force = np.zeros(3)
        allies = [
            u
            for u in self.units  # type: ignore[attr-defined]
            if u.current_hp > 0 and u.team_id == unit.team_id and u.id != unit.id
        ]
        for ally in allies:
            vec_to_ally = ally.position.to_numpy() - pos_unit
            dist = float(np.linalg.norm(vec_to_ally))
            if 0 < dist <= ALLY_REPULSION_RADIUS:
                force += 0.8 * (-vec_to_ally) / max(dist, 1.0)
        return force

    def _boundary_repulsion(self, pos_unit: np.ndarray) -> np.ndarray:
        """マップ境界への斥力ベクトルを返す."""
        force = np.zeros(3)
        map_min, map_max = self.map_bounds  # type: ignore[attr-defined]
        axes = [(0, np.array([1.0, 0.0, 0.0])), (2, np.array([0.0, 0.0, 1.0]))]
        for axis, direction in axes:
            dist_min = pos_unit[axis] - map_min
            if dist_min < BOUNDARY_MARGIN:
                force += 3.0 * direction / max(dist_min, 1.0)
            dist_max = map_max - pos_unit[axis]
            if dist_max < BOUNDARY_MARGIN:
                force += 3.0 * (-direction) / max(dist_max, 1.0)
        return force

    def _attack_target_attraction(
        self, unit: MobileSuit, pos_unit: np.ndarray, target: MobileSuit | None = None
    ) -> np.ndarray:
        """攻撃ターゲットへの引力ベクトルを返す（ATTACK行動時）."""
        force = np.zeros(3)
        if target is not None:
            vec = target.position.to_numpy() - pos_unit
            dist = float(np.linalg.norm(vec))
            if dist > 0:
                force += 2.0 * vec / dist
        return force

    def _closest_enemy_attraction(
        self, unit: MobileSuit, pos_unit: np.ndarray
    ) -> np.ndarray:
        """最近敵への引力ベクトルを返す（MOVE行動時）."""
        force = np.zeros(3)
        enemies = [
            u
            for u in self.units
            if u.current_hp > 0 and u.team_id != unit.team_id  # type: ignore[attr-defined]
        ]
        if enemies:
            closest_enemy = min(
                enemies,
                key=lambda e: float(np.linalg.norm(e.position.to_numpy() - pos_unit)),
            )
            vec = closest_enemy.position.to_numpy() - pos_unit
            dist = float(np.linalg.norm(vec))
            if dist > 0:
                force += 1.5 * vec / dist
        return force

    def _retreat_points_attraction(
        self, pos_unit: np.ndarray, retreat_points: list[RetreatPoint]
    ) -> np.ndarray:
        """撤退ポイントへの強引力ベクトルを返す（RETREAT行動時）."""
        force = np.zeros(3)
        for rp in retreat_points:
            rp_pos = rp.position.to_numpy()
            vec = rp_pos - pos_unit
            dist = float(np.linalg.norm(vec))
            if dist > 0:
                force += RETREAT_ATTRACTION_COEFF * vec / dist
        return force

    def _calculate_potential_field(
        self,
        unit: MobileSuit,
        target: MobileSuit | None = None,
        retreat_points: list[RetreatPoint] | None = None,
    ) -> np.ndarray:
        """ポテンシャルフィールド法による目標方向ベクトルを計算する.

        攻撃ターゲット・脅威敵・味方・マップ境界などの各ソースからの
        引力・斥力を合成して正規化した 3D 単位ベクトルを返す。
        合算結果がゼロベクトルになった場合はランダム方向を返し
        ローカルミニマムを回避する。

        Args:
            unit: 移動するユニット
            target: 攻撃対象ユニット（ATTACK 行動時に強引力を与える）
            retreat_points: 撤退ポイントのリスト（Phase 3-3 用）

        Returns:
            3D 単位ベクトル（XZ 平面）
        """
        if retreat_points is None:
            retreat_points = []

        pos_unit = unit.position.to_numpy()
        unit_id = str(unit.id)
        current_action = self.unit_resources[unit_id].get("current_action", "MOVE")  # type: ignore[attr-defined]
        total_force = np.zeros(3)

        # 1. 攻撃ターゲットへの引力 (ATTACK 行動かつターゲット選択済みの場合)
        if current_action == "ATTACK":
            total_force += self._attack_target_attraction(unit, pos_unit, target)

        # 2. MOVE 行動時の最近敵への引力（RETREAT 時は撤退ポイントへ向かうため除外）
        if current_action == "MOVE":
            total_force += self._closest_enemy_attraction(unit, pos_unit)

        # 3. 高脅威敵（自機射程外）への斥力
        weapon = unit.get_active_weapon()
        weapon_range = float(weapon.range) if weapon else 0.0
        total_force += self._threat_enemy_repulsion(unit, pos_unit, weapon_range)

        # 4. 味方ユニットへの弱い斥力 (ALLY_REPULSION_RADIUS 以内)
        total_force += self._ally_repulsion(unit, pos_unit)

        # 5. マップ境界への斥力 (BOUNDARY_MARGIN 以内)
        total_force += self._boundary_repulsion(pos_unit)

        # 6. 撤退ポイントへの強引力 (RETREAT 行動時のみ、Phase 3-3)
        if current_action == "RETREAT":
            applicable_rps = [
                rp
                for rp in retreat_points
                if rp.team_id is None or rp.team_id == unit.team_id
            ]
            total_force += self._retreat_points_attraction(pos_unit, applicable_rps)

        # 7. 障害物への斥力 (Phase A — LOS システム)
        for obs in self.obstacles:  # type: ignore[attr-defined]
            obs_pos = np.array([obs.position.x, obs.position.y, obs.position.z])
            obs_dist = float(np.linalg.norm(pos_unit - obs_pos))
            if obs_dist <= obs.radius + OBSTACLE_MARGIN:
                away_vec = (pos_unit - obs_pos) / max(obs_dist, 1.0)
                total_force += OBSTACLE_REPULSION_COEFF * away_vec

        # 正規化 — ゼロベクトル時はランダム方向でローカルミニマムを回避
        total_force[1] = 0.0  # Y 成分を XZ 平面に固定
        magnitude = float(np.linalg.norm(total_force))
        if magnitude < 1e-6:
            angle = random.uniform(0.0, 2.0 * math.pi)
            return np.array([math.cos(angle), 0.0, math.sin(angle)])
        return total_force / magnitude

    def _process_movement(
        self,
        actor: MobileSuit,
        pos_actor: np.ndarray,
        pos_target: np.ndarray,
        diff_vector: np.ndarray,
        distance: float,
        dt: float = 0.1,
        target: MobileSuit | None = None,
    ) -> None:
        """移動処理を実行する（ポテンシャルフィールドによる自律移動）."""
        if distance == 0:
            return

        # ポテンシャルフィールドで目標方向を算出し、慣性モデルで位置・速度を更新
        desired_direction = self._calculate_potential_field(
            actor,
            target,
            self.retreat_points,  # type: ignore[attr-defined]
        )
        self._apply_inertia(actor, desired_direction, dt)

        # MOVE_LOG_MIN_DIST 以上の残距離のステップのみログ出力（ログ量削減）
        if distance >= MOVE_LOG_MIN_DIST:
            self.logs.append(  # type: ignore[attr-defined]
                BattleLog(
                    timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                    actor_id=actor.id,
                    action_type="MOVE",
                    message=f"{self._format_actor_name(actor)}が移動中 (残距離: {int(distance)}m)",  # type: ignore[attr-defined]
                    position_snapshot=actor.position,
                    velocity_snapshot=Vector3.from_numpy(
                        self.unit_resources[str(actor.id)]["velocity_vec"]  # type: ignore[attr-defined]
                    ),
                )
            )

    def _apply_inertia(
        self,
        actor: MobileSuit,
        desired_direction: np.ndarray,
        dt: float,
    ) -> None:
        """慣性モデルによる速度・位置更新.

        旋回制限・加速制限を適用したうえで速度ベクトルと位置を更新する。
        `unit_resources` の `velocity_vec` / `movement_heading_deg` を更新し、
        `actor.position` を書き換える。

        Args:
            actor: 移動対象ユニット
            desired_direction: 目標方向の単位ベクトル (3D, XZ平面)
            dt: 時間ステップ幅 (s)
        """
        unit_id = str(actor.id)
        resources = self.unit_resources[unit_id]  # type: ignore[attr-defined]

        current_velocity: np.ndarray = resources["velocity_vec"]
        current_heading: float = resources["movement_heading_deg"]

        # 目標方向のヘッディング角度を計算 (XZ 平面での atan2)
        desired_heading = math.degrees(
            math.atan2(float(desired_direction[2]), float(desired_direction[0]))
        )

        # 1. 旋回制限
        max_rotation = actor.max_turn_rate * dt
        angular_diff = ((desired_heading - current_heading + 180) % 360) - 180
        actual_rotation = max(-max_rotation, min(max_rotation, angular_diff))
        new_heading = current_heading + actual_rotation

        # 2. 加速・減速制限
        current_speed = float(np.linalg.norm(current_velocity))
        terrain_modifier = self._get_terrain_modifier(actor)

        # ブースト中は effective_max_speed を boost_speed_multiplier 倍にする (Phase B)
        boost_multiplier = getattr(
            actor, "boost_speed_multiplier", DEFAULT_BOOST_SPEED_MULTIPLIER
        )
        if resources.get("is_boosting", False):
            effective_max_speed = actor.max_speed * boost_multiplier * terrain_modifier
        else:
            effective_max_speed = actor.max_speed * terrain_modifier

        if current_speed < effective_max_speed:
            new_speed = min(
                current_speed + actor.acceleration * dt, effective_max_speed
            )
        else:
            new_speed = max(current_speed - actor.deceleration * dt, 0.0)

        # 新しい方向ベクトルと速度ベクトルを計算 (XZ 平面、Y=0)
        heading_rad = math.radians(new_heading)
        new_direction = np.array([math.cos(heading_rad), 0.0, math.sin(heading_rad)])
        new_velocity = new_direction * new_speed

        # 3. 位置更新
        pos_actor = actor.position.to_numpy()
        new_pos = pos_actor + new_velocity * dt

        # unit_resources を更新
        resources["velocity_vec"] = new_velocity
        resources["movement_heading_deg"] = new_heading

        # 位置を更新
        actor.position = Vector3.from_numpy(new_pos)

    def _get_terrain_modifier(self, unit: MobileSuit) -> float:
        """地形適正による補正係数を取得."""
        # 地形適正を取得
        terrain_adaptability = getattr(unit, "terrain_adaptability", {})
        adaptability_grade = terrain_adaptability.get(self.environment, "A")  # type: ignore[attr-defined]

        # 補正係数を返す
        modifier = TERRAIN_ADAPTABILITY_MODIFIERS.get(adaptability_grade, 1.0)

        # 重力井戸効果: 機動性をさらに低下
        if "GRAVITY_WELL" in self.special_effects:  # type: ignore[attr-defined]
            gravity = SPECIAL_ENVIRONMENT_EFFECTS["GRAVITY_WELL"]
            modifier *= gravity["mobility_multiplier"]

        return modifier

    def _check_boost_cancel(
        self,
        actor: MobileSuit,
        target: MobileSuit | None,
        dt: float,
    ) -> bool:
        """ブーストキャンセル判定を実行し、キャンセルが必要なら状態を更新する (Phase B).

        以下いずれかの条件を満たすとブーストを終了させる:
        1. boost_elapsed >= boost_max_duration
        2. current_en <= 0 (EN 切れ)
        3. ターゲットが MELEE_BOOST_ARRIVAL_RANGE (100m) 以内
        4. 慣性考慮キャンセル: 停止予想位置から遠距離武器の max_range 以内に入っている

        Args:
            actor: ブースト中のユニット
            target: 現在のターゲット（None の場合は条件 3/4 をスキップ）
            dt: 時間ステップ幅 (s)

        Returns:
            True: ブーストをキャンセルした（is_boosting を False に変更）
            False: ブーストを継続
        """
        unit_id = str(actor.id)
        resources = self.unit_resources[unit_id]  # type: ignore[attr-defined]

        if not resources.get("is_boosting", False):
            return False

        boost_max_duration = getattr(
            actor, "boost_max_duration", DEFAULT_BOOST_MAX_DURATION
        )
        boost_cooldown = getattr(actor, "boost_cooldown", DEFAULT_BOOST_COOLDOWN)
        boost_elapsed = resources.get("boost_elapsed", 0.0)
        current_en = resources.get("current_en", 0.0)

        cancel_reason: str | None = None

        # 条件 1: 最大継続時間超過
        if boost_elapsed >= boost_max_duration:
            cancel_reason = f"max_duration ({boost_max_duration}s) 到達"

        # 条件 2: EN 切れ
        elif current_en <= 0:
            cancel_reason = "EN 枯渇"

        elif target is not None:
            pos_actor = actor.position.to_numpy()
            pos_target = target.position.to_numpy()
            distance_to_target = float(np.linalg.norm(pos_target - pos_actor))

            # 条件 3: ターゲットが格闘到達射程内
            if distance_to_target <= MELEE_BOOST_ARRIVAL_RANGE:
                cancel_reason = f"格闘到達射程 ({MELEE_BOOST_ARRIVAL_RANGE}m) 以内"

            else:
                # 条件 4: 慣性考慮キャンセル判定
                # 使用予定の遠距離武器を取得
                ranged_weapon = next(
                    (
                        w
                        for w in actor.weapons
                        if not w.is_melee
                        and resources["weapon_states"]
                        .get(str(w.id), {})
                        .get("cooldown_remaining_sec", 0.0)
                        == 0.0
                        and (
                            resources["weapon_states"]
                            .get(str(w.id), {})
                            .get("current_ammo")
                            is None
                            or resources["weapon_states"]
                            .get(str(w.id), {})
                            .get("current_ammo", 0)
                            > 0
                        )
                    ),
                    None,
                )

                if ranged_weapon is not None:
                    current_velocity: np.ndarray = resources["velocity_vec"]
                    current_speed = float(np.linalg.norm(current_velocity))
                    deceleration = actor.deceleration

                    # 停止距離: d_stop = v² / (2 × deceleration)
                    if deceleration > 0 and current_speed > 0:
                        d_stop = (current_speed**2) / (2.0 * deceleration)
                        stop_direction = current_velocity / current_speed

                        stop_pos = pos_actor + stop_direction * d_stop
                        d_to_target_from_stop = float(
                            np.linalg.norm(pos_target - stop_pos)
                        )

                        if d_to_target_from_stop <= ranged_weapon.range:
                            cancel_reason = (
                                f"慣性考慮キャンセル (停止予想位置からの射程内: "
                                f"{d_to_target_from_stop:.0f}m <= {ranged_weapon.range}m)"
                            )

        if cancel_reason is None:
            return False

        # ブースト終了処理
        resources["is_boosting"] = False
        resources["boost_cooldown_remaining"] = boost_cooldown

        self.logs.append(  # type: ignore[attr-defined]
            BattleLog(
                timestamp=float(self.elapsed_time),  # type: ignore[attr-defined]
                actor_id=actor.id,
                action_type="BOOST_END",
                message=(
                    f"{self._format_actor_name(actor)} のブーストが終了した"  # type: ignore[attr-defined]
                    f" (理由: {cancel_reason})"
                ),
                position_snapshot=actor.position,
                details={"reason": cancel_reason},
            )
        )

        return True

    def _search_movement(self, actor: MobileSuit, dt: float = 0.1) -> None:
        """索敵移動: 未発見の敵を探すための移動."""
        # 敵対勢力を特定 (team_idが異なるユニットが敵)
        potential_targets = [
            u
            for u in self.units
            if u.current_hp > 0 and u.team_id != actor.team_id  # type: ignore[attr-defined]
        ]

        if not potential_targets:
            return

        pos_actor = actor.position.to_numpy()
        unit_id = str(actor.id)

        # LOS 喪失済みの最終既知座標がある場合はそこへ向かう（Phase A）
        last_known = self.unit_resources[unit_id].get("last_known_enemy_position", {})  # type: ignore[attr-defined]
        if last_known:
            # 最も近い最終既知座標を選ぶ
            best_pos: np.ndarray | None = None
            best_dist = float("inf")
            for pos_list in last_known.values():
                p = np.array(pos_list)
                d = float(np.linalg.norm(p - pos_actor))
                if d < best_dist:
                    best_dist = d
                    best_pos = p
            if best_pos is not None:
                diff_vector = best_pos - pos_actor
                distance = float(np.linalg.norm(diff_vector))
                if distance > 0:
                    desired_direction = self._calculate_potential_field(
                        actor,
                        target=None,
                        retreat_points=self.retreat_points,  # type: ignore[attr-defined]
                    )
                    self._apply_inertia(actor, desired_direction, dt)
                    if distance >= MOVE_LOG_MIN_DIST:
                        self.logs.append(  # type: ignore[attr-defined]
                            BattleLog(
                                timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                                actor_id=actor.id,
                                action_type="MOVE",
                                message=(
                                    f"{self._format_actor_name(actor)}が最終目撃地点へ向かっている"  # type: ignore[attr-defined]
                                    f" (残距離: {int(distance)}m)"
                                ),
                                position_snapshot=actor.position,
                                velocity_snapshot=Vector3.from_numpy(
                                    self.unit_resources[unit_id]["velocity_vec"]  # type: ignore[attr-defined]
                                ),
                            )
                        )
                    return

        # 最も近い敵の方向へ移動（まだ発見していなくても）
        closest_enemy = min(
            potential_targets,
            key=lambda t: np.linalg.norm(t.position.to_numpy() - pos_actor),
        )

        pos_target = closest_enemy.position.to_numpy()
        diff_vector = pos_target - pos_actor
        distance = float(np.linalg.norm(diff_vector))

        if distance == 0:
            return

        # ポテンシャルフィールドで目標方向を算出し、慣性モデルで移動
        desired_direction = self._calculate_potential_field(
            actor,
            target=None,
            retreat_points=self.retreat_points,  # type: ignore[attr-defined]
        )
        self._apply_inertia(actor, desired_direction, dt)

        # MOVE_LOG_MIN_DIST 以上の残距離のステップのみログ出力
        if distance >= MOVE_LOG_MIN_DIST:
            self.logs.append(  # type: ignore[attr-defined]
                BattleLog(
                    timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                    actor_id=actor.id,
                    action_type="MOVE",
                    message=f"{self._format_actor_name(actor)}が索敵中 (残距離: {int(distance)}m)",  # type: ignore[attr-defined]
                    position_snapshot=actor.position,
                    velocity_snapshot=Vector3.from_numpy(
                        self.unit_resources[str(actor.id)]["velocity_vec"]  # type: ignore[attr-defined]
                    ),
                )
            )

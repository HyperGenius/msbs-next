# backend/app/engine/simulation.py
import random

import numpy as np

from app.engine.constants import (
    TERRAIN_ADAPTABILITY_MODIFIERS,
)
from app.models.models import BattleLog, MobileSuit, Vector3, Weapon


class BattleSimulator:
    """戦闘シミュレータ."""

    def __init__(
        self,
        player: MobileSuit,
        enemies: list[MobileSuit],
        player_skills: dict[str, int] | None = None,
        environment: str = "SPACE",
    ):
        """初期化.

        Args:
            player: プレイヤー機体
            enemies: 敵機体リスト
            player_skills: プレイヤーのスキル (skill_id: level)
            environment: 戦闘環境 (SPACE/GROUND/COLONY/UNDERWATER)
        """
        self.player = player
        self.enemies = enemies
        self.units: list[MobileSuit] = [player] + enemies
        self.logs: list[BattleLog] = []
        self.turn = 0
        self.is_finished = False
        self.player_skills = player_skills or {}
        self.environment = environment

        # 索敵状態管理 (チーム単位で共有)
        self.team_detected_units: dict[str, set] = {
            "PLAYER": set(),
            "ENEMY": set(),
        }

    def process_turn(self) -> None:
        """1ターン分の処理を実行."""
        self.turn += 1

        # 生存している全ユニットを機動性の降順でソート
        alive_units = [u for u in self.units if u.current_hp > 0]
        # 機動性が同じ場合のためにランダム値を事前に付与
        units_with_random = [(u, random.random()) for u in alive_units]
        # 機動性とランダム値でソート（機動性が高い方が先、同値ならランダム）
        units_with_random.sort(key=lambda x: (x[0].mobility, x[1]), reverse=True)

        # 索敵フェーズ（ターン開始時）
        self._detection_phase()

        # 各ユニットの行動を順次実行
        for unit, _ in units_with_random:
            if self.is_finished:
                break
            self._action_phase(unit)

    def _action_phase(self, actor: MobileSuit) -> None:
        """片方のユニットの行動処理."""
        # 既に撃墜されていたら何もしない
        if actor.current_hp <= 0:
            return

        # ターゲット選択
        target = self._select_target(actor)
        if not target:
            # 発見済みの敵がいない場合、最も近い未発見の敵の方向へ移動
            self._search_movement(actor)
            return

        pos_actor = actor.position.to_numpy()
        pos_target = target.position.to_numpy()
        diff_vector = pos_target - pos_actor
        distance = float(np.linalg.norm(diff_vector))

        weapon = actor.get_active_weapon()

        # 攻撃可能なら攻撃、そうでなければ移動
        if weapon and distance <= weapon.range:
            self._process_attack(actor, target, distance, pos_actor)
        else:
            self._process_movement(actor, pos_actor, pos_target, diff_vector, distance)

    def _log_target_selection(
        self, actor: MobileSuit, target: MobileSuit, reason: str, details: str
    ) -> None:
        """ターゲット選択の理由をログに記録する.
        
        Args:
            actor: 選択を行った機体
            target: 選択されたターゲット
            reason: 選択理由（戦術名）
            details: 詳細情報（スコア値など）
        """
        message = f"{actor.name}がターゲット選択: {target.name} (戦術: {reason}, {details})"
        self.logs.append(
            BattleLog(
                turn=self.turn,
                actor_id=actor.id,
                action_type="TARGET_SELECTION",
                target_id=target.id,
                message=message,
                position_snapshot=actor.position,
            )
        )

    def _detection_phase(self) -> None:
        """索敵フェーズ: 各ユニットが索敵範囲内の敵を発見."""
        alive_units = [u for u in self.units if u.current_hp > 0]

        for unit in alive_units:
            # 敵対勢力を特定
            if unit.side == "PLAYER":
                # enemy_team = "ENEMY"
                potential_targets = [e for e in self.enemies if e.current_hp > 0]
            else:
                # enemy_team = "PLAYER"
                potential_targets = [self.player] if self.player.current_hp > 0 else []

            pos_unit = unit.position.to_numpy()

            # 索敵範囲内の敵をチェック
            for target in potential_targets:
                if target.id in self.team_detected_units[unit.side]:
                    # 既に発見済み
                    continue

                pos_target = target.position.to_numpy()
                distance = float(np.linalg.norm(pos_target - pos_unit))

                # 索敵判定 (ミノフスキー粒子の影響は今回は簡易実装でスキップ)
                if distance <= unit.sensor_range:
                    # 発見！
                    self.team_detected_units[unit.side].add(target.id)

                    # 発見ログを追加
                    self.logs.append(
                        BattleLog(
                            turn=self.turn,
                            actor_id=unit.id,
                            action_type="DETECTION",
                            target_id=target.id,
                            message=f"{unit.name}が{target.name}を発見！ (距離: {int(distance)}m)",
                            position_snapshot=unit.position,
                        )
                    )

    def _calculate_strategic_value(self, target: MobileSuit) -> float:
        """敵の戦略価値を計算する.
        
        Args:
            target: 評価対象の敵機体
            
        Returns:
            戦略価値スコア（高いほど価値が高い）
        """
        # 武器の平均威力を計算
        weapon_power_avg = 0.0
        if target.weapons:
            weapon_power_avg = sum(w.power for w in target.weapons) / len(target.weapons)
        
        # パイロットレベル（現時点では未実装なのでデフォルト1とする）
        pilot_level = 1.0
        
        # 戦略価値 = (最大HP + 平均武器威力) * (1 + パイロットレベル * 0.1)
        strategic_value = (target.max_hp + weapon_power_avg) * (1 + pilot_level * 0.1)
        
        return strategic_value

    def _calculate_threat_level(self, actor: MobileSuit, target: MobileSuit) -> float:
        """敵の脅威度を計算する.
        
        Args:
            actor: 評価する自機
            target: 評価対象の敵機体
            
        Returns:
            脅威度スコア（高いほど脅威が高い）
        """
        # 敵の攻撃力を計算（武器威力の平均）
        attack_power = 0.0
        if target.weapons:
            attack_power = sum(w.power for w in target.weapons) / len(target.weapons)
        
        # 距離を計算
        pos_actor = actor.position.to_numpy()
        pos_target = target.position.to_numpy()
        distance = float(np.linalg.norm(pos_target - pos_actor))
        
        # 距離が0の場合は最小距離を設定（ゼロ除算回避）
        if distance < 1.0:
            distance = 1.0
        
        # 自機の現在HPが0の場合は最小HPを設定（ゼロ除算回避）
        current_hp = max(1.0, float(actor.current_hp))
        
        # 脅威度 = (敵の攻撃力 / 自機の現在HP) * (1000 / 距離)
        # 距離で1000を割ることで、距離が近いほど脅威度が高くなる
        threat_level = (attack_power / current_hp) * (1000.0 / distance)
        
        return threat_level

    def _select_target(self, actor: MobileSuit) -> MobileSuit | None:
        """ターゲットを選択する（戦術と索敵状態に基づく）."""
        # ターゲット選択: 敵対勢力のユニットをリストアップ
        if actor.side == "PLAYER":
            potential_targets = [e for e in self.enemies if e.current_hp > 0]
        else:  # actor.side == "ENEMY"
            potential_targets = [self.player] if self.player.current_hp > 0 else []

        # 索敵済みの敵のみをターゲット候補とする
        detected_targets = [
            t for t in potential_targets if t.id in self.team_detected_units[actor.side]
        ]

        # ターゲットが存在しない場合はNoneを返す
        # （呼び出し元の_action_phaseで_search_movementが実行される）
        if not detected_targets:
            return None

        # 戦術に基づいてターゲットを選択
        tactics_priority = actor.tactics.get("priority", "CLOSEST")
        pos_actor = actor.position.to_numpy()

        if tactics_priority == "WEAKEST":
            # 最もHPが低い敵を選択
            target = min(detected_targets, key=lambda t: t.current_hp)
            self._log_target_selection(actor, target, "WEAKEST", f"HP: {target.current_hp}")
        elif tactics_priority == "STRONGEST":
            # 戦略価値が最も高い敵を選択
            target = max(detected_targets, key=lambda t: self._calculate_strategic_value(t))
            strategic_value = self._calculate_strategic_value(target)
            self._log_target_selection(actor, target, "STRONGEST", f"戦略価値: {strategic_value:.1f}")
        elif tactics_priority == "THREAT":
            # 脅威度が最も高い敵を選択
            target = max(detected_targets, key=lambda t: self._calculate_threat_level(actor, t))
            threat_level = self._calculate_threat_level(actor, target)
            self._log_target_selection(actor, target, "THREAT", f"脅威度: {threat_level:.2f}")
        elif tactics_priority == "RANDOM":
            # ランダムに敵を選択
            target = random.choice(detected_targets)
            self._log_target_selection(actor, target, "RANDOM", "ランダム選択")
        else:  # CLOSEST (デフォルト)
            # 最も近い敵を選択
            target = min(
                detected_targets,
                key=lambda t: np.linalg.norm(t.position.to_numpy() - pos_actor),
            )
            distance = np.linalg.norm(target.position.to_numpy() - pos_actor)
            self._log_target_selection(actor, target, "CLOSEST", f"距離: {int(distance)}m")
        return target

    def _process_attack(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        distance: float,
        pos_actor: np.ndarray,
    ) -> None:
        """攻撃処理を実行する."""
        weapon = actor.get_active_weapon()
        if not weapon:
            return

        snapshot = Vector3.from_numpy(pos_actor)

        # 命中率計算（最適射程を考慮）
        # 最適射程からの距離差を計算
        distance_from_optimal = abs(distance - weapon.optimal_range)
        dist_penalty = distance_from_optimal * weapon.decay_rate
        evasion_bonus = target.mobility * 10
        hit_chance = float(weapon.accuracy - dist_penalty - evasion_bonus)

        # プレイヤーの攻撃時はスキル補正を適用
        if actor.side == "PLAYER":
            # 命中率向上スキル
            accuracy_skill_level = self.player_skills.get("accuracy_up", 0)
            hit_chance += accuracy_skill_level * 2.0  # +2% / Lv

        # 敵への攻撃時は回避スキル補正を適用
        if target.side == "PLAYER":
            # 回避率向上スキル
            evasion_skill_level = self.player_skills.get("evasion_up", 0)
            hit_chance -= evasion_skill_level * 2.0  # 敵の命中率を -2% / Lv

        hit_chance = max(0, min(100, hit_chance))

        # ダイスロール
        dice = random.uniform(0, 100)
        is_hit = dice <= hit_chance

        # 距離による状況メッセージ
        distance_msg = ""
        if distance_from_optimal < 50:
            distance_msg = " (最適距離!)"
        elif distance_from_optimal > 200:
            distance_msg = " (距離不利)"

        log_base = f"{actor.name}の攻撃！{distance_msg} (命中: {int(hit_chance)}%)"

        if is_hit:
            self._process_hit(actor, target, weapon, log_base, snapshot)
        else:
            self._process_miss(actor, target, log_base, snapshot)

    def _process_hit(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        weapon: Weapon,
        log_base: str,
        snapshot: Vector3,
    ) -> None:
        """命中時の処理."""
        # クリティカル判定
        base_crit_rate = 0.05

        # プレイヤーの攻撃時はクリティカル率スキル補正を適用
        if actor.side == "PLAYER":
            crit_skill_level = self.player_skills.get("crit_rate_up", 0)
            base_crit_rate += (crit_skill_level * 1.0) / 100.0  # +1% / Lv

        is_crit = random.random() < base_crit_rate

        if not is_crit:
            base_damage = max(1, weapon.power - target.armor)
            log_msg = f"{log_base} -> 命中！"
        else:
            base_damage = int(weapon.power * 1.2)
            log_msg = f"{log_base} -> クリティカルヒット！！"

        # プレイヤーの攻撃時はダメージ向上スキル補正を適用
        if actor.side == "PLAYER":
            damage_skill_level = self.player_skills.get("damage_up", 0)
            damage_multiplier = 1.0 + (damage_skill_level * 3.0) / 100.0  # +3% / Lv
            base_damage = int(base_damage * damage_multiplier)

        # 武器タイプに応じた耐性を適用
        weapon_type = getattr(weapon, "type", "PHYSICAL")
        resistance_msg = ""
        if weapon_type == "BEAM":
            resistance = getattr(target, "beam_resistance", 0.0)
            if resistance > 0:
                base_damage = int(base_damage * (1.0 - resistance))
                resistance_msg = f" [対ビーム装甲により{int(resistance * 100)}%軽減]"
        elif weapon_type == "PHYSICAL":
            resistance = getattr(target, "physical_resistance", 0.0)
            if resistance > 0:
                base_damage = int(base_damage * (1.0 - resistance))
                resistance_msg = f" [対実弾装甲により{int(resistance * 100)}%軽減]"

        # 乱数幅
        variance = random.uniform(0.9, 1.1)
        final_damage = int(base_damage * variance)

        target.current_hp -= final_damage

        self.logs.append(
            BattleLog(
                turn=self.turn,
                actor_id=actor.id,
                action_type="ATTACK",
                target_id=target.id,
                damage=final_damage,
                message=f"{log_msg}{resistance_msg} {target.name}に{final_damage}ダメージ！",
                position_snapshot=snapshot,
            )
        )

        if target.current_hp <= 0:
            self._process_destruction(target)

    def _process_miss(
        self, actor: MobileSuit, target: MobileSuit, log_base: str, snapshot: Vector3
    ) -> None:
        """ミス時の処理."""
        self.logs.append(
            BattleLog(
                turn=self.turn,
                actor_id=actor.id,
                action_type="MISS",
                target_id=target.id,
                message=f"{log_base} -> 回避された！",
                position_snapshot=snapshot,
            )
        )

    def _process_destruction(self, target: MobileSuit) -> None:
        """撃破時の処理."""
        target.current_hp = 0
        self.logs.append(
            BattleLog(
                turn=self.turn,
                actor_id=target.id,
                action_type="DESTROYED",
                message=f"{target.name} は爆散した...",
                position_snapshot=target.position,
            )
        )
        # 勝利判定
        if target.side == "PLAYER":
            self.is_finished = True
        elif all(e.current_hp <= 0 for e in self.enemies):
            self.is_finished = True

    def _process_movement(
        self,
        actor: MobileSuit,
        pos_actor: np.ndarray,
        pos_target: np.ndarray,
        diff_vector: np.ndarray,
        distance: float,
    ) -> None:
        """移動処理を実行する（戦術に基づく）."""
        if distance == 0:
            return

        # 地形適正による補正を適用
        terrain_modifier = self._get_terrain_modifier(actor)
        effective_mobility = actor.mobility * terrain_modifier

        # 戦術に基づいて移動方向を決定
        tactics_range = actor.tactics.get("range", "BALANCED")
        weapon = actor.get_active_weapon()

        if tactics_range == "FLEE":
            # 敵から逃げる（後退）
            direction = -diff_vector / distance  # 反対方向
            speed = effective_mobility * 150
            move_vector = direction * speed
            new_pos = pos_actor + move_vector
            actor.position = Vector3.from_numpy(new_pos)

            self.logs.append(
                BattleLog(
                    turn=self.turn,
                    actor_id=actor.id,
                    action_type="MOVE",
                    message=f"{actor.name}が後退中 (距離: {int(distance)}m)",
                    position_snapshot=actor.position,
                )
            )
        elif tactics_range == "RANGED" and weapon:
            # 遠距離維持（射程ギリギリの距離を維持）
            ideal_distance = weapon.range * 0.8  # 射程の80%の距離を維持

            if distance < ideal_distance:
                # 近すぎる場合は後退
                direction = -diff_vector / distance
                speed = effective_mobility * 100
                move_vector = direction * speed
                new_pos = pos_actor + move_vector
                actor.position = Vector3.from_numpy(new_pos)

                self.logs.append(
                    BattleLog(
                        turn=self.turn,
                        actor_id=actor.id,
                        action_type="MOVE",
                        message=f"{actor.name}が距離を取る (距離: {int(distance)}m)",
                        position_snapshot=actor.position,
                    )
                )
            elif distance > weapon.range:
                # 射程外の場合は接近
                direction = diff_vector / distance
                speed = effective_mobility * 100
                move_vector = direction * speed
                new_pos = pos_actor + move_vector

                # 行き過ぎ防止
                if np.linalg.norm(new_pos - pos_actor) > distance:
                    new_pos = pos_target - (direction * ideal_distance)

                actor.position = Vector3.from_numpy(new_pos)

                self.logs.append(
                    BattleLog(
                        turn=self.turn,
                        actor_id=actor.id,
                        action_type="MOVE",
                        message=f"{actor.name}が射程内に移動中 (残距離: {int(distance)}m)",
                        position_snapshot=actor.position,
                    )
                )
        else:  # MELEE or BALANCED (デフォルト)
            # 敵に接近
            direction = diff_vector / distance
            speed = effective_mobility * 150
            move_vector = direction * speed

            new_pos = pos_actor + move_vector

            # 行き過ぎ防止
            if np.linalg.norm(new_pos - pos_actor) > distance:
                new_pos = pos_target - (direction * 50)

            actor.position = Vector3.from_numpy(new_pos)

            self.logs.append(
                BattleLog(
                    turn=self.turn,
                    actor_id=actor.id,
                    action_type="MOVE",
                    message=f"{actor.name}が接近中 (残距離: {int(distance)}m)",
                    position_snapshot=actor.position,
                )
            )

    def _get_terrain_modifier(self, unit: MobileSuit) -> float:
        """地形適正による補正係数を取得."""
        # 地形適正を取得
        terrain_adaptability = getattr(unit, "terrain_adaptability", {})
        adaptability_grade = terrain_adaptability.get(self.environment, "A")

        # 補正係数を返す
        return TERRAIN_ADAPTABILITY_MODIFIERS.get(adaptability_grade, 1.0)

    def _search_movement(self, actor: MobileSuit) -> None:
        """索敵移動: 未発見の敵を探すための移動."""
        # 敵対勢力を特定
        if actor.side == "PLAYER":
            potential_targets = [e for e in self.enemies if e.current_hp > 0]
        else:
            potential_targets = [self.player] if self.player.current_hp > 0 else []

        if not potential_targets:
            return

        # 最も近い敵の方向へ移動（まだ発見していなくても）
        pos_actor = actor.position.to_numpy()
        closest_enemy = min(
            potential_targets,
            key=lambda t: np.linalg.norm(t.position.to_numpy() - pos_actor),
        )

        pos_target = closest_enemy.position.to_numpy()
        diff_vector = pos_target - pos_actor
        distance = float(np.linalg.norm(diff_vector))

        if distance == 0:
            return

        # 地形適正による補正を適用
        terrain_modifier = self._get_terrain_modifier(actor)
        effective_mobility = actor.mobility * terrain_modifier

        # 索敵のための移動
        direction = diff_vector / distance
        speed = effective_mobility * 150
        move_vector = direction * speed
        new_pos = pos_actor + move_vector

        # 行き過ぎ防止
        if np.linalg.norm(new_pos - pos_actor) > distance:
            new_pos = pos_target - (direction * 50)

        actor.position = Vector3.from_numpy(new_pos)

        self.logs.append(
            BattleLog(
                turn=self.turn,
                actor_id=actor.id,
                action_type="MOVE",
                message=f"{actor.name}が索敵中 (残距離: {int(distance)}m)",
                position_snapshot=actor.position,
            )
        )

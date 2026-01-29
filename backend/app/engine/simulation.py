# backend/app/engine/simulation.py
import random

import numpy as np

from app.models.models import BattleLog, MobileSuit, Vector3, Weapon


class BattleSimulator:
    """戦闘シミュレータ."""

    def __init__(self, player: MobileSuit, enemies: list[MobileSuit]):
        """初期化."""
        self.player = player
        self.enemies = enemies
        self.units: list[MobileSuit] = [player] + enemies
        self.logs: list[BattleLog] = []
        self.turn = 0
        self.is_finished = False

    def process_turn(self) -> None:
        """1ターン分の処理を実行."""
        self.turn += 1

        # 生存している全ユニットを機動性の降順でソート
        alive_units = [u for u in self.units if u.current_hp > 0]
        # 機動性が同じ場合のためにランダム値を事前に付与
        units_with_random = [(u, random.random()) for u in alive_units]
        # 機動性とランダム値でソート（機動性が高い方が先、同値ならランダム）
        units_with_random.sort(key=lambda x: (x[0].mobility, x[1]), reverse=True)

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

    def _select_target(self, actor: MobileSuit) -> MobileSuit | None:
        """ターゲットを選択する."""
        # ターゲット選択: 敵対勢力のユニットをリストアップ
        if actor.side == "PLAYER":
            potential_targets = [e for e in self.enemies if e.current_hp > 0]
        else:  # actor.side == "ENEMY"
            potential_targets = [self.player] if self.player.current_hp > 0 else []

        # ターゲットが存在しない場合はNoneを返す
        if not potential_targets:
            return None

        # 最も近い敵を選択
        pos_actor = actor.position.to_numpy()
        target = min(
            potential_targets,
            key=lambda t: np.linalg.norm(t.position.to_numpy() - pos_actor),
        )
        return target

    def _process_attack(
        self, actor: MobileSuit, target: MobileSuit, distance: float, pos_actor: np.ndarray
    ) -> None:
        """攻撃処理を実行する."""
        weapon = actor.get_active_weapon()
        if not weapon:
            return

        snapshot = Vector3.from_numpy(pos_actor)

        # 命中率計算
        dist_penalty = (distance / 100) * 2
        evasion_bonus = target.mobility * 10
        hit_chance = float(weapon.accuracy - dist_penalty - evasion_bonus)
        hit_chance = max(0, min(100, hit_chance))

        # ダイスロール
        dice = random.uniform(0, 100)
        is_hit = dice <= hit_chance

        log_base = f"{actor.name}の攻撃！ (命中: {int(hit_chance)}%)"

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
        is_crit = random.random() < 0.05

        if not is_crit:
            base_damage = max(1, weapon.power - target.armor)
            log_msg = f"{log_base} -> 命中！"
        else:
            base_damage = int(weapon.power * 1.2)
            log_msg = f"{log_base} -> クリティカルヒット！！"

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
                message=f"{log_msg} {target.name}に{final_damage}ダメージ！",
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
        """移動処理を実行する."""
        if distance > 0:
            direction = diff_vector / distance
            speed = actor.mobility * 150
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

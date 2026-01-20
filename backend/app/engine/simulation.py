# backend/app/engine/simulation.py
import random

import numpy as np

from app.models.models import BattleLog, MobileSuit, Vector3


class BattleSimulator:
    """戦闘シミュレータ."""

    def __init__(self, ms1: MobileSuit, ms2: MobileSuit):
        """初期化."""
        self.ms1 = ms1
        self.ms2 = ms2
        self.logs: list[BattleLog] = []
        self.turn = 0
        self.is_finished = False

    def process_turn(self) -> None:
        """1ターン分の処理を実行."""
        self.turn += 1

        # 簡易的な素早さ判定（機動性が高い方が先に行動）
        # 同値ならランダム
        first, second = self.ms1, self.ms2
        if self.ms1.mobility < self.ms2.mobility:
            first, second = self.ms2, self.ms1
        elif self.ms1.mobility == self.ms2.mobility and random.random() > 0.5:
            first, second = self.ms2, self.ms1

        self._action_phase(first, second)
        if not self.is_finished:
            self._action_phase(second, first)

    def _action_phase(self, actor: MobileSuit, target: MobileSuit) -> None:
        """片方のユニットの行動処理."""
        # 既に撃墜されていたら何もしない
        if actor.current_hp <= 0:
            return

        pos_actor = actor.position.to_numpy()
        pos_target = target.position.to_numpy()
        diff_vector = pos_target - pos_actor
        distance = np.linalg.norm(diff_vector)
        snapshot = Vector3.from_numpy(pos_actor)

        weapon = actor.get_active_weapon()

        # --- 攻撃判定ロジック ---
        if weapon and distance <= weapon.range:
            # 1. 命中率計算
            # 距離減衰: 100m離れるごとに命中-2%
            dist_penalty = (distance / 100) * 2
            # 回避補正: 相手の機動性 * 10%
            evasion_bonus = target.mobility * 10

            hit_chance = float(weapon.accuracy - dist_penalty - evasion_bonus)
            hit_chance = max(0, min(100, hit_chance))  # 0~100に収める

            # ダイスロール (0.0 ~ 100.0)
            dice = random.uniform(0, 100)
            is_hit = dice <= hit_chance

            # ログ用メッセージ作成
            log_base = f"{actor.name}の攻撃！ (命中: {int(hit_chance)}%)"

            if is_hit:
                # 2. ダメージ計算
                # クリティカル判定 (5%の確率)
                is_crit = random.random() < 0.05

                base_damage = weapon.power
                if not is_crit:
                    # 通常ヒット: 装甲で減算
                    base_damage = max(1, weapon.power - target.armor)
                    log_msg = f"{log_base} -> 命中！"
                else:
                    # クリティカル: 防御無視 & 威力1.2倍
                    base_damage = int(weapon.power * 1.2)
                    log_msg = f"{log_base} -> クリティカルヒット！！"

                # 乱数幅 (±10%)
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
                    target.current_hp = 0
                    self.is_finished = True
                    self.logs.append(
                        BattleLog(
                            turn=self.turn,
                            actor_id=target.id,
                            action_type="DESTROYED",
                            message=f"{target.name} は爆散した...",
                            position_snapshot=target.position,
                        )
                    )
            else:
                # ミス
                self.logs.append(
                    BattleLog(
                        turn=self.turn,
                        actor_id=actor.id,
                        action_type="MISS",  # 新しいタイプ
                        target_id=target.id,
                        message=f"{log_base} -> 回避された！",
                        position_snapshot=snapshot,
                    )
                )

        else:
            # --- 移動ロジック (前回と同じだが少し調整) ---
            if distance > 0:
                direction = diff_vector / distance
                # 機動性が高いほど速く動く
                speed = actor.mobility * 150
                move_vector = direction * speed

                new_pos = pos_actor + move_vector

                # 行き過ぎ防止
                if np.linalg.norm(new_pos - pos_actor) > distance:
                    new_pos = pos_target - (direction * 50)  # 50m手前まで

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

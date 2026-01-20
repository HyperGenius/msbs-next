# backend/app/engine/simulation.py

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

        # 素早さ判定（今回は単純に交互に行動とせず、同時行動として処理）
        self._action_phase(self.ms1, self.ms2)
        if not self.is_finished:
            self._action_phase(self.ms2, self.ms1)

    def _action_phase(self, actor: MobileSuit, target: MobileSuit) -> None:
        """片方のユニットの行動処理."""
        # 1. 距離計算 (NumPy)
        pos_actor = actor.position.to_numpy()
        pos_target = target.position.to_numpy()

        # ベクトル: 自分 -> 相手
        diff_vector = pos_target - pos_actor
        distance = np.linalg.norm(diff_vector)  # ユークリッド距離

        # ログ用スナップショット
        snapshot = Vector3.from_numpy(pos_actor)

        # 2. 行動判定
        # 武器の射程内か？ (とりあえず最初の武器を使う)
        weapon = actor.get_active_weapon()
        if weapon and distance <= weapon.range:
            # --- 攻撃処理 (Phase 0なので命中確定ログのみ) ---
            log = BattleLog(
                turn=self.turn,
                actor_id=actor.id,
                action_type="ATTACK",
                target_id=target.id,
                message=f"{actor.name}が{weapon.name}を発射！ (距離: {distance:.1f})",
                position_snapshot=snapshot,
            )
            self.logs.append(log)

            # ダメージ計算（仮）
            damage = weapon.power
            target.current_hp -= damage
            self.logs.append(
                BattleLog(
                    turn=self.turn,
                    actor_id=target.id,  # ダメージを受けた側
                    action_type="DAMAGE",
                    damage=damage,
                    message=f"{target.name}に{damage}のダメージ！ (残りHP: {target.current_hp})",
                    position_snapshot=target.position,  # その場の位置
                )
            )

            if target.current_hp <= 0:
                self.is_finished = True
                self.logs.append(
                    BattleLog(
                        turn=self.turn,
                        actor_id=target.id,
                        action_type="DESTROYED",
                        message=f"{target.name} は撃墜された...",
                        position_snapshot=target.position,
                    )
                )

        else:
            # --- 移動処理 ---
            # 射程外なら相手に向かって近づく
            # 正規化ベクトル（向き） * 移動速度
            if distance > 0:
                direction = diff_vector / distance
                move_vector = direction * (
                    actor.mobility * 100
                )  # 仮: mobility 1.0 = 100m/turn

                # 新しい座標
                new_pos = pos_actor + move_vector

                # 行き過ぎ防止（相手を通り越さないようにする）
                if np.linalg.norm(new_pos - pos_actor) > distance:
                    new_pos = pos_target - (direction * 10)  # 相手の手前10mで止まる

                # 座標更新
                actor.position = Vector3.from_numpy(new_pos)

                self.logs.append(
                    BattleLog(
                        turn=self.turn,
                        actor_id=actor.id,
                        action_type="MOVE",
                        message=f"{actor.name}が接近中... (座標: {int(new_pos[0])}, {int(new_pos[1])}, {int(new_pos[2])})",
                        position_snapshot=actor.position,
                    )
                )

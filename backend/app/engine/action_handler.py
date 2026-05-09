# backend/app/engine/action_handler.py
"""アクションフェーズ・ブーストダッシュ・格闘処理のミックスイン."""

from typing import TYPE_CHECKING

import numpy as np

from app.engine.constants import MELEE_BOOST_ARRIVAL_RANGE, POST_MELEE_DISTANCE
from app.models.models import BattleLog, MobileSuit, Vector3, Weapon

if TYPE_CHECKING:
    pass


class ActionHandlerMixin:
    """アクションフェーズ・ブーストダッシュ・格闘処理のミックスイン."""

    def _action_phase(self, actor: MobileSuit, dt: float = 0.1) -> None:
        """片方のユニットの行動処理."""
        # 既に撃墜されていたら何もしない
        if actor.current_hp <= 0:
            return

        # 撤退完了済みのユニットは行動しない
        unit_id = str(actor.id)
        if self.unit_resources[unit_id].get("status") == "RETREATED":  # type: ignore[attr-defined]
            return

        # ファジィ推論で決定した行動を取得
        current_action = self.unit_resources[unit_id].get("current_action", "MOVE")  # type: ignore[attr-defined]

        # ターゲット選択
        target = self._select_target_fuzzy(actor)  # type: ignore[attr-defined]
        if not target:
            # 発見済みの敵がいない場合、最も近い未発見の敵の方向へ移動
            self._search_movement(actor, dt)  # type: ignore[attr-defined]
            return

        pos_actor = actor.position.to_numpy()
        pos_target = target.position.to_numpy()
        diff_vector = pos_target - pos_actor
        distance = float(np.linalg.norm(diff_vector))

        weapon = self._select_weapon_fuzzy(actor, target)  # type: ignore[attr-defined]
        if weapon is None:
            weapon = actor.get_active_weapon()

        if current_action == "ATTACK":
            # 攻撃行動: 攻撃可能なら攻撃、そうでなければ移動
            if weapon and distance <= weapon.range:
                self._process_attack(actor, target, distance, pos_actor, weapon)  # type: ignore[attr-defined]
            else:
                self._process_movement(  # type: ignore[attr-defined]
                    actor,
                    pos_actor,
                    pos_target,
                    diff_vector,
                    distance,
                    dt,
                    target=target,
                )
        elif current_action == "ENGAGE_MELEE":
            self._handle_engage_melee_action(
                actor, target, weapon, pos_actor, pos_target, diff_vector, distance, dt
            )
        elif current_action == "BOOST_DASH":
            self._handle_boost_dash_action(
                actor, target, weapon, pos_actor, pos_target, diff_vector, distance, dt
            )
        else:
            # MOVE 行動（RETREAT フォールバックを含む）: 移動のみ（攻撃対象引力なし）
            self._process_movement(  # type: ignore[attr-defined]
                actor, pos_actor, pos_target, diff_vector, distance, dt
            )

    def _handle_boost_dash_action(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        weapon: object,
        pos_actor: np.ndarray,
        pos_target: np.ndarray,
        diff_vector: np.ndarray,
        distance: float,
        dt: float,
    ) -> None:
        """ブーストダッシュ行動処理 (Phase B)."""
        unit_id = str(actor.id)
        resources = self.unit_resources[unit_id]  # type: ignore[attr-defined]
        is_boosting = resources.get("is_boosting", False)
        cooldown_remaining = resources.get("boost_cooldown_remaining", 0.0)

        if not is_boosting and cooldown_remaining <= 0.0:
            # ブースト開始
            resources["is_boosting"] = True
            resources["boost_elapsed"] = 0.0
            self.logs.append(  # type: ignore[attr-defined]
                BattleLog(
                    timestamp=float(self.elapsed_time),  # type: ignore[attr-defined]
                    actor_id=actor.id,
                    action_type="BOOST_START",
                    message=(
                        f"{self._format_actor_name(actor)} がブーストダッシュを開始した！"  # type: ignore[attr-defined]
                    ),
                    position_snapshot=actor.position,
                )
            )

        # ブーストキャンセル判定
        cancelled = self._check_boost_cancel(actor, target, dt)  # type: ignore[attr-defined]

        if cancelled:
            # キャンセル後は遠距離攻撃試行
            if weapon and isinstance(weapon, Weapon) and distance <= weapon.range:
                self._process_attack(actor, target, distance, pos_actor, weapon)  # type: ignore[attr-defined]
            else:
                self._process_movement(  # type: ignore[attr-defined]
                    actor,
                    pos_actor,
                    pos_target,
                    diff_vector,
                    distance,
                    dt,
                    target=target,
                )
        else:
            # ブースト継続: ターゲット方向へ高速移動
            self._process_movement(  # type: ignore[attr-defined]
                actor,
                pos_actor,
                pos_target,
                diff_vector,
                distance,
                dt,
                target=target,
            )

    def _handle_engage_melee_action(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        weapon: object,
        pos_actor: np.ndarray,
        pos_target: np.ndarray,
        diff_vector: np.ndarray,
        distance: float,
        dt: float,
    ) -> None:
        """近接格闘突入行動処理 (Phase C).

        ENGAGE_MELEE アクション:
        1. ターゲットまでの距離 > MELEE_BOOST_ARRIVAL_RANGE → BOOST_DASH を実行
        2. ターゲットまでの距離 <= MELEE_BOOST_ARRIVAL_RANGE → 格闘武器で攻撃

        Args:
            actor: 行動ユニット
            target: ターゲットユニット
            weapon: 選択された武器
            pos_actor: アクターの位置
            pos_target: ターゲットの位置
            diff_vector: ターゲット方向ベクトル
            distance: ターゲットまでの距離
            dt: 時間ステップ幅 (s)
        """
        if distance > MELEE_BOOST_ARRIVAL_RANGE:
            # ターゲットへ向かってブーストダッシュ
            self._handle_boost_dash_action(
                actor, target, weapon, pos_actor, pos_target, diff_vector, distance, dt
            )
        else:
            # 格闘攻撃範囲内 — 格闘武器で攻撃
            melee_weapon = next(
                (
                    w
                    for w in actor.weapons
                    if getattr(w, "weapon_type", "RANGED") == "MELEE"
                    or getattr(w, "is_melee", False)
                ),
                weapon if isinstance(weapon, Weapon) else None,
            )
            if melee_weapon and isinstance(melee_weapon, Weapon):
                self._process_engage_melee(actor, target, pos_actor, melee_weapon)
            elif weapon and isinstance(weapon, Weapon):
                self._process_attack(actor, target, distance, pos_actor, weapon)  # type: ignore[attr-defined]
            else:
                self._process_movement(  # type: ignore[attr-defined]
                    actor,
                    pos_actor,
                    pos_target,
                    diff_vector,
                    distance,
                    dt,
                    target=target,
                )

    def _process_engage_melee(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        pos_actor: np.ndarray,
        weapon: Weapon,
    ) -> None:
        """格闘攻撃を処理し、命中後に再配置を行う (Phase C).

        格闘命中後のポジショニング:
            dir_away = normalize(pos_self - pos_target)
            pos_self  = pos_target + dir_away × POST_MELEE_DISTANCE (10m)
            velocity_vec = [0, 0, 0]  # 速度リセット

        Args:
            actor: 格闘攻撃するユニット
            target: 攻撃対象
            pos_actor: アクターの現在位置
            weapon: 使用する格闘武器
        """
        pos_target = target.position.to_numpy()
        distance = float(np.linalg.norm(pos_target - pos_actor))

        # 格闘攻撃を実行
        self._process_attack(actor, target, distance, pos_actor, weapon)  # type: ignore[attr-defined]

        # 格闘命中後の再配置（ターゲットが生存している場合）
        if target.current_hp > 0:
            dir_away_vec = pos_actor - pos_target
            dir_away_dist = float(np.linalg.norm(dir_away_vec))
            if dir_away_dist > 1e-6:
                dir_away = dir_away_vec / dir_away_dist
            else:
                dir_away = np.array([1.0, 0.0, 0.0])

            new_pos = pos_target + dir_away * POST_MELEE_DISTANCE
            actor.position = Vector3.from_numpy(new_pos)

            unit_id = str(actor.id)
            self.unit_resources[unit_id]["velocity_vec"] = np.zeros(3)  # type: ignore[attr-defined]

    def _log_target_selection(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        reason: str,
        details: str,
        fuzzy_scores: dict | None = None,
    ) -> None:
        """ターゲット選択の理由をログに記録する.

        Args:
            actor: 選択を行った機体
            target: 選択されたターゲット
            reason: 選択理由（戦術名）
            details: 詳細情報（スコア値など）
            fuzzy_scores: ファジィ推論のスコア（reason が "FUZZY" の場合に提供される）
        """
        _tactics_label: dict[str, str] = {
            "CLOSEST": "近距離優先",
            "WEAKEST": "弱体ターゲット優先",
            "STRONGEST": "高脅威ターゲット優先",
            "THREAT": "最大脅威優先",
            "RANDOM": "ランダム選択",
            "FUZZY": "ファジィ推論",
        }
        actor_name = self._format_actor_name(actor)  # type: ignore[attr-defined]
        label = _tactics_label.get(reason, reason)

        if reason == "CLOSEST":
            # details = "距離: XXXm"
            dist_str = details.replace("距離: ", "").strip()
            try:
                dist_val = float(dist_str.rstrip("m"))
                dist_label = self._get_distance_label(dist_val)  # type: ignore[attr-defined]
            except ValueError:
                dist_label = dist_str
            message = (
                f"{actor_name}は[戦術: {label}]に従い、"
                f"{dist_label}にいる{target.name}をターゲットに捕捉！"
            )
        elif reason == "WEAKEST":
            # details = "HP: XX"
            message = (
                f"{actor_name}は[戦術: {label}]でスキャン。"
                f"{details}の{target.name}を狙い撃ちにする！"
            )
        elif reason == "STRONGEST":
            message = (
                f"{actor_name}は[戦術: {label}]に従い、"
                f"{target.name}（{details}）を最優先ターゲットに設定！"
            )
        elif reason == "THREAT":
            message = (
                f"{actor_name}は[戦術: {label}]で判断し、"
                f"最も危険な{target.name}（{details}）を排除対象に選定！"
            )
        elif reason == "RANDOM":
            message = f"{actor_name}はランダムに{target.name}をターゲットに選択した"
        elif reason == "FUZZY":
            message = (
                f"{actor_name}は[{label}]で{target.name}を最優先ターゲットに決定"
                f"（{details}）"
            )
        else:
            message = f"{actor_name}がターゲット選択: {target.name} (戦術: {reason}, {details})"

        self.logs.append(  # type: ignore[attr-defined]
            BattleLog(
                timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                actor_id=actor.id,
                action_type="TARGET_SELECTION",
                target_id=target.id,
                message=message,
                position_snapshot=actor.position,
                fuzzy_scores=fuzzy_scores,
            )
        )

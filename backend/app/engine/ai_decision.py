# backend/app/engine/ai_decision.py
"""戦略・AI決定・後退チェックフェーズのミックスイン."""

import math
from typing import TYPE_CHECKING

import numpy as np

from app.engine.combat import has_los
from app.engine.constants import (
    DEFAULT_BOOST_EN_COST,
    STRATEGY_UPDATE_INTERVAL,
)
from app.models.models import BattleLog, MobileSuit, Vector3

if TYPE_CHECKING:
    pass

# 近隣ユニット検索半径 (m)
_FUZZY_NEIGHBOR_RADIUS = 500.0


class AiDecisionMixin:
    """戦略・AI決定・後退チェックフェーズのミックスイン."""

    def _strategy_phase(self) -> None:
        """戦略評価フェーズ: チームレベルの戦略モードを評価・更新する (Phase 4-2 / 4-3).

        STRATEGY_UPDATE_INTERVAL ステップごとに各チームの TeamStrategyController を
        呼び出してメトリクスを評価し、戦略変更が発生した場合はユニットの strategy_mode
        を一括更新して STRATEGY_CHANGED ログを記録する。
        撤退ポイント未設定時に RETREAT → DEFENSIVE フォールバックを適用する (T10)。
        """
        # 全チームのメトリクスを収集
        team_ids = list(self._strategy_controllers.keys())  # type: ignore[attr-defined]
        team_metrics_map = {
            team_id: self._collect_team_metrics(team_id) for team_id in team_ids  # type: ignore[attr-defined]
        }

        for team_id, controller in self._strategy_controllers.items():  # type: ignore[attr-defined]
            if not controller.should_evaluate():
                continue

            metrics = team_metrics_map[team_id]
            previous_strategy = controller.current_strategy
            new_strategy = controller.evaluate(metrics)
            matched_rule_id = controller._last_matched_rule_id

            # T10 フォールバック: RETREAT への遷移かつ撤退ポイント未設定 → DEFENSIVE に切替
            if new_strategy == "RETREAT" and len(self.retreat_points) == 0:  # type: ignore[attr-defined]
                new_strategy = "DEFENSIVE"
                matched_rule_id = "T10"

            if new_strategy is None or new_strategy == previous_strategy:
                continue

            # ACTIVE ユニットの strategy_mode を一括更新
            team_unit_resources = [
                (u, self.unit_resources[str(u.id)])  # type: ignore[attr-defined]
                for u in self.units  # type: ignore[attr-defined]
                if u.team_id == team_id
            ]
            controller.apply(new_strategy, team_unit_resources)

            # STRATEGY_CHANGED ログを記録
            # trigger_metrics の float キャストで numpy 型を回避
            trigger_metrics = {
                "alive_ratio": float(metrics.alive_ratio),
                "avg_hp_ratio": float(metrics.avg_hp_ratio),
                "min_hp_ratio": float(metrics.min_hp_ratio),
                "alive_count": int(metrics.alive_count),
                "total_count": int(metrics.total_count),
            }

            self.logs.append(  # type: ignore[attr-defined]
                BattleLog(
                    timestamp=float(self.elapsed_time),  # type: ignore[attr-defined]
                    actor_id=self._team_event_actor_id,  # type: ignore[attr-defined]
                    action_type="STRATEGY_CHANGED",
                    message=(
                        f"チーム [{team_id}] の戦略が "
                        f"[{previous_strategy}] → [{new_strategy}] に変更された。"
                    ),
                    position_snapshot=Vector3(),
                    team_id=team_id,
                    strategy_mode=new_strategy,
                    details={
                        "previous_strategy": previous_strategy,
                        "new_strategy": new_strategy,
                        "rule_id": matched_rule_id,
                        "trigger_metrics": trigger_metrics,
                    },
                )
            )

    def _compute_phase_c_fuzzy_inputs(
        self,
        unit: MobileSuit,
        unit_id: str,
        pos_unit: np.ndarray,
        nearest_enemy: MobileSuit,
    ) -> dict[str, float]:
        """Phase C ファジィ入力変数を計算して返す.

        Args:
            unit: 行動中のユニット
            unit_id: ユニットの文字列 ID
            pos_unit: 行動中ユニットの位置ベクトル
            nearest_enemy: 最近の索敵済み敵ユニット

        Returns:
            ranged_ammo_ratio / los_blocked / boost_available を含む dict
        """
        result: dict[str, float] = {}

        # ranged_ammo_ratio: 全遠距離武器の残弾割合の平均
        ranged_weapons = [
            w
            for w in unit.weapons
            if getattr(w, "weapon_type", "RANGED") != "MELEE"
            and not getattr(w, "is_melee", False)
        ]
        if ranged_weapons:
            ammo_ratios = []
            for rw in ranged_weapons:
                ws = self.unit_resources[unit_id]["weapon_states"].get(rw.id, {})  # type: ignore[attr-defined]
                if rw.max_ammo is not None and rw.max_ammo > 0:
                    current_ammo = ws.get("current_ammo", rw.max_ammo) or 0
                    ammo_ratios.append(float(current_ammo) / float(rw.max_ammo))
                else:
                    ammo_ratios.append(1.0)
            result["ranged_ammo_ratio"] = sum(ammo_ratios) / len(ammo_ratios)
        else:
            result["ranged_ammo_ratio"] = 1.0

        # los_blocked: ターゲットへの LOS 状態（Phase A の結果を使用）
        if self.obstacles:  # type: ignore[attr-defined]
            pos_nearest = nearest_enemy.position.to_numpy()
            los_ok = has_los(pos_unit, pos_nearest, self.obstacles)  # type: ignore[attr-defined]
            result["los_blocked"] = 0.0 if los_ok else 1.0
        else:
            result["los_blocked"] = 0.0

        # boost_available: クールダウン中でなく EN が十分か
        boost_cooldown_remaining = self.unit_resources[unit_id].get(  # type: ignore[attr-defined]
            "boost_cooldown_remaining", 0.0
        )
        current_en = self.unit_resources[unit_id].get("current_en", 0.0)  # type: ignore[attr-defined]
        boost_en_cost = getattr(unit, "boost_en_cost", DEFAULT_BOOST_EN_COST)
        result["boost_available"] = (
            1.0
            if boost_cooldown_remaining == 0.0 and current_en > boost_en_cost
            else 0.0
        )

        return result

    def _resolve_final_action(
        self, action: str, unit_id: str, strategy_mode: str
    ) -> str:
        """ファジィ推論結果に制約ガードを適用して最終アクションを決定する.

        Args:
            action: ファジィ推論が提案したアクション名
            unit_id: ユニットの文字列 ID
            strategy_mode: 現在の戦略モード

        Returns:
            制約ガード適用後の最終アクション名
        """
        if action == "RETREAT" and not self.retreat_points:  # type: ignore[attr-defined]
            return "MOVE"

        if action == "BOOST_DASH":
            cooldown_remaining = self.unit_resources[unit_id].get(  # type: ignore[attr-defined]
                "boost_cooldown_remaining", 0.0
            )
            if cooldown_remaining > 0.0:
                return "MOVE"

        if action == "ENGAGE_MELEE" and strategy_mode == "RETREAT":
            return "MOVE"

        return action

    def _ai_decision_phase(self, unit: MobileSuit) -> None:
        """中階層ファジィ推論フェーズ: 各ユニットの行動を決定する.

        入力変数（hp_ratio, enemy_count_near, ally_count_near, distance_to_nearest_enemy）
        を FuzzyEngine に渡し、行動（ATTACK / MOVE / RETREAT）を決定する。
        決定した行動は unit_resources[unit_id]["current_action"] に保存される。

        Args:
            unit: 行動を決定するユニット
        """
        if unit.current_hp <= 0:
            return

        unit_id = str(unit.id)

        # 撤退完了済みのユニットは意思決定しない
        if self.unit_resources[unit_id].get("status") == "RETREATED":  # type: ignore[attr-defined]
            return

        pos_unit = unit.position.to_numpy()

        # 索敵済みの敵ユニットを取得
        if unit.team_id is None:
            self.unit_resources[unit_id]["current_action"] = "MOVE"  # type: ignore[attr-defined]
            return

        detected_enemy_ids = self.team_detected_units.get(unit.team_id, set())  # type: ignore[attr-defined]
        detected_enemies = [
            u
            for u in self.units  # type: ignore[attr-defined]
            if u.current_hp > 0
            and u.team_id != unit.team_id
            and u.id in detected_enemy_ids
        ]

        # 索敵済みの敵が0体の場合はファジィ推論をスキップして MOVE を選択
        if not detected_enemies:
            self.unit_resources[unit_id]["current_action"] = "MOVE"  # type: ignore[attr-defined]
            return

        # --- ファジィ入力変数の計算 ---
        hp_ratio = unit.current_hp / max(1, unit.max_hp)

        distances_to_detected = [
            float(np.linalg.norm(e.position.to_numpy() - pos_unit))
            for e in detected_enemies
        ]
        distance_to_nearest_enemy = (
            min(distances_to_detected) if distances_to_detected else 9999.0
        )

        enemy_count_near = float(
            sum(1 for d in distances_to_detected if d <= _FUZZY_NEIGHBOR_RADIUS)
        )

        ally_count_near = float(
            sum(
                1
                for u in self.units  # type: ignore[attr-defined]
                if u.current_hp > 0
                and u.team_id == unit.team_id
                and u.id != unit.id
                and float(np.linalg.norm(u.position.to_numpy() - pos_unit))
                <= _FUZZY_NEIGHBOR_RADIUS
            )
        )

        fuzzy_inputs = {
            "hp_ratio": hp_ratio,
            "enemy_count_near": enemy_count_near,
            "ally_count_near": ally_count_near,
            "distance_to_nearest_enemy": distance_to_nearest_enemy,
        }

        # --- Phase C 入力変数をヘルパーで追加 ---
        nearest_enemy = min(
            detected_enemies,
            key=lambda e: float(np.linalg.norm(e.position.to_numpy() - pos_unit)),
        )
        phase_c_inputs = self._compute_phase_c_fuzzy_inputs(
            unit, unit_id, pos_unit, nearest_enemy
        )
        fuzzy_inputs.update(phase_c_inputs)

        # --- Phase 6-1: angle_to_target を計算してファジィ入力に追加 ---
        # ファジィ選択ターゲット方向と胴体向きとの角度差を計算する。
        # ターゲット未選択時（索敵前 / 索敵済み敵がいない場合）は 180.0（最大値）として扱う。
        # これにより REAR のメンバーシップ度が最大となり、ファジィ推論で ATTACK が選ばれなくなる。
        # この挙動は意図的な設計仕様であり、単純な "敵なし = 旋回" 制御を実現する。
        body_heading_deg = self.unit_resources[unit_id].get("body_heading_deg", 0.0)  # type: ignore[attr-defined]
        target_for_angle: MobileSuit | None = self._select_target_fuzzy(unit)  # type: ignore[attr-defined]
        if target_for_angle is None:
            # ターゲット未選択時は REAR が最大活性化するよう 180.0 に固定
            angle_to_target = 180.0
        else:
            pos_target_for_angle = target_for_angle.position.to_numpy()
            target_dir_deg = math.degrees(
                math.atan2(
                    float(pos_target_for_angle[2] - pos_unit[2]),
                    float(pos_target_for_angle[0] - pos_unit[0]),
                )
            )
            raw_diff = target_dir_deg - body_heading_deg
            angle_to_target = abs(((raw_diff + 180) % 360) - 180)  # 0〜180 に正規化
        fuzzy_inputs["angle_to_target"] = angle_to_target

        # --- 戦略モードに応じたファジィエンジンを選択 ---
        strategy_mode = self._resolve_strategy_mode(unit)  # type: ignore[attr-defined]
        behavior_engine = self._strategy_engines.get(strategy_mode, {}).get(  # type: ignore[attr-defined]
            "behavior", self._fuzzy_engine  # type: ignore[attr-defined]
        )

        # --- ファジィ推論 ---
        _, debug = behavior_engine.infer_with_debug(fuzzy_inputs)
        fuzzy_scores: dict = debug.get("activations", {})

        # 行動を決定: action の活性化度が最も高いラベルを選択
        action_activations: dict[str, float] = fuzzy_scores.get("action", {})
        if action_activations:
            action = max(action_activations, key=lambda k: action_activations[k])
        else:
            action = "MOVE"

        # 制約ガード（RETREAT/BOOST_DASH/ENGAGE_MELEE のフォールバック）
        action = self._resolve_final_action(action, unit_id, strategy_mode)

        # 決定した行動を保存
        self.unit_resources[unit_id]["current_action"] = action  # type: ignore[attr-defined]

        # ファジィ推論結果をログに記録
        ranged_ammo_ratio = phase_c_inputs["ranged_ammo_ratio"]
        los_blocked = phase_c_inputs["los_blocked"]
        boost_available = phase_c_inputs["boost_available"]
        self.logs.append(  # type: ignore[attr-defined]
            BattleLog(
                timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                actor_id=unit.id,
                action_type="AI_DECISION",
                message=(
                    f"{self._format_actor_name(unit)} がファジィ推論により"  # type: ignore[attr-defined]
                    f" [{action}] を選択"
                    f" (HP率:{hp_ratio:.2f} 近敵:{enemy_count_near:.0f}"
                    f" 近味:{ally_count_near:.0f} 近距:{distance_to_nearest_enemy:.0f}m"
                    f" 弾薬率:{ranged_ammo_ratio:.2f} LOS閉塞:{los_blocked:.0f}"
                    f" ブースト可:{boost_available:.0f} 対目標角:{angle_to_target:.1f}°)"
                ),
                position_snapshot=unit.position,
                fuzzy_scores=fuzzy_scores,
                strategy_mode=strategy_mode,
            )
        )

    def _retreat_check_phase(self) -> None:
        """撤退離脱判定フェーズ (Phase 3-3).

        RETREAT 行動中のユニットが撤退ポイントの有効半径内に入ったかどうかをチェックする。
        半径内に入った場合は RETREATED ステータスを設定し、RETREAT_COMPLETE ログを記録する。
        全ユニットが DESTROYED / RETREATED になった場合は戦闘終了とする。
        """
        retreating_units = [
            u
            for u in self.units  # type: ignore[attr-defined]
            if u.current_hp > 0
            and self.unit_resources[str(u.id)]["status"] == "ACTIVE"  # type: ignore[attr-defined]
            and self.unit_resources[str(u.id)].get("current_action") == "RETREAT"  # type: ignore[attr-defined]
        ]

        for unit in retreating_units:
            unit_id = str(unit.id)
            pos_unit = unit.position.to_numpy()

            # 対象ユニットに適用可能な撤退ポイントを抽出
            applicable_rps = [
                rp
                for rp in self.retreat_points  # type: ignore[attr-defined]
                if rp.team_id is None or rp.team_id == unit.team_id
            ]

            for rp in applicable_rps:
                rp_pos = rp.position.to_numpy()
                dist = float(np.linalg.norm(rp_pos - pos_unit))
                if dist <= rp.radius:
                    # 撤退完了
                    self.unit_resources[unit_id]["status"] = "RETREATED"  # type: ignore[attr-defined]
                    self.logs.append(  # type: ignore[attr-defined]
                        BattleLog(
                            timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                            actor_id=unit.id,
                            action_type="RETREAT_COMPLETE",
                            message=(
                                f"{self._format_actor_name(unit)} が撤退ポイントに到達し、"  # type: ignore[attr-defined]
                                f"戦線から離脱した。"
                            ),
                            position_snapshot=unit.position,
                        )
                    )
                    break

        # 勝利判定: ACTIVE な生存ユニットのチームが 1 つ以下なら戦闘終了
        active_teams = {
            u.team_id
            for u in self.units  # type: ignore[attr-defined]
            if u.current_hp > 0 and self.unit_resources[str(u.id)]["status"] == "ACTIVE"  # type: ignore[attr-defined]
        }
        if len(active_teams) <= 1:
            self.is_finished = True  # type: ignore[attr-defined]

    def _update_body_heading(self, actor: MobileSuit, dt: float) -> None:
        """胴体（砲塔）の向きを毎ステップ更新する (Phase 6-1).

        アクションとターゲット有無に応じた目標方向へ body_turn_rate で旋回制限を適用し、
        `unit_resources[unit_id]["body_heading_deg"]` を更新する。

        旋回ルール:
        - ATTACK / ENGAGE_MELEE かつターゲットあり → ターゲット方向
        - MOVE かつターゲットあり → ターゲット方向（ストレイフ移動）
        - それ以外（MOVE でターゲットなし / RETREAT / その他）→ movement_heading_deg

        Args:
            actor: 対象ユニット
            dt: 時間ステップ幅 (s)
        """
        if actor.current_hp <= 0:
            return

        unit_id = str(actor.id)
        resources = self.unit_resources[unit_id]  # type: ignore[attr-defined]

        if resources.get("status") == "RETREATED":
            return

        current_body_heading: float = resources.get("body_heading_deg", 0.0)
        current_action = resources.get("current_action", "MOVE")
        movement_heading: float = resources.get("movement_heading_deg", 0.0)

        # ターゲットを取得（攻撃対象のみ対象; 選択失敗時は None）
        target: MobileSuit | None = None
        if current_action in ("ATTACK", "ENGAGE_MELEE", "MOVE"):
            target = self._select_target_fuzzy(actor)  # type: ignore[attr-defined]

        # 目標方向を決定
        if target is not None and current_action in ("ATTACK", "ENGAGE_MELEE", "MOVE"):
            pos_actor = actor.position.to_numpy()
            pos_target = target.position.to_numpy()
            target_heading = math.degrees(
                math.atan2(
                    float(pos_target[2] - pos_actor[2]),
                    float(pos_target[0] - pos_actor[0]),
                )
            )
        else:
            target_heading = movement_heading

        # 旋回制限を適用
        body_turn_rate: float = getattr(actor, "body_turn_rate", 720.0)
        max_rotation = body_turn_rate * dt
        angular_diff = ((target_heading - current_body_heading + 180) % 360) - 180
        actual_rotation = max(-max_rotation, min(max_rotation, angular_diff))
        resources["body_heading_deg"] = current_body_heading + actual_rotation

    def _refresh_phase(self, dt: float = 0.1) -> None:
        """リフレッシュフェーズ: ENの回復とクールダウンの減少."""
        for unit in self.units:  # type: ignore[attr-defined]
            if unit.current_hp <= 0:
                continue

            unit_id = str(unit.id)
            resources = self.unit_resources[unit_id]  # type: ignore[attr-defined]

            is_boosting: bool = resources.get("is_boosting", False)

            if is_boosting:
                # ブースト中: EN 消費（boost_en_cost × dt）
                boost_en_cost = getattr(unit, "boost_en_cost", DEFAULT_BOOST_EN_COST)
                resources["current_en"] = max(
                    0.0, resources["current_en"] - boost_en_cost * dt
                )
                # ブースト継続時間を加算
                resources["boost_elapsed"] = resources.get("boost_elapsed", 0.0) + dt
            else:
                # 非ブースト中: EN を回復（最大値を超えない）
                current_en = resources["current_en"]
                max_en = unit.max_en
                en_recovery = unit.en_recovery
                new_en = min(current_en + en_recovery, max_en)
                resources["current_en"] = new_en

                # ブーストクールダウンを減算
                cooldown = resources.get("boost_cooldown_remaining", 0.0)
                if cooldown > 0.0:
                    resources["boost_cooldown_remaining"] = max(0.0, cooldown - dt)

            # 武器のクールダウンを減少
            for _, weapon_state in resources["weapon_states"].items():
                if weapon_state["current_cool_down"] > 0:
                    weapon_state["current_cool_down"] -= 1

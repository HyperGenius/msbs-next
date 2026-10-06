# backend/app/engine/ai_decision.py
"""戦略・AI決定・後退チェックフェーズのミックスイン."""

import math
from typing import TYPE_CHECKING

import numpy as np

from app.engine.battle_utils import is_melee_weapon
from app.engine.calculator import PilotStats
from app.engine.combat import has_los
from app.engine.constants import (
    DEFAULT_BOOST_EN_COST,
    DISENGAGE_COOLDOWN_SEC,
    DISENGAGE_DISTANCE_MAX,
    DISENGAGE_DISTANCE_MIN,
    DISENGAGE_MAX_SEC,
    DISENGAGE_RANGED_PREFERENCE_SEC,
    IDLE_STALEMATE_ATTACK_SEC,
    IDLE_STALEMATE_SEC,
)
from app.engine.engagement import (
    DisengageState,
    dominance,
    restart_bout,
    stalemate,
    track_engagement,
)
from app.engine.engagement_style import (
    disengage_max_sec,
    perceived_dominance,
    ranged_preference_multiplier,
    stalemate_patience,
    tactics_range,
)
from app.models.models import BattleLog, MobileSuit, Vector3

if TYPE_CHECKING:
    from app.engine.strategy_controller import TeamMetrics

# 近隣ユニット検索半径 (m)
_FUZZY_NEIGHBOR_RADIUS = 500.0
# 膠着度がこの値以上なら、仕切り直しの理由を膠着とする。未満なら劣勢とする。
_DISENGAGE_STALEMATE_REASON_THRESHOLD = 0.5


class AiDecisionMixin:
    """戦略・AI決定・後退チェックフェーズのミックスイン."""

    # BattleSimulator が提供するインスタンス属性 (mypy 向け型宣言のみ; 実体は simulation.py)
    units: list[MobileSuit]

    if TYPE_CHECKING:

        def _collect_team_metrics(self, team_id: str) -> "TeamMetrics": ...

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
            team_id: self._collect_team_metrics(team_id)
            for team_id in team_ids  # type: ignore[attr-defined]
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
        self,
        action: str,
        unit_id: str,
        strategy_mode: str,
        idle_stalemate: bool = False,
        keeps_range: bool = False,
    ) -> str:
        """ファジィ推論結果に制約ガードを適用して最終アクションを決定する.

        Args:
            action: ファジィ推論が提案したアクション名
            unit_id: ユニットの文字列 ID
            strategy_mode: 現在の戦略モード
            idle_stalemate: 撃たない膠着が続いているか（`_is_idle_stalemate()`）
            keeps_range: 格闘へ突入せず射撃で戦うか（`_keeps_range()`）

        Returns:
            制約ガード適用後の最終アクション名
        """
        # MOVE は撃たない。両機が撃たずに周回すると、時間切れまで決着しない。
        if action == "RETREAT" and not self.retreat_points:  # type: ignore[attr-defined]
            return "ATTACK" if idle_stalemate else "MOVE"
        if action == "MOVE" and idle_stalemate:
            return "ATTACK"

        if action == "BOOST_DASH":
            cooldown_remaining = self.unit_resources[unit_id].get(  # type: ignore[attr-defined]
                "boost_cooldown_remaining", 0.0
            )
            if cooldown_remaining > 0.0:
                return "MOVE"

        if action == "ENGAGE_MELEE":
            if strategy_mode == "RETREAT":
                return "MOVE"
            if keeps_range or self._prefers_ranged(unit_id):
                return "ATTACK"

        if action == "HIT_AND_AWAY":
            current_en = self.unit_resources[unit_id].get("current_en", 999)  # type: ignore[attr-defined]
            if current_en < 10:
                return "ATTACK"

        return action

    def _compute_engagement_inputs(
        self, unit: MobileSuit, target: MobileSuit | None
    ) -> dict[str, float]:
        """現在のターゲットとの交戦記録を更新し、膠着度と優勢度を返す.

        どちらも `tactics.range` とパイロット能力で補正した、判断用の値を返す。
        """
        resources = self.unit_resources[str(unit.id)]  # type: ignore[attr-defined]
        if target is None:
            resources["engagement"] = None
            return {"stalemate": 0.0, "dominance": 0.0}

        now = float(self.elapsed_time)  # type: ignore[attr-defined]
        distance = float(
            np.linalg.norm(target.position.to_numpy() - unit.position.to_numpy())
        )
        record = track_engagement(
            resources.get("engagement"), str(target.id), distance, now
        )
        resources["engagement"] = record
        pilot = self._pilot_stats(unit)
        patience = stalemate_patience(tactics_range(unit), pilot)
        return {
            "stalemate": stalemate(record, now, unit.max_hp, target.max_hp, patience),
            "dominance": perceived_dominance(
                dominance(record, unit.max_hp, target.max_hp), pilot
            ),
        }

    def _pilot_stats(self, unit: MobileSuit) -> PilotStats:
        """機体のパイロット能力を返す. 未登録なら全能力 0 とする."""
        return self.unit_pilot_stats.get(str(unit.id), PilotStats())  # type: ignore[attr-defined]

    def _keeps_range(self, unit: MobileSuit) -> bool:
        """格闘へ突入せず、射撃で戦う設定かを返す.

        `tactics.range` が RANGED / FLEE で、射撃武器を持つときに真。
        射撃武器が無ければ、設定より使える武器を優先する。
        """
        return tactics_range(unit) in ("RANGED", "FLEE") and any(
            not is_melee_weapon(w) for w in unit.weapons
        )

    def _disengage_max_sec(self, unit: MobileSuit) -> float:
        """仕切り直しの最長時間 (s) を返す."""
        return disengage_max_sec(DISENGAGE_MAX_SEC, self._pilot_stats(unit))

    def _ranged_preference_sec(self, unit: MobileSuit) -> float:
        """仕切り直しの後に射撃武器を優先する時間 (s) を返す."""
        return DISENGAGE_RANGED_PREFERENCE_SEC * ranged_preference_multiplier(
            tactics_range(unit)
        )

    def _decide_action(
        self,
        unit: MobileSuit,
        action_activations: dict[str, float],
        strategy_mode: str,
        target: MobileSuit | None,
        fuzzy_inputs: dict[str, float],
    ) -> str:
        """活性化度が最も高い行動を選び、仕切り直しの状態と制約ガードを適用する.

        実行中の仕切り直しは、終える条件を満たすまで続ける。
        仕切り直しを始められないときは、DISENGAGE を除いて選び直す。
        """
        unit_id = str(unit.id)
        resources = self.unit_resources[unit_id]  # type: ignore[attr-defined]
        candidates = dict(action_activations)

        if resources.get("disengage") is not None:
            if self._should_continue_disengage(unit, target, strategy_mode, candidates):
                return "DISENGAGE"
            self._end_disengage(unit)

        if target is None or not self._can_start_disengage(unit, target, strategy_mode):
            candidates.pop("DISENGAGE", None)

        if candidates:
            action = max(candidates, key=lambda k: candidates[k])
        else:
            action = "MOVE"

        action = self._resolve_final_action(
            action,
            unit_id,
            strategy_mode,
            idle_stalemate=action in ("RETREAT", "MOVE")
            and self._is_idle_stalemate(unit, target),
            keeps_range=self._keeps_range(unit),
        )
        if action == "DISENGAGE" and target is not None:
            self._start_disengage(unit, target, fuzzy_inputs)
        return action

    def _can_start_disengage(
        self, unit: MobileSuit, target: MobileSuit, strategy_mode: str
    ) -> bool:
        """仕切り直しを始められるかを返す.

        RETREAT 戦略中は既存の撤退を優先する。交戦記録が無いときと、
        既に目標距離より離れているときは始めない。
        格闘武器を持たない機体は始めない。切り替える攻撃方法が無く、
        仕切り直しが後退するだけになるため。
        """
        resources = self.unit_resources[str(unit.id)]  # type: ignore[attr-defined]
        if (
            strategy_mode == "RETREAT"
            or not any(is_melee_weapon(w) for w in unit.weapons)
            or resources.get("engagement") is None
            or float(self.elapsed_time)  # type: ignore[attr-defined]
            < resources.get("disengage_cooldown_until", 0.0)
        ):
            return False
        distance = float(
            np.linalg.norm(target.position.to_numpy() - unit.position.to_numpy())
        )
        return distance < self._disengage_target_distance(unit)

    def _should_continue_disengage(
        self,
        unit: MobileSuit,
        target: MobileSuit | None,
        strategy_mode: str,
        action_activations: dict[str, float],
    ) -> bool:
        """実行中の仕切り直しを続けるかを返す.

        目標距離に着くか、最長時間（`_disengage_max_sec()`）が過ぎたら終える。
        撤退（RETREAT 戦略と、撤退ポイントへの RETREAT）は仕切り直しより優先する。
        """
        state: DisengageState = self.unit_resources[str(unit.id)]["disengage"]  # type: ignore[attr-defined]
        if strategy_mode == "RETREAT":
            return False
        if action_activations and self.retreat_points:  # type: ignore[attr-defined]
            top = max(action_activations, key=lambda k: action_activations[k])
            if top == "RETREAT":
                return False
        if target is None or str(target.id) != state.opponent_id:
            return False
        if float(self.elapsed_time) - state.started_at >= self._disengage_max_sec(unit):  # type: ignore[attr-defined]
            return False
        distance = float(
            np.linalg.norm(target.position.to_numpy() - unit.position.to_numpy())
        )
        return distance < state.target_distance

    def _disengage_target_distance(self, unit: MobileSuit) -> float:
        """仕切り直しで下がる目標距離を返す.

        射撃武器があれば、その目標交戦距離を `DISENGAGE_DISTANCE_MIN`〜
        `DISENGAGE_DISTANCE_MAX` に収めて使う。無ければ下限まで下がる。
        """
        distances = [
            engagement.distance
            for w in unit.weapons
            if not is_melee_weapon(w)
            and (engagement := self._engagement_range(unit, w)) is not None  # type: ignore[attr-defined]
        ]
        if not distances:
            return DISENGAGE_DISTANCE_MIN
        return min(DISENGAGE_DISTANCE_MAX, max(DISENGAGE_DISTANCE_MIN, max(distances)))

    def _start_disengage(
        self, unit: MobileSuit, target: MobileSuit, fuzzy_inputs: dict[str, float]
    ) -> None:
        """仕切り直しを始め、DISENGAGE ログを記録する.

        自分の交戦記録は捨てる。次の膠着度・優勢度は仕切り直しの後から数える。
        相手の記録は優勢度だけ数え直す。昔の命中による優勢が続くと、
        相手がいつまでも膠着とみなさないため。ブーストが使えれば使う。
        """
        unit_id = str(unit.id)
        resources = self.unit_resources[unit_id]  # type: ignore[attr-defined]
        now = float(self.elapsed_time)  # type: ignore[attr-defined]
        record = resources.get("engagement")
        target_distance = self._disengage_target_distance(unit)

        resources["disengage"] = DisengageState(
            opponent_id=str(target.id),
            started_at=now,
            target_distance=target_distance,
        )
        resources["engagement"] = None
        target_resources = self.unit_resources[str(target.id)]  # type: ignore[attr-defined]
        target_record = target_resources.get("engagement")
        if target_record is not None and target_record.opponent_id == unit_id:
            restart_bout(target_record)
        # 終了時に `_end_disengage()` が期限を付け直す。仕切り直し中の命中で 0 になる。
        resources["ranged_preference_until"] = (
            now + self._disengage_max_sec(unit) + self._ranged_preference_sec(unit)
        )

        boost_en_cost = getattr(unit, "boost_en_cost", DEFAULT_BOOST_EN_COST)
        if (
            not resources.get("is_boosting", False)
            and resources.get("boost_cooldown_remaining", 0.0) <= 0.0
            and resources.get("current_en", 0.0) > boost_en_cost
        ):
            self._start_boost(unit)  # type: ignore[attr-defined]

        stalemate_value = fuzzy_inputs.get("stalemate", 0.0)
        is_stalemate = stalemate_value >= _DISENGAGE_STALEMATE_REASON_THRESHOLD
        reason_text = "互角と見て" if is_stalemate else "劣勢と見て"
        self.logs.append(  # type: ignore[attr-defined]
            BattleLog(
                timestamp=now,
                actor_id=unit.id,
                action_type="DISENGAGE",
                target_id=target.id,
                message=(
                    f"{self._format_actor_name(unit)}は{target.name}との攻防を"  # type: ignore[attr-defined]
                    f"{reason_text}距離を取り、仕切り直す"
                ),
                position_snapshot=unit.position,
                velocity_snapshot=Vector3.from_numpy(resources["velocity_vec"]),
                chatter=self._generate_chatter(unit, "disengage"),  # type: ignore[attr-defined]
                details={
                    "reason": "STALEMATE" if is_stalemate else "DISADVANTAGE",
                    "stalemate": round(stalemate_value, 3),
                    "dominance": round(fuzzy_inputs.get("dominance", 0.0), 3),
                    "target_distance": round(target_distance, 1),
                    "attacks": record.attacks if record else 0,
                    "hits": record.hits if record else 0,
                    "attacked": record.attacked if record else 0,
                    "attacked_hits": record.attacked_hits if record else 0,
                },
            )
        )

    def _end_disengage(self, unit: MobileSuit) -> None:
        """仕切り直しを終え、射撃優先と次の仕切り直しまでの待ち時間を始める."""
        resources = self.unit_resources[str(unit.id)]  # type: ignore[attr-defined]
        now = float(self.elapsed_time)  # type: ignore[attr-defined]
        resources["disengage"] = None
        resources["disengage_cooldown_until"] = now + DISENGAGE_COOLDOWN_SEC
        if resources.get("ranged_preference_until", 0.0) > now:
            resources["ranged_preference_until"] = now + self._ranged_preference_sec(
                unit
            )
        if resources.get("is_boosting", False):
            self._end_boost(unit, "仕切り直し完了")  # type: ignore[attr-defined]

    def _prefers_ranged(self, unit_id: str) -> bool:
        """仕切り直し中と、その後の射撃優先の期間かを返す."""
        resources = self.unit_resources[unit_id]  # type: ignore[attr-defined]
        return resources.get("disengage") is not None or float(
            self.elapsed_time  # type: ignore[attr-defined]
        ) < resources.get("ranged_preference_until", 0.0)

    def _is_idle_stalemate(self, unit: MobileSuit, target: MobileSuit | None) -> bool:
        """武器の射程内に敵がいるのに、攻撃のやり取りが無い状態が続いているかを返す.

        `IDLE_STALEMATE_SEC` 攻撃が無ければ、その後 `IDLE_STALEMATE_ATTACK_SEC` は
        膠着が続いているとみなす。1 発撃つたびに膠着が解けて撃たなくなるのを防ぐため。
        """
        if target is None or not self._is_within_weapon_range(unit, target):
            return False
        resources = self.unit_resources[str(unit.id)]  # type: ignore[attr-defined]
        now = float(self.elapsed_time)  # type: ignore[attr-defined]
        if now < resources.get("idle_stalemate_until", 0.0):
            return True
        if now - resources.get("last_attack_exchange_at", 0.0) < IDLE_STALEMATE_SEC:
            return False
        resources["idle_stalemate_until"] = now + IDLE_STALEMATE_ATTACK_SEC
        return True

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
            # 仕切り直しのブーストは、仕切り直しを終えるまで止まらないため終える。
            if self.unit_resources[unit_id].get("disengage") is not None:  # type: ignore[attr-defined]
                self._end_disengage(unit)
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
                True  # bool (sum counts True=1); fixes mypy [misc] int-vs-bool error
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
        fuzzy_inputs.update(self._compute_engagement_inputs(unit, target_for_angle))

        # --- 戦略モードに応じたファジィエンジンを選択 ---
        strategy_mode = self._resolve_strategy_mode(unit)  # type: ignore[attr-defined]
        behavior_engine = self._strategy_engines.get(strategy_mode, {}).get(  # type: ignore[attr-defined]
            "behavior",
            self._fuzzy_engine,  # type: ignore[attr-defined]
        )

        # --- ファジィ推論 ---
        _, debug = behavior_engine.infer_with_debug(fuzzy_inputs)
        fuzzy_scores: dict = debug.get("activations", {})

        action_activations: dict[str, float] = fuzzy_scores.get("action", {})
        action = self._decide_action(
            unit, action_activations, strategy_mode, target_for_angle, fuzzy_inputs
        )

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
                    f" ブースト可:{boost_available:.0f} 対目標角:{angle_to_target:.1f}°"
                    f" 膠着:{fuzzy_inputs['stalemate']:.2f}"
                    f" 優勢:{fuzzy_inputs['dominance']:+.2f})"
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
        - ATTACK / ENGAGE_MELEE / DISENGAGE かつターゲットあり → ターゲット方向
        - MOVE かつターゲットが武器の射程内 → ターゲット方向
        - 上記以外 → movement_heading_deg（実際の移動方向）

        MOVE で射程内の敵を向くのは、側面・背面の敵を正面に収めるため。
        移動方向に追従すると、密着した両機が互いの周りを回り続けて攻撃に移れない。

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

        target: MobileSuit | None = None
        # 仕切り直しはターゲットを向いたまま下がる。背を向けると背面から撃たれるため。
        if current_action in ("ATTACK", "ENGAGE_MELEE", "DISENGAGE"):
            target = self._select_target_fuzzy(actor)  # type: ignore[attr-defined]
        elif current_action == "MOVE":
            target = self._select_target_fuzzy(actor)  # type: ignore[attr-defined]
            if target is not None and not self._is_within_weapon_range(actor, target):
                target = None

        if target is not None:
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

    @staticmethod
    def _is_within_weapon_range(actor: MobileSuit, target: MobileSuit) -> bool:
        """装備武器の最大射程内にターゲットがいるかを返す."""
        if not actor.weapons:
            return False
        max_range = max(w.range for w in actor.weapons)
        distance = float(
            np.linalg.norm(target.position.to_numpy() - actor.position.to_numpy())
        )
        return distance <= max_range

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
                new_en = min(current_en + en_recovery * dt, max_en)
                resources["current_en"] = new_en

                # ブーストクールダウンを減算
                cooldown = resources.get("boost_cooldown_remaining", 0.0)
                if cooldown > 0.0:
                    resources["boost_cooldown_remaining"] = max(0.0, cooldown - dt)

            # 武器のクールダウンを減少 (Phase 6-2: 秒単位)
            for _, weapon_state in resources["weapon_states"].items():
                remaining = weapon_state.get("cooldown_remaining_sec", 0.0)
                if remaining > 0.0:
                    weapon_state["cooldown_remaining_sec"] = max(0.0, remaining - dt)

            # 武装持ち替えの行動不能タイムを減少
            switch_lock_remaining = resources.get(
                "weapon_switch_lock_remaining_sec", 0.0
            )
            if switch_lock_remaining > 0.0:
                resources["weapon_switch_lock_remaining_sec"] = max(
                    0.0, switch_lock_remaining - dt
                )

# backend/app/engine/targeting.py
"""索敵・ターゲット選択・武器選択処理のミックスイン."""

from typing import TYPE_CHECKING

import numpy as np

from app.engine.combat import has_los
from app.engine.constants import (
    SPECIAL_ENVIRONMENT_EFFECTS,
)
from app.models.models import BattleLog, MobileSuit, Weapon

if TYPE_CHECKING:
    pass

# ターゲット選択ファジィ推論: 距離の最大値 (m)
_TARGET_SELECTION_MAX_DIST = 3000.0
# 武器選択ファジィ推論: 距離の最大値 (m)
_WEAPON_SELECTION_MAX_DIST = 3000.0


class TargetingMixin:
    """索敵・ターゲット選択・武器選択処理のミックスイン."""

    # BattleSimulator が提供するインスタンス属性 (mypy 向け型宣言のみ; 実体は simulation.py)
    units: list[MobileSuit]
    team_detected_units: dict[str, set]

    def _detection_phase(self) -> None:
        """索敵フェーズ: 各ユニットが索敵範囲内の敵を発見."""
        alive_units = [u for u in self.units if u.current_hp > 0]  # type: ignore[attr-defined]

        # ミノフスキー粒子効果: 索敵範囲を半減
        sensor_multiplier = 1.0
        if "MINOVSKY" in self.special_effects:  # type: ignore[attr-defined]
            minovsky = SPECIAL_ENVIRONMENT_EFFECTS["MINOVSKY"]
            sensor_multiplier = minovsky["sensor_range_multiplier"]

        for unit in alive_units:
            if unit.team_id is None:
                continue
            # 敵対勢力を特定 (team_idが異なるユニットが敵)
            potential_targets = [t for t in alive_units if t.team_id != unit.team_id]

            pos_unit = unit.position.to_numpy()
            effective_sensor_range = unit.sensor_range * sensor_multiplier

            # 索敵範囲内の敵をチェック
            for target in potential_targets:
                unit_id = str(unit.id)
                pos_target = target.position.to_numpy()
                distance = float(np.linalg.norm(pos_target - pos_unit))

                if target.id in self.team_detected_units[unit.team_id]:  # type: ignore[attr-defined]
                    # 既に発見済み — LOS が失われていないか再チェック（障害物がある場合）
                    if self.obstacles and not has_los(  # type: ignore[attr-defined]
                        pos_unit,
                        pos_target,
                        self.obstacles,  # type: ignore[attr-defined]
                    ):
                        # LOS 喪失: 発見済みリストから除外し最終座標を記憶
                        self.team_detected_units[unit.team_id].discard(target.id)  # type: ignore[attr-defined]
                        self.unit_resources[unit_id]["last_known_enemy_position"][  # type: ignore[attr-defined]
                            str(target.id)
                        ] = pos_target.tolist()
                    continue

                # 索敵判定（ミノフスキー粒子による索敵範囲低下を適用）
                if distance <= effective_sensor_range:
                    # LOS チェック（障害物がある場合のみ）
                    if self.obstacles and not has_los(  # type: ignore[attr-defined]
                        pos_unit,
                        pos_target,
                        self.obstacles,  # type: ignore[attr-defined]
                    ):
                        # 障害物により遮断されているため発見不可
                        continue

                    # 発見！
                    self.team_detected_units[unit.team_id].add(target.id)  # type: ignore[attr-defined]

                    # 発見ログを追加
                    dist_label = self._get_distance_label(distance)  # type: ignore[attr-defined]
                    actor_name = self._format_actor_name(unit)  # type: ignore[attr-defined]
                    if "MINOVSKY" in self.special_effects:  # type: ignore[attr-defined]
                        detect_message = (
                            f"{actor_name}が濃密なミノフスキー粒子の中、"
                            f"{dist_label}に{target.name}の反応を捉えた！"
                        )
                    else:
                        detect_message = (
                            f"{actor_name}が{dist_label}に{target.name}を発見！"
                        )
                    self.logs.append(  # type: ignore[attr-defined]
                        BattleLog(
                            timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                            actor_id=unit.id,
                            action_type="DETECTION",
                            target_id=target.id,
                            message=detect_message,
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
            weapon_power_avg = sum(w.power for w in target.weapons) / len(
                target.weapons
            )

        # 戦略価値 = 最大HP + 平均武器威力
        # Note: パイロットレベルは将来的に実装予定
        strategic_value = target.max_hp + weapon_power_avg

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

    def _calculate_attack_power(self, unit: MobileSuit) -> float:
        """ユニットの攻撃力を計算する（武器威力の最大値）.

        Args:
            unit: 評価対象のユニット

        Returns:
            攻撃力スコア（武器がない場合は0.0）
        """
        if not unit.weapons:
            return 0.0
        return float(max(w.power for w in unit.weapons))

    def _select_target_legacy(self, actor: MobileSuit) -> MobileSuit | None:
        """ターゲットを選択する（戦術と索敵状態に基づくレガシー実装）.

        Note:
            Phase 3以降で廃止予定。フォールバック用として残す。
        """
        # ターゲット選択: team_idが異なる生存ユニットをリストアップ
        potential_targets = [
            u
            for u in self.units
            if u.current_hp > 0 and u.team_id != actor.team_id  # type: ignore[attr-defined]
        ]

        # 索敵済みの敵のみをターゲット候補とする
        if actor.team_id is None:
            return None
        detected_targets = [
            t
            for t in potential_targets
            if t.id in self.team_detected_units[actor.team_id]  # type: ignore[attr-defined]
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
            self._log_target_selection(  # type: ignore[attr-defined]
                actor, target, "WEAKEST", f"HP: {target.current_hp}"
            )
        elif tactics_priority == "STRONGEST":
            # 戦略価値が最も高い敵を選択
            target = max(
                detected_targets, key=lambda t: self._calculate_strategic_value(t)
            )
            strategic_value = self._calculate_strategic_value(target)
            self._log_target_selection(  # type: ignore[attr-defined]
                actor, target, "STRONGEST", f"戦略価値: {strategic_value:.1f}"
            )
        elif tactics_priority == "THREAT":
            # 脅威度が最も高い敵を選択
            target = max(
                detected_targets, key=lambda t: self._calculate_threat_level(actor, t)
            )
            threat_level = self._calculate_threat_level(actor, target)
            self._log_target_selection(  # type: ignore[attr-defined]
                actor, target, "THREAT", f"脅威度: {threat_level:.2f}"
            )
        elif tactics_priority == "RANDOM":
            import random

            # ランダムに敵を選択
            target = random.choice(detected_targets)
            self._log_target_selection(actor, target, "RANDOM", "ランダム選択")  # type: ignore[attr-defined]
        else:  # CLOSEST (デフォルト)
            # 最も近い敵を選択
            target = min(
                detected_targets,
                key=lambda t: np.linalg.norm(t.position.to_numpy() - pos_actor),
            )
            distance = np.linalg.norm(target.position.to_numpy() - pos_actor)
            self._log_target_selection(  # type: ignore[attr-defined]
                actor, target, "CLOSEST", f"距離: {int(distance)}m"
            )
        return target

    def _select_target_fuzzy(self, actor: MobileSuit) -> MobileSuit | None:
        """ターゲットを選択する（ファジィ推論による動的優先度スコア計算）.

        各索敵済み候補に対してファジィ推論を実行し、最も高い target_priority
        スコアを持つユニットを選択する。推論失敗時は CLOSEST フォールバックを使用する。

        Args:
            actor: 選択を行う機体

        Returns:
            選択されたターゲット。候補が0件の場合は None。
        """
        # ターゲット選択: team_idが異なる生存ユニットをリストアップ
        potential_targets = [
            u
            for u in self.units
            if u.current_hp > 0 and u.team_id != actor.team_id  # type: ignore[attr-defined]
        ]

        # 索敵済みの敵のみをターゲット候補とする
        if actor.team_id is None:
            return None
        detected_targets = [
            t
            for t in potential_targets
            if t.id in self.team_detected_units[actor.team_id]  # type: ignore[attr-defined]
        ]

        # ターゲットが存在しない場合はNoneを返す
        if not detected_targets:
            return None

        pos_actor = actor.position.to_numpy()

        # 戦略モードに応じたターゲット選択エンジンを選択
        strategy_mode = self._resolve_strategy_mode(actor)  # type: ignore[attr-defined]
        target_engine = self._strategy_engines.get(strategy_mode, {}).get(  # type: ignore[attr-defined]
            "target",
            self._target_selection_fuzzy_engine,  # type: ignore[attr-defined]
        )

        # 各候補にファジィ推論を実行し優先度スコアを計算
        try:
            best_target: MobileSuit | None = None
            best_score: float = -1.0
            best_fuzzy_scores: dict | None = None
            all_scores: dict[str, float] = {}

            for candidate in detected_targets:
                pos_candidate = candidate.position.to_numpy()
                distance = float(np.linalg.norm(pos_candidate - pos_actor))
                distance = min(distance, _TARGET_SELECTION_MAX_DIST)

                hp_ratio = candidate.current_hp / max(1, candidate.max_hp)
                attack_power = self._calculate_attack_power(candidate)
                unit_id_candidate = str(candidate.id)
                candidate_action = self.unit_resources.get(unit_id_candidate, {}).get(  # type: ignore[attr-defined]
                    "current_action", "MOVE"
                )
                is_attacking_ally = 1.0 if candidate_action == "ATTACK" else 0.0

                fuzzy_inputs = {
                    "target_hp_ratio": hp_ratio,
                    "target_distance": distance,
                    "target_attack_power": attack_power,
                    "is_attacking_ally": is_attacking_ally,
                }

                result, debug = target_engine.infer_with_debug(fuzzy_inputs)
                score = result.get("target_priority", 0.0)
                all_scores[str(candidate.id)] = score

                if score > best_score:
                    best_score = score
                    best_target = candidate
                    best_fuzzy_scores = {
                        "layer": "target_selection",
                        "selected_target_id": str(candidate.id),
                        "score": score,
                        "inputs": fuzzy_inputs,
                        "fuzzified": debug.get("fuzzified", {}),
                        "activations": debug.get("activations", {}),
                    }

            if best_target is None:
                # フォールバック: CLOSEST
                best_target = min(
                    detected_targets,
                    key=lambda t: np.linalg.norm(t.position.to_numpy() - pos_actor),
                )
                fallback_distance = float(
                    np.linalg.norm(best_target.position.to_numpy() - pos_actor)
                )
                self._log_target_selection(  # type: ignore[attr-defined]
                    actor,
                    best_target,
                    "CLOSEST",
                    f"距離: {int(fallback_distance)}m",
                )
                return best_target

            # ループ完了後に全候補スコアを記録
            if best_fuzzy_scores is not None:
                best_fuzzy_scores["all_scores"] = all_scores

            self._log_target_selection(  # type: ignore[attr-defined]
                actor,
                best_target,
                "FUZZY",
                f"優先度スコア: {best_score:.3f}",
                fuzzy_scores=best_fuzzy_scores,
            )
            return best_target

        except (KeyError, ValueError, ZeroDivisionError, AttributeError):
            # 推論失敗時は CLOSEST フォールバック
            fallback = min(
                detected_targets,
                key=lambda t: np.linalg.norm(t.position.to_numpy() - pos_actor),
            )
            fallback_distance = float(
                np.linalg.norm(fallback.position.to_numpy() - pos_actor)
            )
            self._log_target_selection(  # type: ignore[attr-defined]
                actor, fallback, "CLOSEST", f"距離: {int(fallback_distance)}m"
            )
            return fallback

    def _is_weapon_usable(self, actor: MobileSuit, weapon: Weapon) -> bool:
        """武器が現在使用可能か判定する（クールダウン・EN・弾薬をチェック）.

        Args:
            actor: 使用するユニット
            weapon: チェック対象の武器

        Returns:
            True if the weapon can be used, False otherwise.
        """
        unit_id = str(actor.id)
        resources = self.unit_resources[unit_id]  # type: ignore[attr-defined]
        weapon_state = self._get_or_init_weapon_state(weapon, resources)  # type: ignore[attr-defined]
        can_use, _ = self._check_attack_resources(weapon, weapon_state, resources)  # type: ignore[attr-defined]
        return can_use

    def _select_weapon_fuzzy(
        self, actor: MobileSuit, target: MobileSuit
    ) -> Weapon | None:
        """武器を選択する（ファジィ推論による動的スコア計算）.

        使用可能な武器（クールダウン=0・EN残量≥コスト・弾薬残量>0）に対して
        ファジィ推論を実行し、最高 weapon_score の武器を選択する。
        推論失敗時は最初の使用可能武器にフォールバックする。

        Args:
            actor: 武器を選択するユニット
            target: 攻撃対象ユニット

        Returns:
            選択された武器。使用可能な武器が0件の場合は None。
        """
        # 使用可能な武器（クールダウン・EN・弾薬チェック）をリストアップ
        usable_weapons = [w for w in actor.weapons if self._is_weapon_usable(actor, w)]

        if not usable_weapons:
            return None

        unit_id = str(actor.id)
        resources = self.unit_resources[unit_id]  # type: ignore[attr-defined]

        # ターゲットの耐性値を取得
        target_beam_resistance = float(getattr(target, "beam_resistance", 0.0))
        target_physical_resistance = float(getattr(target, "physical_resistance", 0.0))

        # 距離計算（最大値でクランプ）
        pos_actor = actor.position.to_numpy()
        pos_target = target.position.to_numpy()
        distance = float(np.linalg.norm(pos_target - pos_actor))
        distance = min(distance, _WEAPON_SELECTION_MAX_DIST)

        # アクターの現在EN比率を計算
        current_en = float(resources["current_en"])
        max_en = float(max(1, actor.max_en))
        current_en_ratio = current_en / max_en

        # 戦略モードに応じた武器選択エンジンを選択
        strategy_mode = self._resolve_strategy_mode(actor)  # type: ignore[attr-defined]
        weapon_engine = self._strategy_engines.get(strategy_mode, {}).get(  # type: ignore[attr-defined]
            "weapon",
            self._weapon_selection_fuzzy_engine,  # type: ignore[attr-defined]
        )

        try:
            best_weapon: Weapon | None = None
            best_score: float = -1.0
            best_fuzzy_scores: dict | None = None
            all_scores: dict[str, float] = {}

            for weapon in usable_weapons:
                # 武器の弾薬比率を計算（無制限弾薬の場合は 1.0）
                weapon_state = resources["weapon_states"].get(weapon.id, {})
                current_ammo = weapon_state.get("current_ammo")
                if weapon.max_ammo is not None and weapon.max_ammo > 0:
                    ammo_ratio = float(current_ammo or 0) / weapon.max_ammo
                else:
                    ammo_ratio = 1.0

                # ビーム武器か実弾武器かを数値化（TRUE=1.0 / FALSE=0.0）
                weapon_is_beam = (
                    1.0 if getattr(weapon, "type", "PHYSICAL") == "BEAM" else 0.0
                )

                fuzzy_inputs = {
                    "distance_to_target": distance,
                    "current_en_ratio": current_en_ratio,
                    "ammo_ratio": ammo_ratio,
                    "target_beam_resistance": target_beam_resistance,
                    "target_physical_resistance": target_physical_resistance,
                    "weapon_is_beam": weapon_is_beam,
                }

                result, debug = weapon_engine.infer_with_debug(fuzzy_inputs)
                score = result.get("weapon_score", 0.0)
                all_scores[str(weapon.id)] = score

                if score > best_score:
                    best_score = score
                    best_weapon = weapon
                    best_fuzzy_scores = {
                        "layer": "weapon_selection",
                        "selected_weapon_id": str(weapon.id),
                        "selected_weapon_name": weapon.name,
                        "score": score,
                        "inputs": fuzzy_inputs,
                        "fuzzified": debug.get("fuzzified", {}),
                        "activations": debug.get("activations", {}),
                    }

            if best_fuzzy_scores is not None:
                best_fuzzy_scores["all_scores"] = all_scores

            return best_weapon

        except (KeyError, ValueError, ZeroDivisionError, AttributeError):
            # 推論失敗時は最初の使用可能武器をフォールバックとして返す
            return usable_weapons[0]

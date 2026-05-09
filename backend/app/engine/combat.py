# backend/app/engine/combat.py
"""攻撃・命中・ダメージ・破壊処理のミックスイン."""

import math
import random
from typing import TYPE_CHECKING

import numpy as np

from app.engine.calculator import (
    calculate_critical_chance,
    calculate_damage_variance,
    calculate_hit_chance,
)
from app.engine.constants import (
    CLOSE_RANGE,
    COMBO_BASE_CHANCE,
    COMBO_CHAIN_DECAY,
    COMBO_DAMAGE_MULTIPLIER,
    COMBO_MAX_CHAIN,
    DEFAULT_FIRE_ARC_DEG,
    MELEE_CLOSE_ACCURACY_BONUS,
    MELEE_MID_ACCURACY_BONUS,
    MELEE_RANGE,
    RANGED_CLOSE_ACCURACY_PENALTY,
    RANGED_MID_ACCURACY_PENALTY,
    SPECIAL_ENVIRONMENT_EFFECTS,
)
from app.models.models import BattleLog, MobileSuit, Obstacle, Vector3, Weapon

if TYPE_CHECKING:
    pass


def has_los(
    pos_a: np.ndarray,
    pos_b: np.ndarray,
    obstacles: "list[Obstacle]",
) -> bool:
    """pos_a から pos_b への視線が障害物に遮られていないか判定する（3D Ray-Sphere 交差判定）.

    障害物を 3D 球体としてモデル化し、Y 軸（高度）も考慮する。
    a = |unit_dir|² = 1 なので簡略化した判別式を使用する。

    Args:
        pos_a: 射撃者の位置 (3D numpy 配列)
        pos_b: ターゲットの位置 (3D numpy 配列)
        obstacles: 障害物リスト

    Returns:
        True: LOS あり（視線が通っている）
        False: LOS なし（障害物で遮断されている）
    """
    if not obstacles:
        return True

    direction = pos_b - pos_a
    dist = float(np.linalg.norm(direction))
    if dist < 1e-6:
        return True
    unit_dir = direction / dist

    for obs in obstacles:
        obs_center = np.array([obs.position.x, obs.position.y, obs.position.z])
        oc = pos_a - obs_center
        b = 2.0 * np.dot(oc, unit_dir)
        c = np.dot(oc, oc) - obs.radius**2
        discriminant = b**2 - 4.0 * c
        if discriminant < 0:
            continue
        t = (-b - math.sqrt(discriminant)) / 2.0
        if 0.0 < t < dist:
            return False
    return True


class CombatMixin:
    """攻撃・命中・ダメージ・破壊処理のミックスイン."""

    def _get_or_init_weapon_state(self, weapon: Weapon, resources: dict) -> dict:
        """武器状態を取得または初期化する."""
        weapon_state = resources["weapon_states"].get(weapon.id)
        if not weapon_state:
            weapon_state = {
                "current_ammo": weapon.max_ammo
                if weapon.max_ammo is not None
                else None,
                "current_cool_down": 0,
            }
            resources["weapon_states"][weapon.id] = weapon_state
        return weapon_state

    @staticmethod
    def _get_accuracy_modifier(distance: float, weapon_type: str) -> float:
        """距離と武器種別に応じた命中率補正乗数を返す (Phase C).

        Args:
            distance: ターゲットまでの距離 (m)
            weapon_type: 武器種別 ("MELEE" / "CLOSE_RANGE" / "RANGED" など)

        Returns:
            命中率に乗算する補正値 (0.4〜1.5)
        """
        if weapon_type in ("MELEE", "CLOSE_RANGE"):
            if distance <= MELEE_RANGE:
                return MELEE_CLOSE_ACCURACY_BONUS  # 1.5
            if distance <= CLOSE_RANGE:
                return MELEE_MID_ACCURACY_BONUS  # 1.2
            return 0.8
        else:
            if distance <= MELEE_RANGE:
                return RANGED_CLOSE_ACCURACY_PENALTY  # 0.4
            if distance <= CLOSE_RANGE:
                return RANGED_MID_ACCURACY_PENALTY  # 0.7
            return 1.0

    def _check_attack_resources(
        self, weapon: Weapon, weapon_state: dict, resources: dict
    ) -> tuple[bool, str]:
        """攻撃に必要なリソースをチェックする.

        MELEE 武器は弾薬・EN 消費が発生しないため、該当チェックをスキップする (Phase C)。

        Returns:
            tuple[bool, str]: (攻撃可能か, 失敗理由)
        """
        is_melee_weapon = getattr(
            weapon, "weapon_type", "RANGED"
        ) == "MELEE" or getattr(weapon, "is_melee", False)

        # MELEE武器は弾数・EN消費ゼロ（弾切れ/EN不足チェックをスキップ）
        if not is_melee_weapon:
            # 弾数チェック（max_ammoがNoneまたは0の場合は無制限）
            if weapon.max_ammo is not None and weapon.max_ammo > 0:
                current_ammo = weapon_state["current_ammo"]
                if current_ammo is None or current_ammo <= 0:
                    return False, "弾切れ"

            # ENチェック
            if weapon.en_cost > 0:
                current_en = resources["current_en"]
                if current_en < weapon.en_cost:
                    return False, "EN不足"

        # クールダウンチェック
        if weapon_state["current_cool_down"] > 0:
            return (
                False,
                f"クールダウン中 (残り{weapon_state['current_cool_down']}ターン)",
            )

        return True, ""

    def _calculate_hit_chance(
        self, actor: MobileSuit, target: MobileSuit, weapon: Weapon, distance: float
    ) -> tuple[float, float]:
        """命中率を計算する.

        距離補正乗数を適用する（Phase C — 近接戦闘システム）。

        Returns:
            tuple[float, float]: (命中率, 最適距離からの差)
        """
        distance_from_optimal = abs(distance - weapon.optimal_range)
        dist_penalty = distance_from_optimal * weapon.decay_rate
        evasion_bonus = target.mobility * 10
        hit_chance = float(weapon.accuracy - dist_penalty - evasion_bonus)

        # 機体パラメータ補正: 命中補正と回避補正を適用
        hit_chance += getattr(actor, "accuracy_bonus", 0.0)
        hit_chance -= getattr(target, "evasion_bonus", 0.0)

        # プレイヤーの攻撃時はスキル補正を適用
        if actor.side == "PLAYER":
            accuracy_skill_level = self.player_skills.get("accuracy_up", 0)  # type: ignore[attr-defined]
            hit_chance += accuracy_skill_level * 2.0  # +2% / Lv

        # 敵への攻撃時は回避スキル補正を適用
        if target.side == "PLAYER":
            evasion_skill_level = self.player_skills.get("evasion_up", 0)  # type: ignore[attr-defined]
            hit_chance -= evasion_skill_level * 2.0  # 敵の命中率を -2% / Lv

        # 障害物効果: 命中率をペナルティ
        if "OBSTACLE" in self.special_effects:  # type: ignore[attr-defined]
            obstacle = SPECIAL_ENVIRONMENT_EFFECTS["OBSTACLE"]
            hit_chance -= obstacle["accuracy_penalty"]

        # パイロットステータス補正を適用
        attacker_dex = self.player_pilot_stats.dex if actor.side == "PLAYER" else 0  # type: ignore[attr-defined]
        defender_int = self.player_pilot_stats.intel if target.side == "PLAYER" else 0  # type: ignore[attr-defined]
        hit_chance = calculate_hit_chance(
            hit_chance,
            distance_from_optimal=distance_from_optimal,
            decay_rate=weapon.decay_rate,
            attacker_dex=attacker_dex,
            defender_int=defender_int,
        )

        # 距離補正乗数を適用 (Phase C — 近接戦闘システム)
        weapon_type = getattr(weapon, "weapon_type", "RANGED")
        # is_melee フラグが True の場合は MELEE 扱い
        if getattr(weapon, "is_melee", False) and weapon_type == "RANGED":
            weapon_type = "MELEE"
        accuracy_modifier = self._get_accuracy_modifier(distance, weapon_type)
        hit_chance = hit_chance * accuracy_modifier

        # 命中率を [0.0, 100.0] にクランプ
        hit_chance = max(0.0, min(100.0, hit_chance))

        return hit_chance, distance_from_optimal

    def _consume_attack_resources(
        self, weapon: Weapon, weapon_state: dict, resources: dict
    ) -> None:
        """攻撃実行時のリソースを消費する.

        MELEE 武器は弾薬・EN 消費がゼロのためスキップする (Phase C)。
        """
        is_melee_weapon = getattr(
            weapon, "weapon_type", "RANGED"
        ) == "MELEE" or getattr(weapon, "is_melee", False)

        if not is_melee_weapon:
            # 弾数を消費
            if weapon.max_ammo is not None and weapon.max_ammo > 0:
                if weapon_state["current_ammo"] is not None:
                    weapon_state["current_ammo"] -= 1

            # ENを消費
            if weapon.en_cost > 0:
                resources["current_en"] -= weapon.en_cost

        # クールダウンを設定（MELEE武器でも適用）
        if weapon.cool_down_turn > 0:
            weapon_state["current_cool_down"] = weapon.cool_down_turn

    def _log_attack_wait(
        self,
        actor: MobileSuit,
        weapon: Weapon,
        weapon_state: dict,
        failure_reason: str,
        snapshot: Vector3,
    ) -> None:
        """攻撃リソース不足時の待機ログを追記する."""
        actor_name = self._format_actor_name(actor)  # type: ignore[attr-defined]
        weapon_display = f"[{weapon.name}]" if weapon.name else "[格闘]"
        if "弾切れ" in failure_reason:
            wait_message = f"{actor_name}は{weapon_display}の弾薬が尽き、攻撃手段がない"
        elif "EN不足" in failure_reason:
            wait_message = f"{actor_name}はENが枯渇し、{weapon_display}を使えず待機中"
        elif "クールダウン" in failure_reason:
            remaining_turns = weapon_state.get("current_cool_down", 0)
            wait_message = f"{actor_name}は{weapon_display}の冷却を待ちながら（残り{remaining_turns}ターン）、やむなく待機"
        else:
            wait_message = f"{actor_name}は{failure_reason}のため攻撃できない（待機）"
        self.logs.append(  # type: ignore[attr-defined]
            BattleLog(
                timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                actor_id=actor.id,
                action_type="WAIT",
                message=wait_message,
                position_snapshot=snapshot,
            )
        )

    def _process_attack(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        distance: float,
        pos_actor: np.ndarray,
        weapon: Weapon | None = None,
    ) -> None:
        """攻撃処理を実行する."""
        if weapon is None:
            weapon = actor.get_active_weapon()
        if not weapon:
            return

        snapshot = Vector3.from_numpy(pos_actor)
        unit_id = str(actor.id)

        # --- Phase 6-1: fire_arc_deg ゲートチェック ---
        if self._is_fire_arc_blocked(actor, target, weapon, pos_actor, snapshot):  # type: ignore[attr-defined]
            return
        resources = self.unit_resources[unit_id]  # type: ignore[attr-defined]

        # LOS チェック（格闘武器はスキップ、障害物がある場合のみ）
        if self._is_los_blocked(actor, target, weapon, pos_actor, snapshot):  # type: ignore[attr-defined]
            return

        # リソース状態を取得または初期化
        weapon_state = self._get_or_init_weapon_state(weapon, resources)

        # リソースチェック
        can_attack, failure_reason = self._check_attack_resources(
            weapon, weapon_state, resources
        )

        if not can_attack:
            self._log_attack_wait(actor, weapon, weapon_state, failure_reason, snapshot)
            return

        # 命中率計算
        hit_chance, distance_from_optimal = self._calculate_hit_chance(
            actor, target, weapon, distance
        )

        # スキルボーナスを個別に計算（スキル発動判定のため）
        skill_bonus = 0.0
        if actor.side == "PLAYER":
            accuracy_skill_level = self.player_skills.get("accuracy_up", 0)  # type: ignore[attr-defined]
            skill_bonus += accuracy_skill_level * 2.0
        if target.side == "PLAYER":
            evasion_skill_level = self.player_skills.get("evasion_up", 0)  # type: ignore[attr-defined]
            skill_bonus -= evasion_skill_level * 2.0

        # ダイスロール（ロール値を保持してスキル発動判定に使用）
        roll = random.uniform(0, 100)
        is_hit = roll <= hit_chance

        # スキル発動判定: スキルボーナスがあり、それが命中/回避の結果を変えた場合
        # hit_chance はクランプ済みのため、スキルなし命中率も [0, 100] にクランプして近似
        skill_activated = False
        if skill_bonus != 0.0:
            hit_chance_without_skill = max(0.0, min(100.0, hit_chance - skill_bonus))
            would_have_hit_without_skill = roll <= hit_chance_without_skill
            skill_activated = is_hit != would_have_hit_without_skill

        # 距離による状況メッセージ（命中/ミスのコンテキストとして使用）
        is_optimal_distance = distance_from_optimal < 50
        is_bad_distance = distance_from_optimal > 200

        actor_name = self._format_actor_name(actor)  # type: ignore[attr-defined]
        weapon_display = f"[{weapon.name}]" if weapon.name else "[格闘]"
        log_base = f"{actor_name}が{weapon_display}で攻撃！ (命中: {int(hit_chance)}%)"

        # リソース消費
        self._consume_attack_resources(weapon, weapon_state, resources)

        # 攻撃時のセリフ生成
        attack_chatter = self._generate_chatter(actor, "attack")  # type: ignore[attr-defined]

        if is_hit:
            self._process_hit(
                actor,
                target,
                weapon,
                log_base,
                snapshot,
                attack_chatter,
                is_optimal_distance,
                skill_activated,
            )
        else:
            self._process_miss(
                actor,
                target,
                log_base,
                snapshot,
                attack_chatter,
                is_bad_distance,
                skill_activated,
            )

    def _is_fire_arc_blocked(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        weapon: Weapon,
        pos_actor: np.ndarray,
        snapshot: Vector3,
    ) -> bool:
        """射撃弧制限ゲートチェック. 弧外なら True を返してログを記録する."""
        # MELEE 武器は全方位攻撃可能なので弧制限ゲートをスキップする
        is_melee_weapon = getattr(
            weapon, "weapon_type", "RANGED"
        ) == "MELEE" or getattr(weapon, "is_melee", False)
        if is_melee_weapon:
            return False
        unit_id = str(actor.id)
        pos_target = target.position.to_numpy()
        target_dir_deg = math.degrees(
            math.atan2(
                float(pos_target[2] - pos_actor[2]),
                float(pos_target[0] - pos_actor[0]),
            )
        )
        body_heading = self.unit_resources[unit_id].get("body_heading_deg", 0.0)  # type: ignore[attr-defined]
        raw_diff = target_dir_deg - body_heading
        angle_to_tgt = abs(((raw_diff + 180) % 360) - 180)
        effective_fire_arc = getattr(weapon, "fire_arc_deg", DEFAULT_FIRE_ARC_DEG)
        if angle_to_tgt <= effective_fire_arc:
            return False
        # 弧外: 攻撃をスキップして旋回を継続する
        actor_name = self._format_actor_name(actor)  # type: ignore[attr-defined]
        weapon_display = f"[{weapon.name}]" if weapon.name else "[武装]"
        self.logs.append(  # type: ignore[attr-defined]
            BattleLog(
                timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                actor_id=actor.id,
                action_type="TURNING_TO_TARGET",
                target_id=target.id,
                message=(
                    f"{actor_name}の{weapon_display}は射撃弧外"
                    f"（角度差:{angle_to_tgt:.1f}° > 弧:{effective_fire_arc:.1f}°）"
                    f"のため旋回中"
                ),
                position_snapshot=snapshot,
            )
        )
        return True

    def _is_los_blocked(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        weapon: Weapon,
        pos_actor: np.ndarray,
        snapshot: Vector3,
    ) -> bool:
        """LOS（射線）チェック. 射線なしなら True を返してログを記録する."""
        is_melee = getattr(weapon, "is_melee", False)
        if is_melee or not self.obstacles:  # type: ignore[attr-defined]
            return False
        pos_target = target.position.to_numpy()
        if has_los(pos_actor, pos_target, self.obstacles):  # type: ignore[attr-defined]
            return False
        actor_name = self._format_actor_name(actor)  # type: ignore[attr-defined]
        weapon_display = f"[{weapon.name}]" if weapon.name else "[武装]"
        self.logs.append(  # type: ignore[attr-defined]
            BattleLog(
                timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                actor_id=actor.id,
                action_type="ATTACK_BLOCKED_LOS",
                target_id=target.id,
                message=(
                    f"{actor_name}の{weapon_display}は障害物に遮られ、"
                    f"{target.name}への射線が確保できない"
                ),
                position_snapshot=snapshot,
            )
        )
        return True

    def _process_hit(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        weapon: Weapon,
        log_base: str,
        snapshot: Vector3,
        attack_chatter: str | None = None,
        is_optimal_distance: bool = False,
        skill_activated: bool = False,
    ) -> None:
        """命中時の処理."""
        base_damage, log_msg = self._calculate_hit_base_damage(
            actor, target, weapon, log_base
        )
        base_damage, resistance_msg = self._apply_hit_damage_modifiers(
            actor, target, weapon, base_damage
        )

        # パイロットステータス補正: ダメージ乱数変動・LUK 完全回避
        attacker_tou = self.player_pilot_stats.tou if actor.side == "PLAYER" else 0  # type: ignore[attr-defined]
        attacker_luk = self.player_pilot_stats.luk if actor.side == "PLAYER" else 0  # type: ignore[attr-defined]
        defender_dex = self.player_pilot_stats.dex if target.side == "PLAYER" else 0  # type: ignore[attr-defined]
        defender_tou = self.player_pilot_stats.tou if target.side == "PLAYER" else 0  # type: ignore[attr-defined]
        defender_luk = self.player_pilot_stats.luk if target.side == "PLAYER" else 0  # type: ignore[attr-defined]

        final_damage, perfect_evade = calculate_damage_variance(
            base_damage,
            attacker_luk=attacker_luk,
            attacker_tou=attacker_tou,
            defender_dex=defender_dex,
            defender_tou=defender_tou,
            defender_luk=defender_luk,
        )

        # 完全回避（LUK 発動）
        if perfect_evade:
            # 被弾時のセリフ生成
            hit_chatter = self._generate_chatter(target, "hit")  # type: ignore[attr-defined]
            self.logs.append(  # type: ignore[attr-defined]
                BattleLog(
                    timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                    actor_id=actor.id,
                    action_type="MISS",
                    target_id=target.id,
                    damage=0,
                    message=f"{log_base} -> 直撃コース！ しかし{target.name}は信じられない反射神経で紙一重の回避！ ★ [LUK]の奇跡が働いた！",
                    position_snapshot=snapshot,
                    chatter=attack_chatter or hit_chatter,
                )
            )
            return

        target.current_hp -= final_damage

        # 被弾時のセリフ生成
        hit_chatter = self._generate_chatter(target, "hit")  # type: ignore[attr-defined]

        # 命中状況テキスト
        is_crit = "クリティカルヒット" in log_msg
        if is_crit:
            hit_text = " -> ★★ クリティカルヒット！！"
        elif is_optimal_distance:
            hit_text = " -> 最適射程でクリーンヒット！"
        else:
            hit_text = " -> 命中！"

        # ダメージ表現（HP割合ベース）
        damage_desc = self._get_damage_description(final_damage, target)  # type: ignore[attr-defined]
        # HP残量コメント
        hp_comment = self._get_hp_status_comment(target)  # type: ignore[attr-defined]

        # 装甲軽減メッセージ
        if resistance_msg:
            if resistance_msg.endswith("、"):
                # 低軽減: 装甲メッセージの後にダメージ表現を追加
                damage_message = f"{resistance_msg}{target.name}に{final_damage}ダメージ！（{damage_desc}）{hp_comment}"
            else:
                # 高軽減: 装甲メッセージ自体にダメージの深刻度が含まれている
                damage_message = f"{resistance_msg} {target.name}に{final_damage}ダメージ！{hp_comment}"
        elif is_crit:
            # クリティカルヒット: 弱点を捉えた強調表現を追加
            damage_message = f" 弱点を的確に捉え、{target.name}に{final_damage}ダメージ！（{damage_desc}）{hp_comment}"
        else:
            damage_message = (
                f" {target.name}に{final_damage}ダメージ！（{damage_desc}）{hp_comment}"
            )

        self.logs.append(  # type: ignore[attr-defined]
            BattleLog(
                timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                actor_id=actor.id,
                action_type="ATTACK",
                target_id=target.id,
                damage=final_damage,
                target_max_hp=target.max_hp,
                message=f"{log_base}{hit_text}{damage_message}",
                position_snapshot=snapshot,
                weapon_name=weapon.name if weapon else None,
                chatter=attack_chatter or hit_chatter,
                skill_activated=True if skill_activated else None,
            )
        )

        if target.current_hp <= 0:
            self._process_destruction(target)
            return

        # 格闘コンボシステム (Phase C — MELEE 武器のみ適用)
        is_melee_weapon = getattr(
            weapon, "weapon_type", "RANGED"
        ) == "MELEE" or getattr(weapon, "is_melee", False)
        if is_melee_weapon:
            self._process_melee_combo(
                actor, target, weapon, base_damage, snapshot, attack_chatter
            )

    def _process_melee_combo(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        weapon: Weapon,
        base_damage: int,
        snapshot: Vector3,
        attack_chatter: str | None = None,
    ) -> None:
        """格闘コンボシステム: 命中時に確率的にコンボ（連続ヒット）が発生する (Phase C).

        コンボ計算:
            n 連目の発生確率 = COMBO_BASE_CHANCE × COMBO_CHAIN_DECAY^(n-1)
            例: 1連目 30%、2連目 15%、3連目 7.5%

        Args:
            actor: 攻撃ユニット
            target: 攻撃対象
            weapon: 格闘武器
            base_damage: 最初の命中で計算されたベースダメージ
            snapshot: 攻撃時点の座標スナップショット
            attack_chatter: 攻撃時のセリフ
        """
        combo_count = 0
        combo_total_damage = 0
        combo_chance = COMBO_BASE_CHANCE

        for _ in range(COMBO_MAX_CHAIN):
            if random.random() > combo_chance:
                break
            if target.current_hp <= 0:
                break

            combo_count += 1
            combo_damage = int(base_damage * COMBO_DAMAGE_MULTIPLIER)
            combo_total_damage += combo_damage
            target.current_hp -= combo_damage

            if target.current_hp <= 0:
                target.current_hp = 0

            # コンボ継続確率を減衰
            combo_chance *= COMBO_CHAIN_DECAY

        if combo_count > 0:
            combo_message = f"{combo_count}Combo {combo_total_damage}ダメージ!!"
            self.logs.append(  # type: ignore[attr-defined]
                BattleLog(
                    timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                    actor_id=actor.id,
                    action_type="MELEE_COMBO",
                    target_id=target.id,
                    damage=combo_total_damage,
                    target_max_hp=target.max_hp,
                    message=(
                        f"{self._format_actor_name(actor)} の格闘コンボ！"  # type: ignore[attr-defined]
                        f" {combo_message}"
                    ),
                    position_snapshot=snapshot,
                    weapon_name=weapon.name if weapon else None,
                    chatter=attack_chatter,
                    combo_count=combo_count,
                    combo_message=combo_message,
                )
            )

            if target.current_hp <= 0:
                self._process_destruction(target)

    def _calculate_hit_base_damage(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        weapon: Weapon,
        log_base: str,
    ) -> tuple[int, str]:
        """命中時の基礎ダメージとログメッセージを算出する."""
        base_crit_rate = 0.05

        if actor.side == "PLAYER":
            crit_skill_level = self.player_skills.get("crit_rate_up", 0)  # type: ignore[attr-defined]
            base_crit_rate += (crit_skill_level * 1.0) / 100.0  # +1% / Lv

        attacker_int = self.player_pilot_stats.intel if actor.side == "PLAYER" else 0  # type: ignore[attr-defined]
        defender_tou_crit = (
            self.player_pilot_stats.tou if target.side == "PLAYER" else 0  # type: ignore[attr-defined]
        )
        adjusted_crit_rate = calculate_critical_chance(
            base_crit_rate,
            attacker_int=attacker_int,
            defender_tou=defender_tou_crit,
        )

        is_crit = random.random() < adjusted_crit_rate
        if not is_crit:
            return max(1, weapon.power - target.armor), f"{log_base} -> 命中！"
        return int(weapon.power * 1.2), f"{log_base} -> クリティカルヒット！！"

    def _apply_hit_damage_modifiers(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        weapon: Weapon,
        base_damage: int,
    ) -> tuple[int, str]:
        """命中ダメージへスキル・適性・耐性補正を適用する.

        MELEE 武器は耐性計算をバイパスする（属性なし物理として扱う）(Phase C)。
        """
        if actor.side == "PLAYER":
            damage_skill_level = self.player_skills.get("damage_up", 0)  # type: ignore[attr-defined]
            damage_multiplier = 1.0 + (damage_skill_level * 3.0) / 100.0  # +3% / Lv
            base_damage = int(base_damage * damage_multiplier)

        is_melee = getattr(weapon, "weapon_type", "RANGED") == "MELEE" or getattr(
            weapon, "is_melee", False
        )
        aptitude = (
            getattr(actor, "melee_aptitude", 1.0)
            if is_melee
            else getattr(actor, "shooting_aptitude", 1.0)
        )
        base_damage = int(base_damage * aptitude)

        resistance_msg = ""

        # MELEE武器は耐性無視（属性なし物理として扱う）
        if is_melee:
            return base_damage, resistance_msg

        weapon_type = getattr(weapon, "type", "PHYSICAL")
        if weapon_type == "BEAM":
            resistance = getattr(target, "beam_resistance", 0.0)
            if resistance > 0:
                base_damage = int(base_damage * (1.0 - resistance))
                if resistance >= 0.20:
                    resistance_msg = f" しかし{target.name}の強固なビーム吸収コーティングが衝撃を受け止め、ダメージは軽微に！"
                else:
                    resistance_msg = f" {target.name}のビーム吸収コーティングをわずかに弾きながらも、"
        elif weapon_type == "PHYSICAL":
            resistance = getattr(target, "physical_resistance", 0.0)
            if resistance > 0:
                base_damage = int(base_damage * (1.0 - resistance))
                if resistance >= 0.20:
                    resistance_msg = f" しかし{target.name}の強固な対実弾装甲が衝撃を受け止め、ダメージは軽微に！"
                else:
                    resistance_msg = (
                        f" {target.name}の対実弾装甲をわずかに弾きながらも、"
                    )

        return base_damage, resistance_msg

    def _process_miss(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        log_base: str,
        snapshot: Vector3,
        attack_chatter: str | None = None,
        is_bad_distance: bool = False,
        skill_activated: bool = False,
    ) -> None:
        """ミス時の処理."""
        # ミス時のセリフ生成
        miss_chatter = self._generate_chatter(actor, "miss")  # type: ignore[attr-defined]

        if is_bad_distance:
            miss_text = f" -> 距離が合わず、{target.name}に回避された！"
        else:
            miss_text = f" -> {target.name}に回避された！"

        self.logs.append(  # type: ignore[attr-defined]
            BattleLog(
                timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                actor_id=actor.id,
                action_type="MISS",
                target_id=target.id,
                message=f"{log_base}{miss_text}",
                position_snapshot=snapshot,
                chatter=attack_chatter or miss_chatter,
                skill_activated=True if skill_activated else None,
            )
        )

    def _process_destruction(self, target: MobileSuit) -> None:
        """撃破時の処理."""
        target.current_hp = 0

        # ステータスを DESTROYED に更新 (Phase 3-3)
        target_id = str(target.id)
        self.unit_resources[target_id]["status"] = "DESTROYED"  # type: ignore[attr-defined]

        # 撃破時のセリフ生成
        destroyed_chatter = self._generate_chatter(target, "destroyed")  # type: ignore[attr-defined]

        # エース撃破時の特別メッセージ
        ace_msg = ""
        if getattr(target, "is_ace", False):
            ace_msg = (
                f" ★【エース撃破】{getattr(target, 'pilot_name', 'Unknown')}を撃破！"
            )

        self.logs.append(  # type: ignore[attr-defined]
            BattleLog(
                timestamp=self.elapsed_time,  # type: ignore[attr-defined]
                actor_id=target.id,
                action_type="DESTROYED",
                message=f"{self._format_actor_name(target)} は爆散した...{ace_msg}",  # type: ignore[attr-defined]
                position_snapshot=target.position,
                chatter=destroyed_chatter,
            )
        )
        # 勝利判定 (ACTIVE な生存ユニットのteam_idの種類が1つ以下なら戦闘終了)
        active_teams = {
            u.team_id
            for u in self.units  # type: ignore[attr-defined]
            if u.current_hp > 0 and self.unit_resources[str(u.id)]["status"] == "ACTIVE"  # type: ignore[attr-defined]
        }
        if len(active_teams) <= 1:
            self.is_finished = True  # type: ignore[attr-defined]

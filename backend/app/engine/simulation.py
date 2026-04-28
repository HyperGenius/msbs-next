# backend/app/engine/simulation.py
import random
from pathlib import Path

import numpy as np

from app.core.npc_data import BATTLE_CHATTER
from app.engine.calculator import (
    PilotStats,
    calculate_critical_chance,
    calculate_damage_variance,
    calculate_hit_chance,
)
from app.engine.constants import (
    SPECIAL_ENVIRONMENT_EFFECTS,
    TERRAIN_ADAPTABILITY_MODIFIERS,
)
from app.engine.fuzzy_engine import FuzzyEngine
from app.models.models import BattleLog, MobileSuit, Vector3, Weapon

_MAX_STEPS = 5000
_FUZZY_RULES_PATH = (
    Path(__file__).parent.parent.parent / "data" / "fuzzy_rules" / "aggressive.json"
)
_TARGET_SELECTION_FUZZY_RULES_PATH = (
    Path(__file__).parent.parent.parent
    / "data"
    / "fuzzy_rules"
    / "aggressive_target_selection.json"
)
# 近隣ユニット検索半径 (m)
_FUZZY_NEIGHBOR_RADIUS = 500.0
# ターゲット選択ファジィ推論: 距離の最大値 (m)
_TARGET_SELECTION_MAX_DIST = 3000.0


class BattleSimulator:
    """戦闘シミュレータ."""

    def __init__(
        self,
        player: MobileSuit,
        enemies: list[MobileSuit],
        player_skills: dict[str, int] | None = None,
        environment: str = "SPACE",
        special_effects: list[str] | None = None,
        player_pilot_stats: PilotStats | None = None,
    ):
        """初期化.

        Args:
            player: プレイヤー機体
            enemies: 敵機体リスト
            player_skills: プレイヤーのスキル (skill_id: level)
            environment: 戦闘環境 (SPACE/GROUND/COLONY/UNDERWATER)
            special_effects: 特殊環境効果リスト (MINOVSKY/GRAVITY_WELL/OBSTACLE)
            player_pilot_stats: プレイヤーのパイロットステータス (DEX/INT/REF/TOU/LUK)

        Note:
            team_id が未設定のユニットは in-place で team_id が自動付与されます。
        """
        self.player = player
        self.enemies = enemies
        self.units: list[MobileSuit] = [player] + enemies
        self.logs: list[BattleLog] = []
        self.elapsed_time: float = 0.0
        self._step_count: int = 0
        self.is_finished = False
        self.player_skills = player_skills or {}
        self.environment = environment
        self.special_effects: list[str] = special_effects or []
        self.player_pilot_stats: PilotStats = player_pilot_stats or PilotStats()

        # team_id が未設定のユニットにはソロ参加用のIDを自動付与
        for unit in self.units:
            if unit.team_id is None:
                unit.team_id = str(unit.id)

        # 索敵状態管理 (チーム単位で共有)
        self.team_detected_units: dict[str, set] = {
            unit.team_id: set() for unit in self.units if unit.team_id is not None
        }

        # リソース状態管理（戦闘中の一時ステータス）
        self.unit_resources: dict = {}
        for unit in self.units:
            unit_id = str(unit.id)
            self.unit_resources[unit_id] = {
                "current_en": unit.max_en,
                "current_propellant": unit.max_propellant,
                "weapon_states": {},
                "current_action": "MOVE",  # 中階層ファジィ推論で決定した行動
            }
            # 各武器のリソース状態を初期化
            for weapon in unit.weapons:
                weapon_id = weapon.id
                self.unit_resources[unit_id]["weapon_states"][weapon_id] = {
                    "current_ammo": weapon.max_ammo
                    if weapon.max_ammo is not None
                    else None,
                    "current_cool_down": 0,
                }

        # 中階層ファジィ推論エンジン（AGGRESSIVEルールセット）
        self._fuzzy_engine: FuzzyEngine = FuzzyEngine.from_json(
            _FUZZY_RULES_PATH, default_output={"action": 0.0}
        )
        # 低階層ファジィ推論エンジン: ターゲット選択（AGGRESSIVEルールセット）
        self._target_selection_fuzzy_engine: FuzzyEngine = FuzzyEngine.from_json(
            _TARGET_SELECTION_FUZZY_RULES_PATH,
            default_output={"target_priority": 0.0},
        )

    def _generate_chatter(self, unit: MobileSuit, chatter_type: str) -> str | None:
        """NPCのセリフを生成する.

        Args:
            unit: ユニット
            chatter_type: セリフの種類 (attack/hit/destroyed/miss)

        Returns:
            str | None: セリフ。NPCでない場合や確率で発言しない場合はNone
        """
        # NPCでない場合はセリフなし
        if not unit.personality:
            return None

        # 30%の確率でセリフを発言
        if random.random() > 0.3:
            return None

        # 性格に応じたセリフを取得
        personality = unit.personality
        if personality in BATTLE_CHATTER:
            chatter_list = BATTLE_CHATTER[personality].get(chatter_type, [])
            if chatter_list:
                return random.choice(chatter_list)

        return None

    def _format_actor_name(
        self, actor: MobileSuit, viewer_team_id: str | None = None
    ) -> str:
        """パイロット名付きの機体名を返す.

        Args:
            actor: 機体
            viewer_team_id: 視点チームID。指定された場合、そのチームから未索敵の機体は
                            「UNKNOWN機」と表示する。省略時はアクターが敵チームなら
                            プレイヤーチーム視点で自動判定する。

        Returns:
            - 未索敵の敵: 「UNKNOWN機」
            - パイロット名がある場合: 「[パイロット名]のMS名」
            - パイロット名がない場合: 「MS名」
        """
        # 索敵チェック: 視点チームIDを決定
        effective_viewer = viewer_team_id
        if effective_viewer is None and actor.team_id != self.player.team_id:
            # アクターが敵チームの場合、プレイヤー視点で索敵判定を行う
            effective_viewer = self.player.team_id

        if effective_viewer and actor.id not in self.team_detected_units.get(
            effective_viewer, set()
        ):
            return "UNKNOWN機"

        pilot_name = getattr(actor, "pilot_name", None)
        if pilot_name:
            return f"[{pilot_name}]の{actor.name}"
        return actor.name

    def _get_distance_label(self, distance: float) -> str:
        """距離を日本語ラベルに変換する.

        Args:
            distance: 距離(m)

        Returns:
            近距離 / 中距離 / 遠距離
        """
        if distance <= 200:
            return "近距離"
        if distance <= 400:
            return "中距離"
        return "遠距離"

    def _get_damage_description(self, damage: int, target: MobileSuit) -> str:
        """HP割合に基づくダメージ表現を返す.

        Args:
            damage: ダメージ量
            target: 攻撃対象

        Returns:
            致命的なヒット / 手痛いダメージ / ダメージ / 軽微なダメージ
        """
        ratio = damage / max(1, target.max_hp)
        if ratio >= 0.20:
            return "致命的なヒット"
        if ratio >= 0.10:
            return "手痛いダメージ"
        if ratio >= 0.05:
            return "ダメージ"
        return "軽微なダメージ"

    def _get_hp_status_comment(self, target: MobileSuit) -> str:
        """ダメージ後のHP残量に応じた状況コメントを返す.

        Args:
            target: 攻撃対象

        Returns:
            HP残量に応じた状況コメント（余裕がある場合は空文字）
        """
        ratio = target.current_hp / max(1, target.max_hp)
        if ratio <= 0.10:
            return " — 大破寸前...！（残りHP僅少）"
        if ratio <= 0.20:
            return " — 機体が限界に近い！"
        if ratio <= 0.50:
            return " — 戦闘継続能力が低下"
        return ""

    def step(self, dt: float = 0.1) -> None:
        """1時間ステップ分の処理を実行.

        Args:
            dt: 時間ステップ幅（秒）。デフォルト 0.1s。
        """
        if self.is_finished:
            return

        # 最大ステップ数超過 → 引き分けとして終了
        if self._step_count >= _MAX_STEPS:
            self.is_finished = True
            return

        # 1. 索敵フェーズ
        self._detection_phase()

        # 2. AI意思決定フェーズ（中階層ファジィ推論）
        alive_units = [u for u in self.units if u.current_hp > 0]
        for unit in alive_units:
            self._ai_decision_phase(unit)

        # 3. 行動フェーズ（全ユニットを同一ステップで並列処理）
        alive_units = [u for u in self.units if u.current_hp > 0]
        for unit in alive_units:
            if self.is_finished:
                break
            self._action_phase(unit)

        # 4. リソース更新フェーズ（EN回復・クールダウン減少）
        self._refresh_phase()

        # 5. 時間を進める
        self.elapsed_time += dt
        self._step_count += 1

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
        pos_unit = unit.position.to_numpy()

        # 索敵済みの敵ユニットを取得
        if unit.team_id is None:
            self.unit_resources[unit_id]["current_action"] = "MOVE"
            return

        detected_enemy_ids = self.team_detected_units.get(unit.team_id, set())
        detected_enemies = [
            u
            for u in self.units
            if u.current_hp > 0
            and u.team_id != unit.team_id
            and u.id in detected_enemy_ids
        ]

        # 索敵済みの敵が0体の場合はファジィ推論をスキップして MOVE を選択
        if not detected_enemies:
            self.unit_resources[unit_id]["current_action"] = "MOVE"
            return

        # --- ファジィ入力変数の計算 ---
        # hp_ratio: 現在HP / 最大HP
        hp_ratio = unit.current_hp / max(1, unit.max_hp)

        # 最近敵との距離を計算
        distances_to_detected = [
            float(np.linalg.norm(e.position.to_numpy() - pos_unit))
            for e in detected_enemies
        ]
        distance_to_nearest_enemy = (
            min(distances_to_detected) if distances_to_detected else 9999.0
        )

        # enemy_count_near: 索敵済みの敵ユニット数（半径 _FUZZY_NEIGHBOR_RADIUS 以内）
        enemy_count_near = float(
            sum(1 for d in distances_to_detected if d <= _FUZZY_NEIGHBOR_RADIUS)
        )

        # ally_count_near: 同一チームの生存ユニット数（半径 _FUZZY_NEIGHBOR_RADIUS 以内、自分を除く）
        ally_count_near = float(
            sum(
                1
                for u in self.units
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

        # --- ファジィ推論 ---
        _, debug = self._fuzzy_engine.infer_with_debug(fuzzy_inputs)
        fuzzy_scores: dict = debug.get("activations", {})

        # 行動を決定: action の活性化度が最も高いラベルを選択
        action_activations: dict[str, float] = fuzzy_scores.get("action", {})
        if action_activations:
            action = max(action_activations, key=lambda k: action_activations[k])
        else:
            action = "MOVE"

        # RETREAT が出力されたが撤退ポイントが未設定の場合は MOVE にフォールバック
        if action == "RETREAT":
            action = "MOVE"

        # 決定した行動を保存
        self.unit_resources[unit_id]["current_action"] = action

        # ファジィ推論結果をログに記録
        self.logs.append(
            BattleLog(
                timestamp=self.elapsed_time,
                actor_id=unit.id,
                action_type="AI_DECISION",
                message=(
                    f"{self._format_actor_name(unit)} がファジィ推論により"
                    f" [{action}] を選択"
                    f" (HP率:{hp_ratio:.2f} 近敵:{enemy_count_near:.0f}"
                    f" 近味:{ally_count_near:.0f} 近距:{distance_to_nearest_enemy:.0f}m)"
                ),
                position_snapshot=unit.position,
                fuzzy_scores=fuzzy_scores,
                strategy_mode="AGGRESSIVE",
            )
        )

    def _refresh_phase(self) -> None:
        """リフレッシュフェーズ: ENの回復とクールダウンの減少."""
        for unit in self.units:
            if unit.current_hp <= 0:
                continue

            unit_id = str(unit.id)
            resources = self.unit_resources[unit_id]

            # ENを回復（最大値を超えない）
            current_en = resources["current_en"]
            max_en = unit.max_en
            en_recovery = unit.en_recovery
            new_en = min(current_en + en_recovery, max_en)
            resources["current_en"] = new_en

            # 武器のクールダウンを減少
            for _, weapon_state in resources["weapon_states"].items():
                if weapon_state["current_cool_down"] > 0:
                    weapon_state["current_cool_down"] -= 1

    def _action_phase(self, actor: MobileSuit) -> None:
        """片方のユニットの行動処理."""
        # 既に撃墜されていたら何もしない
        if actor.current_hp <= 0:
            return

        # ファジィ推論で決定した行動を取得
        unit_id = str(actor.id)
        current_action = self.unit_resources[unit_id].get("current_action", "MOVE")

        # ターゲット選択
        target = self._select_target_fuzzy(actor)
        if not target:
            # 発見済みの敵がいない場合、最も近い未発見の敵の方向へ移動
            self._search_movement(actor)
            return

        pos_actor = actor.position.to_numpy()
        pos_target = target.position.to_numpy()
        diff_vector = pos_target - pos_actor
        distance = float(np.linalg.norm(diff_vector))

        weapon = actor.get_active_weapon()

        if current_action == "ATTACK":
            # 攻撃行動: 攻撃可能なら攻撃、そうでなければ移動
            if weapon and distance <= weapon.range:
                self._process_attack(actor, target, distance, pos_actor)
            else:
                self._process_movement(
                    actor, pos_actor, pos_target, diff_vector, distance
                )
        else:
            # MOVE 行動（RETREAT フォールバックを含む）: 移動のみ
            self._process_movement(actor, pos_actor, pos_target, diff_vector, distance)

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
        actor_name = self._format_actor_name(actor)
        label = _tactics_label.get(reason, reason)

        if reason == "CLOSEST":
            # details = "距離: XXXm"
            dist_str = details.replace("距離: ", "").strip()
            try:
                dist_val = float(dist_str.rstrip("m"))
                dist_label = self._get_distance_label(dist_val)
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

        self.logs.append(
            BattleLog(
                timestamp=self.elapsed_time,
                actor_id=actor.id,
                action_type="TARGET_SELECTION",
                target_id=target.id,
                message=message,
                position_snapshot=actor.position,
                fuzzy_scores=fuzzy_scores,
            )
        )

    def _detection_phase(self) -> None:
        """索敵フェーズ: 各ユニットが索敵範囲内の敵を発見."""
        alive_units = [u for u in self.units if u.current_hp > 0]

        # ミノフスキー粒子効果: 索敵範囲を半減
        sensor_multiplier = 1.0
        if "MINOVSKY" in self.special_effects:
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
                if target.id in self.team_detected_units[unit.team_id]:
                    # 既に発見済み
                    continue

                pos_target = target.position.to_numpy()
                distance = float(np.linalg.norm(pos_target - pos_unit))

                # 索敵判定（ミノフスキー粒子による索敵範囲低下を適用）
                if distance <= effective_sensor_range:
                    # 発見！
                    self.team_detected_units[unit.team_id].add(target.id)

                    # 発見ログを追加
                    dist_label = self._get_distance_label(distance)
                    actor_name = self._format_actor_name(unit)
                    if "MINOVSKY" in self.special_effects:
                        detect_message = (
                            f"{actor_name}が濃密なミノフスキー粒子の中、"
                            f"{dist_label}に{target.name}の反応を捉えた！"
                        )
                    else:
                        detect_message = (
                            f"{actor_name}が{dist_label}に{target.name}を発見！"
                        )
                    self.logs.append(
                        BattleLog(
                            timestamp=self.elapsed_time,
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
            u for u in self.units if u.current_hp > 0 and u.team_id != actor.team_id
        ]

        # 索敵済みの敵のみをターゲット候補とする
        if actor.team_id is None:
            return None
        detected_targets = [
            t
            for t in potential_targets
            if t.id in self.team_detected_units[actor.team_id]
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
            self._log_target_selection(
                actor, target, "WEAKEST", f"HP: {target.current_hp}"
            )
        elif tactics_priority == "STRONGEST":
            # 戦略価値が最も高い敵を選択
            target = max(
                detected_targets, key=lambda t: self._calculate_strategic_value(t)
            )
            strategic_value = self._calculate_strategic_value(target)
            self._log_target_selection(
                actor, target, "STRONGEST", f"戦略価値: {strategic_value:.1f}"
            )
        elif tactics_priority == "THREAT":
            # 脅威度が最も高い敵を選択
            target = max(
                detected_targets, key=lambda t: self._calculate_threat_level(actor, t)
            )
            threat_level = self._calculate_threat_level(actor, target)
            self._log_target_selection(
                actor, target, "THREAT", f"脅威度: {threat_level:.2f}"
            )
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
            self._log_target_selection(
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
            u for u in self.units if u.current_hp > 0 and u.team_id != actor.team_id
        ]

        # 索敵済みの敵のみをターゲット候補とする
        if actor.team_id is None:
            return None
        detected_targets = [
            t
            for t in potential_targets
            if t.id in self.team_detected_units[actor.team_id]
        ]

        # ターゲットが存在しない場合はNoneを返す
        if not detected_targets:
            return None

        pos_actor = actor.position.to_numpy()

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
                candidate_action = self.unit_resources.get(unit_id_candidate, {}).get(
                    "current_action", "MOVE"
                )
                is_attacking_ally = 1.0 if candidate_action == "ATTACK" else 0.0

                fuzzy_inputs = {
                    "target_hp_ratio": hp_ratio,
                    "target_distance": distance,
                    "target_attack_power": attack_power,
                    "is_attacking_ally": is_attacking_ally,
                }

                result, debug = self._target_selection_fuzzy_engine.infer_with_debug(
                    fuzzy_inputs
                )
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
                self._log_target_selection(
                    actor,
                    best_target,
                    "CLOSEST",
                    f"距離: {int(fallback_distance)}m",
                )
                return best_target

            # ループ完了後に全候補スコアを記録
            if best_fuzzy_scores is not None:
                best_fuzzy_scores["all_scores"] = all_scores

            self._log_target_selection(
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
            self._log_target_selection(
                actor, fallback, "CLOSEST", f"距離: {int(fallback_distance)}m"
            )
            return fallback

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

    def _check_attack_resources(
        self, weapon: Weapon, weapon_state: dict, resources: dict
    ) -> tuple[bool, str]:
        """攻撃に必要なリソースをチェックする.

        Returns:
            tuple[bool, str]: (攻撃可能か, 失敗理由)
        """
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
            accuracy_skill_level = self.player_skills.get("accuracy_up", 0)
            hit_chance += accuracy_skill_level * 2.0  # +2% / Lv

        # 敵への攻撃時は回避スキル補正を適用
        if target.side == "PLAYER":
            evasion_skill_level = self.player_skills.get("evasion_up", 0)
            hit_chance -= evasion_skill_level * 2.0  # 敵の命中率を -2% / Lv

        # 障害物効果: 命中率をペナルティ
        if "OBSTACLE" in self.special_effects:
            obstacle = SPECIAL_ENVIRONMENT_EFFECTS["OBSTACLE"]
            hit_chance -= obstacle["accuracy_penalty"]

        # パイロットステータス補正を適用
        attacker_dex = self.player_pilot_stats.dex if actor.side == "PLAYER" else 0
        defender_int = self.player_pilot_stats.intel if target.side == "PLAYER" else 0
        hit_chance = calculate_hit_chance(
            hit_chance,
            distance_from_optimal=distance_from_optimal,
            decay_rate=weapon.decay_rate,
            attacker_dex=attacker_dex,
            defender_int=defender_int,
        )

        return hit_chance, distance_from_optimal

    def _consume_attack_resources(
        self, weapon: Weapon, weapon_state: dict, resources: dict
    ) -> None:
        """攻撃実行時のリソースを消費する."""
        # 弾数を消費
        if weapon.max_ammo is not None and weapon.max_ammo > 0:
            if weapon_state["current_ammo"] is not None:
                weapon_state["current_ammo"] -= 1

        # ENを消費
        if weapon.en_cost > 0:
            resources["current_en"] -= weapon.en_cost

        # クールダウンを設定
        if weapon.cool_down_turn > 0:
            weapon_state["current_cool_down"] = weapon.cool_down_turn

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
        unit_id = str(actor.id)
        resources = self.unit_resources[unit_id]

        # リソース状態を取得または初期化
        weapon_state = self._get_or_init_weapon_state(weapon, resources)

        # リソースチェック
        can_attack, failure_reason = self._check_attack_resources(
            weapon, weapon_state, resources
        )

        if not can_attack:
            actor_name = self._format_actor_name(actor)
            weapon_display = f"[{weapon.name}]" if weapon.name else "[格闘]"
            if "弾切れ" in failure_reason:
                wait_message = (
                    f"{actor_name}は{weapon_display}の弾薬が尽き、攻撃手段がない"
                )
            elif "EN不足" in failure_reason:
                wait_message = (
                    f"{actor_name}はENが枯渇し、{weapon_display}を使えず待機中"
                )
            elif "クールダウン" in failure_reason:
                # failure_reason 例: "クールダウン中 (残りNターン)"
                remaining_turns = weapon_state.get("current_cool_down", 0)
                wait_message = f"{actor_name}は{weapon_display}の冷却を待ちながら（残り{remaining_turns}ターン）、やむなく待機"
            else:
                wait_message = (
                    f"{actor_name}は{failure_reason}のため攻撃できない（待機）"
                )
            self.logs.append(
                BattleLog(
                    timestamp=self.elapsed_time,
                    actor_id=actor.id,
                    action_type="WAIT",
                    message=wait_message,
                    position_snapshot=snapshot,
                )
            )
            return

        # 命中率計算
        hit_chance, distance_from_optimal = self._calculate_hit_chance(
            actor, target, weapon, distance
        )

        # スキルボーナスを個別に計算（スキル発動判定のため）
        skill_bonus = 0.0
        if actor.side == "PLAYER":
            accuracy_skill_level = self.player_skills.get("accuracy_up", 0)
            skill_bonus += accuracy_skill_level * 2.0
        if target.side == "PLAYER":
            evasion_skill_level = self.player_skills.get("evasion_up", 0)
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

        actor_name = self._format_actor_name(actor)
        weapon_display = f"[{weapon.name}]" if weapon.name else "[格闘]"
        log_base = f"{actor_name}が{weapon_display}で攻撃！ (命中: {int(hit_chance)}%)"

        # リソース消費
        self._consume_attack_resources(weapon, weapon_state, resources)

        # 攻撃時のセリフ生成
        attack_chatter = self._generate_chatter(actor, "attack")

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
        attacker_tou = self.player_pilot_stats.tou if actor.side == "PLAYER" else 0
        attacker_luk = self.player_pilot_stats.luk if actor.side == "PLAYER" else 0
        defender_dex = self.player_pilot_stats.dex if target.side == "PLAYER" else 0
        defender_tou = self.player_pilot_stats.tou if target.side == "PLAYER" else 0
        defender_luk = self.player_pilot_stats.luk if target.side == "PLAYER" else 0

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
            hit_chatter = self._generate_chatter(target, "hit")
            self.logs.append(
                BattleLog(
                    timestamp=self.elapsed_time,
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
        hit_chatter = self._generate_chatter(target, "hit")

        # 命中状況テキスト
        is_crit = "クリティカルヒット" in log_msg
        if is_crit:
            hit_text = " -> ★★ クリティカルヒット！！"
        elif is_optimal_distance:
            hit_text = " -> 最適射程でクリーンヒット！"
        else:
            hit_text = " -> 命中！"

        # ダメージ表現（HP割合ベース）
        damage_desc = self._get_damage_description(final_damage, target)
        # HP残量コメント
        hp_comment = self._get_hp_status_comment(target)

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

        self.logs.append(
            BattleLog(
                timestamp=self.elapsed_time,
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
            crit_skill_level = self.player_skills.get("crit_rate_up", 0)
            base_crit_rate += (crit_skill_level * 1.0) / 100.0  # +1% / Lv

        attacker_int = self.player_pilot_stats.intel if actor.side == "PLAYER" else 0
        defender_tou_crit = (
            self.player_pilot_stats.tou if target.side == "PLAYER" else 0
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
        """命中ダメージへスキル・適性・耐性補正を適用する."""
        if actor.side == "PLAYER":
            damage_skill_level = self.player_skills.get("damage_up", 0)
            damage_multiplier = 1.0 + (damage_skill_level * 3.0) / 100.0  # +3% / Lv
            base_damage = int(base_damage * damage_multiplier)

        is_melee = getattr(weapon, "is_melee", False)
        aptitude = (
            getattr(actor, "melee_aptitude", 1.0)
            if is_melee
            else getattr(actor, "shooting_aptitude", 1.0)
        )
        base_damage = int(base_damage * aptitude)

        weapon_type = getattr(weapon, "type", "PHYSICAL")
        resistance_msg = ""
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
        miss_chatter = self._generate_chatter(actor, "miss")

        if is_bad_distance:
            miss_text = f" -> 距離が合わず、{target.name}に回避された！"
        else:
            miss_text = f" -> {target.name}に回避された！"

        self.logs.append(
            BattleLog(
                timestamp=self.elapsed_time,
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

        # 撃破時のセリフ生成
        destroyed_chatter = self._generate_chatter(target, "destroyed")

        # エース撃破時の特別メッセージ
        ace_msg = ""
        if getattr(target, "is_ace", False):
            ace_msg = (
                f" ★【エース撃破】{getattr(target, 'pilot_name', 'Unknown')}を撃破！"
            )

        self.logs.append(
            BattleLog(
                timestamp=self.elapsed_time,
                actor_id=target.id,
                action_type="DESTROYED",
                message=f"{self._format_actor_name(target)} は爆散した...{ace_msg}",
                position_snapshot=target.position,
                chatter=destroyed_chatter,
            )
        )
        # 勝利判定 (生存ユニットのteam_idの種類が1つ以下なら戦闘終了)
        alive_teams = {u.team_id for u in self.units if u.current_hp > 0}
        if len(alive_teams) <= 1:
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
                    timestamp=self.elapsed_time,
                    actor_id=actor.id,
                    action_type="MOVE",
                    message=f"{self._format_actor_name(actor)}が後退中 (距離: {int(distance)}m)",
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
                        timestamp=self.elapsed_time,
                        actor_id=actor.id,
                        action_type="MOVE",
                        message=f"{self._format_actor_name(actor)}が距離を取る (距離: {int(distance)}m)",
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
                        timestamp=self.elapsed_time,
                        actor_id=actor.id,
                        action_type="MOVE",
                        message=f"{self._format_actor_name(actor)}が射程内に移動中 (残距離: {int(distance)}m)",
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
                    timestamp=self.elapsed_time,
                    actor_id=actor.id,
                    action_type="MOVE",
                    message=f"{self._format_actor_name(actor)}が接近中 (残距離: {int(distance)}m)",
                    position_snapshot=actor.position,
                )
            )

    def _get_terrain_modifier(self, unit: MobileSuit) -> float:
        """地形適正による補正係数を取得."""
        # 地形適正を取得
        terrain_adaptability = getattr(unit, "terrain_adaptability", {})
        adaptability_grade = terrain_adaptability.get(self.environment, "A")

        # 補正係数を返す
        modifier = TERRAIN_ADAPTABILITY_MODIFIERS.get(adaptability_grade, 1.0)

        # 重力井戸効果: 機動性をさらに低下
        if "GRAVITY_WELL" in self.special_effects:
            gravity = SPECIAL_ENVIRONMENT_EFFECTS["GRAVITY_WELL"]
            modifier *= gravity["mobility_multiplier"]

        return modifier

    def _search_movement(self, actor: MobileSuit) -> None:
        """索敵移動: 未発見の敵を探すための移動."""
        # 敵対勢力を特定 (team_idが異なるユニットが敵)
        potential_targets = [
            u for u in self.units if u.current_hp > 0 and u.team_id != actor.team_id
        ]

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
                timestamp=self.elapsed_time,
                actor_id=actor.id,
                action_type="MOVE",
                message=f"{self._format_actor_name(actor)}が索敵中 (残距離: {int(distance)}m)",
                position_snapshot=actor.position,
            )
        )

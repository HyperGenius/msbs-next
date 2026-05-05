# backend/app/engine/simulation.py
import logging
import math
import random
import uuid

import numpy as np

from app.core.npc_data import BATTLE_CHATTER
from app.engine.calculator import (
    PilotStats,
    calculate_critical_chance,
    calculate_damage_variance,
    calculate_hit_chance,
)
from app.engine.constants import (
    ALLY_REPULSION_RADIUS,
    BOUNDARY_MARGIN,
    CLOSE_RANGE,
    COMBO_BASE_CHANCE,
    COMBO_CHAIN_DECAY,
    COMBO_DAMAGE_MULTIPLIER,
    COMBO_MAX_CHAIN,
    DEFAULT_BOOST_COOLDOWN,
    DEFAULT_BOOST_EN_COST,
    DEFAULT_BOOST_MAX_DURATION,
    DEFAULT_BOOST_SPEED_MULTIPLIER,
    FUZZY_RULES_DIR,
    HIGH_THREAT_THRESHOLD,
    MAP_BOUNDS,
    MELEE_BOOST_ARRIVAL_RANGE,
    MELEE_CLOSE_ACCURACY_BONUS,
    MELEE_MID_ACCURACY_BONUS,
    MELEE_RANGE,
    OBSTACLE_MARGIN,
    OBSTACLE_REPULSION_COEFF,
    POST_MELEE_DISTANCE,
    RANGED_CLOSE_ACCURACY_PENALTY,
    RANGED_MID_ACCURACY_PENALTY,
    RETREAT_ATTRACTION_COEFF,
    SPECIAL_ENVIRONMENT_EFFECTS,
    STRATEGY_UPDATE_INTERVAL,
    TERRAIN_ADAPTABILITY_MODIFIERS,
    VALID_STRATEGY_MODES,
)
from app.engine.fuzzy_engine import FuzzyEngine
from app.engine.fuzzy_rule_cache import FuzzyRuleCache
from app.engine.strategy_controller import TeamMetrics, TeamStrategyController
from app.models.models import (
    BattleLog,
    MobileSuit,
    Obstacle,
    RetreatPoint,
    Vector3,
    Weapon,
)

logger = logging.getLogger(__name__)

_MAX_STEPS = 5000
# 近隣ユニット検索半径 (m)
_FUZZY_NEIGHBOR_RADIUS = 500.0
# ターゲット選択ファジィ推論: 距離の最大値 (m)
_TARGET_SELECTION_MAX_DIST = 3000.0
# 武器選択ファジィ推論: 距離の最大値 (m)
_WEAPON_SELECTION_MAX_DIST = 3000.0
# MOVE ログを出力する最小残距離 (m) — これ未満の残距離では MOVE ログを抑制する
MOVE_LOG_MIN_DIST: float = 100.0
# チームレベルイベントのダミー actor_id (Phase 4-2)
_TEAM_EVENT_ACTOR_ID: uuid.UUID = uuid.UUID(int=0)


def _has_los(
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
        retreat_points: list[RetreatPoint] | None = None,
        strategy_update_interval: int = STRATEGY_UPDATE_INTERVAL,
        enable_hot_reload: bool = False,
        obstacles: list[Obstacle] | None = None,
    ):
        """初期化.

        Args:
            player: プレイヤー機体
            enemies: 敵機体リスト
            player_skills: プレイヤーのスキル (skill_id: level)
            environment: 戦闘環境 (SPACE/GROUND/COLONY/UNDERWATER)
            special_effects: 特殊環境効果リスト (MINOVSKY/GRAVITY_WELL/OBSTACLE)
            player_pilot_stats: プレイヤーのパイロットステータス (DEX/INT/REF/TOU/LUK)
            retreat_points: 撤退ポイントのリスト (Phase 3-3)
            strategy_update_interval: 何ステップごとに戦略評価を行うか (Phase 4-2)
            enable_hot_reload: True の場合、シミュレーション実行ごとにファジィルール JSON
                の変更を自動検出して再ロードする（ローカル開発用）。False の場合は
                起動時に一度だけロードしてスナップショットとして保持する（デフォルト）。
            obstacles: フィールド上の障害物リスト (Phase A — LOS システム)

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
        self.retreat_points: list[RetreatPoint] = retreat_points or []
        self.obstacles: list[Obstacle] = obstacles or []

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
                "velocity_vec": np.zeros(3),  # 現在の速度ベクトル (3D, m/s)
                "heading_deg": 0.0,  # 現在の向き (XZ平面, 度)
                "status": "ACTIVE",  # ユニット状態: ACTIVE / RETREATED / DESTROYED (Phase 3-3)
                "last_known_enemy_position": {},  # {enemy_id: [x, y, z]} LOS 喪失時の最終座標 (Phase A)
                "is_boosting": False,  # ブースト中フラグ (Phase B)
                "boost_elapsed": 0.0,  # 現ブーストの継続時間 (s) (Phase B)
                "boost_cooldown_remaining": 0.0,  # 残クールダウン時間 (s) (Phase B)
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
            FUZZY_RULES_DIR / "aggressive.json", default_output={"action": 0.0}
        )
        # 低階層ファジィ推論エンジン: ターゲット選択（AGGRESSIVEルールセット）
        self._target_selection_fuzzy_engine: FuzzyEngine = FuzzyEngine.from_json(
            FUZZY_RULES_DIR / "aggressive_target_selection.json",
            default_output={"target_priority": 0.0},
        )
        # 低階層ファジィ推論エンジン: 武器選択（AGGRESSIVEルールセット）
        self._weapon_selection_fuzzy_engine: FuzzyEngine = FuzzyEngine.from_json(
            FUZZY_RULES_DIR / "aggressive_weapon_selection.json",
            default_output={"weapon_score": 0.0},
        )

        # ホットリロード設定 (Phase 5-2)
        self._enable_hot_reload: bool = enable_hot_reload
        self._rule_cache: FuzzyRuleCache = FuzzyRuleCache(FUZZY_RULES_DIR)
        # ホットリロード無効時はスナップショットとしてキャッシュから一度だけ取得
        self._cached_engines: dict[str, dict[str, FuzzyEngine]] = (
            self._rule_cache.get_engines()
        )

        # チームレベル戦略コントローラ (Phase 4-2)
        team_ids = {unit.team_id for unit in self.units if unit.team_id is not None}
        self._strategy_controllers: dict[str, TeamStrategyController] = {
            team_id: TeamStrategyController(
                team_id=team_id,
                initial_strategy="AGGRESSIVE",
                update_interval=strategy_update_interval,
            )
            for team_id in team_ids
        }

    @property
    def _strategy_engines(self) -> dict[str, dict[str, FuzzyEngine]]:
        """戦略モード別ファジィ推論エンジン辞書を返す.

        ホットリロードが有効な場合はキャッシュから変更検出付きで取得し、
        無効な場合は起動時に一度だけロードしたスナップショットを返す。

        Returns:
            {"MODE": {"behavior": FuzzyEngine, "target": FuzzyEngine, "weapon": FuzzyEngine}}
        """
        if self._enable_hot_reload:
            return self._rule_cache.get_engines()
        return self._cached_engines

    def _resolve_strategy_mode(self, unit: MobileSuit) -> str:
        """ユニットの戦略モードを解決する.

        unit.strategy_mode が有効な値でない場合は AGGRESSIVE にフォールバックし、
        ログに警告を出力する。ロードされたエンジンが存在しないモードも AGGRESSIVE へ
        フォールバックする。

        Args:
            unit: 対象ユニット

        Returns:
            使用する戦略モード名（常にロード済みエンジンが存在するモード）
        """
        raw = getattr(unit, "strategy_mode", None)
        if raw is None:
            return "AGGRESSIVE"

        mode = str(raw).upper()
        if mode not in VALID_STRATEGY_MODES:
            logger.warning(
                "ユニット %s の strategy_mode '%s' は無効な値です。AGGRESSIVE にフォールバックします。",
                unit.id,
                raw,
            )
            return "AGGRESSIVE"

        if mode not in self._strategy_engines:
            logger.warning(
                "戦略モード '%s' のエンジンが未ロードです。AGGRESSIVE にフォールバックします。",
                mode,
            )
            return "AGGRESSIVE"

        return mode

    def _get_units_in_weapon_range(
        self,
        unit: MobileSuit,
        all_units: list[MobileSuit],
        weapon_max_range: float,
    ) -> list[MobileSuit]:
        """射撃武器の最大射程内にいるユニットを返す（LOS チェックのパフォーマンス最適化用）.

        Args:
            unit: 基準となるユニット
            all_units: チェック対象の全ユニットリスト
            weapon_max_range: 武器の最大射程 (m)

        Returns:
            射程内にいるユニットのリスト
        """
        pos_unit = unit.position.to_numpy()
        result = []
        for target in all_units:
            if target.id == unit.id:
                continue
            dist = float(np.linalg.norm(target.position.to_numpy() - pos_unit))
            if dist <= weapon_max_range:
                result.append(target)
        return result

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

        # 2. 戦略評価フェーズ (Phase 4-2)
        self._strategy_phase()

        # 3. AI意思決定フェーズ（中階層ファジィ推論）
        alive_units = [u for u in self.units if u.current_hp > 0]
        for unit in alive_units:
            self._ai_decision_phase(unit)

        # 4. 行動フェーズ（全ユニットを同一ステップで並列処理）
        alive_units = [u for u in self.units if u.current_hp > 0]
        for unit in alive_units:
            if self.is_finished:
                break
            self._action_phase(unit, dt)

        # 5. 撤退離脱判定フェーズ (Phase 3-3)
        if self.retreat_points:
            self._retreat_check_phase()

        # 6. リソース更新フェーズ（EN回復・クールダウン減少）
        self._refresh_phase(dt)

        # 7. 時間を進める
        self.elapsed_time += dt
        self._step_count += 1

    def _collect_team_metrics(self, team_id: str) -> TeamMetrics:
        """チームのバトルメトリクスを収集する (Phase 4-2).

        ACTIVE ステータスのユニットのみを対象に HP 割合を計算する。

        Args:
            team_id: 対象チームID

        Returns:
            TeamMetrics: チームの現在のメトリクス
        """
        controller = self._strategy_controllers.get(team_id)
        current_strategy = controller.current_strategy if controller else "AGGRESSIVE"

        team_units = [u for u in self.units if u.team_id == team_id]
        total_count = len(team_units)

        active_units = [
            u
            for u in team_units
            if self.unit_resources[str(u.id)].get("status") == "ACTIVE"
            and u.current_hp > 0
        ]
        alive_count = len(active_units)

        alive_ratio = alive_count / total_count if total_count > 0 else 0.0

        if active_units:
            hp_ratios = [
                float(u.current_hp) / float(max(1, u.max_hp)) for u in active_units
            ]
            avg_hp_ratio = float(sum(hp_ratios) / len(hp_ratios))
            min_hp_ratio = float(min(hp_ratios))
        else:
            avg_hp_ratio = 0.0
            min_hp_ratio = 0.0

        return TeamMetrics(
            team_id=team_id,
            alive_count=alive_count,
            total_count=total_count,
            alive_ratio=float(alive_ratio),
            avg_hp_ratio=avg_hp_ratio,
            min_hp_ratio=min_hp_ratio,
            current_strategy=current_strategy,
            elapsed_time=float(self.elapsed_time),
            retreat_points_empty=len(self.retreat_points) == 0,
        )

    def _strategy_phase(self) -> None:
        """戦略評価フェーズ: チームレベルの戦略モードを評価・更新する (Phase 4-2 / 4-3).

        STRATEGY_UPDATE_INTERVAL ステップごとに各チームの TeamStrategyController を
        呼び出してメトリクスを評価し、戦略変更が発生した場合はユニットの strategy_mode
        を一括更新して STRATEGY_CHANGED ログを記録する。
        撤退ポイント未設定時に RETREAT → DEFENSIVE フォールバックを適用する (T10)。
        """
        # 全チームのメトリクスを収集
        team_ids = list(self._strategy_controllers.keys())
        team_metrics_map: dict[str, TeamMetrics] = {
            team_id: self._collect_team_metrics(team_id) for team_id in team_ids
        }

        for team_id, controller in self._strategy_controllers.items():
            if not controller.should_evaluate():
                continue

            metrics = team_metrics_map[team_id]
            previous_strategy = controller.current_strategy
            new_strategy = controller.evaluate(metrics)
            matched_rule_id = controller._last_matched_rule_id

            # T10 フォールバック: RETREAT への遷移かつ撤退ポイント未設定 → DEFENSIVE に切替
            if new_strategy == "RETREAT" and len(self.retreat_points) == 0:
                new_strategy = "DEFENSIVE"
                matched_rule_id = "T10"

            if new_strategy is None or new_strategy == previous_strategy:
                continue

            # ACTIVE ユニットの strategy_mode を一括更新
            team_unit_resources = [
                (u, self.unit_resources[str(u.id)])
                for u in self.units
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

            self.logs.append(
                BattleLog(
                    timestamp=float(self.elapsed_time),
                    actor_id=_TEAM_EVENT_ACTOR_ID,
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
        if self.unit_resources[unit_id].get("status") == "RETREATED":
            return

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

        # --- 新規入力変数 (Phase C) ---
        # ranged_ammo_ratio: 遠距離武器の残弾割合（全遠距離武器の平均）
        ranged_weapons = [
            w for w in unit.weapons
            if getattr(w, "weapon_type", "RANGED") != "MELEE"
            and not getattr(w, "is_melee", False)
        ]
        if ranged_weapons:
            ammo_ratios = []
            for rw in ranged_weapons:
                ws = self.unit_resources[unit_id]["weapon_states"].get(rw.id, {})
                if rw.max_ammo is not None and rw.max_ammo > 0:
                    current_ammo = ws.get("current_ammo", rw.max_ammo) or 0
                    ammo_ratios.append(float(current_ammo) / float(rw.max_ammo))
                else:
                    ammo_ratios.append(1.0)
            ranged_ammo_ratio = sum(ammo_ratios) / len(ammo_ratios)
        else:
            ranged_ammo_ratio = 1.0
        fuzzy_inputs["ranged_ammo_ratio"] = ranged_ammo_ratio

        # los_blocked: ターゲットへの LOS 状態（Phase A の結果を使用）
        nearest_enemy = min(
            detected_enemies,
            key=lambda e: float(np.linalg.norm(e.position.to_numpy() - pos_unit)),
        )
        if self.obstacles:
            pos_nearest = nearest_enemy.position.to_numpy()
            los_ok = _has_los(pos_unit, pos_nearest, self.obstacles)
            los_blocked = 0.0 if los_ok else 1.0
        else:
            los_blocked = 0.0
        fuzzy_inputs["los_blocked"] = los_blocked

        # boost_available: ブースト可否（クールダウン中か否か、EN残量チェック）
        boost_cooldown_remaining = self.unit_resources[unit_id].get(
            "boost_cooldown_remaining", 0.0
        )
        current_en = self.unit_resources[unit_id].get("current_en", 0.0)
        boost_en_cost = getattr(unit, "boost_en_cost", DEFAULT_BOOST_EN_COST)
        boost_available = (
            1.0
            if boost_cooldown_remaining == 0.0 and current_en > boost_en_cost
            else 0.0
        )
        fuzzy_inputs["boost_available"] = boost_available

        # --- 戦略モードに応じたファジィエンジンを選択 ---
        strategy_mode = self._resolve_strategy_mode(unit)
        behavior_engine = self._strategy_engines.get(strategy_mode, {}).get(
            "behavior", self._fuzzy_engine
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

        # RETREAT が出力されたが撤退ポイントが未設定の場合は MOVE にフォールバック
        if action == "RETREAT" and not self.retreat_points:
            action = "MOVE"

        # BOOST_DASH がクールダウン中の場合は MOVE にフォールバック (Phase B)
        if action == "BOOST_DASH":
            cooldown_remaining = self.unit_resources[unit_id].get(
                "boost_cooldown_remaining", 0.0
            )
            if cooldown_remaining > 0.0:
                action = "MOVE"

        # ENGAGE_MELEE は RETREAT モード中は選択されない (Phase C)
        if action == "ENGAGE_MELEE":
            if strategy_mode == "RETREAT":
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
                    f" 近味:{ally_count_near:.0f} 近距:{distance_to_nearest_enemy:.0f}m"
                    f" 弾薬率:{ranged_ammo_ratio:.2f} LOS閉塞:{los_blocked:.0f}"
                    f" ブースト可:{boost_available:.0f})"
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
            for u in self.units
            if u.current_hp > 0
            and self.unit_resources[str(u.id)]["status"] == "ACTIVE"
            and self.unit_resources[str(u.id)].get("current_action") == "RETREAT"
        ]

        for unit in retreating_units:
            unit_id = str(unit.id)
            pos_unit = unit.position.to_numpy()

            # 対象ユニットに適用可能な撤退ポイントを抽出
            applicable_rps = [
                rp
                for rp in self.retreat_points
                if rp.team_id is None or rp.team_id == unit.team_id
            ]

            for rp in applicable_rps:
                rp_pos = rp.position.to_numpy()
                dist = float(np.linalg.norm(rp_pos - pos_unit))
                if dist <= rp.radius:
                    # 撤退完了
                    self.unit_resources[unit_id]["status"] = "RETREATED"
                    self.logs.append(
                        BattleLog(
                            timestamp=self.elapsed_time,
                            actor_id=unit.id,
                            action_type="RETREAT_COMPLETE",
                            message=(
                                f"{self._format_actor_name(unit)} が撤退ポイントに到達し、"
                                f"戦線から離脱した。"
                            ),
                            position_snapshot=unit.position,
                        )
                    )
                    break

        # 勝利判定: ACTIVE な生存ユニットのチームが 1 つ以下なら戦闘終了
        active_teams = {
            u.team_id
            for u in self.units
            if u.current_hp > 0 and self.unit_resources[str(u.id)]["status"] == "ACTIVE"
        }
        if len(active_teams) <= 1:
            self.is_finished = True

    def _refresh_phase(self, dt: float = 0.1) -> None:
        """リフレッシュフェーズ: ENの回復とクールダウンの減少."""
        for unit in self.units:
            if unit.current_hp <= 0:
                continue

            unit_id = str(unit.id)
            resources = self.unit_resources[unit_id]

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

    def _action_phase(self, actor: MobileSuit, dt: float = 0.1) -> None:
        """片方のユニットの行動処理."""
        # 既に撃墜されていたら何もしない
        if actor.current_hp <= 0:
            return

        # 撤退完了済みのユニットは行動しない
        unit_id = str(actor.id)
        if self.unit_resources[unit_id].get("status") == "RETREATED":
            return

        # ファジィ推論で決定した行動を取得
        current_action = self.unit_resources[unit_id].get("current_action", "MOVE")

        # ターゲット選択
        target = self._select_target_fuzzy(actor)
        if not target:
            # 発見済みの敵がいない場合、最も近い未発見の敵の方向へ移動
            self._search_movement(actor, dt)
            return

        pos_actor = actor.position.to_numpy()
        pos_target = target.position.to_numpy()
        diff_vector = pos_target - pos_actor
        distance = float(np.linalg.norm(diff_vector))

        weapon = self._select_weapon_fuzzy(actor, target)
        if weapon is None:
            weapon = actor.get_active_weapon()

        if current_action == "ATTACK":
            # 攻撃行動: 攻撃可能なら攻撃、そうでなければ移動
            if weapon and distance <= weapon.range:
                self._process_attack(actor, target, distance, pos_actor, weapon)
            else:
                self._process_movement(
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
            self._process_movement(
                actor, pos_actor, pos_target, diff_vector, distance, dt
            )

    def _handle_boost_dash_action(
        self,
        actor: MobileSuit,
        target: MobileSuit,
        weapon: object,
        pos_actor: object,
        pos_target: object,
        diff_vector: object,
        distance: float,
        dt: float,
    ) -> None:
        """ブーストダッシュ行動処理 (Phase B)."""
        unit_id = str(actor.id)
        resources = self.unit_resources[unit_id]
        is_boosting = resources.get("is_boosting", False)
        cooldown_remaining = resources.get("boost_cooldown_remaining", 0.0)

        if not is_boosting and cooldown_remaining <= 0.0:
            # ブースト開始
            resources["is_boosting"] = True
            resources["boost_elapsed"] = 0.0
            self.logs.append(
                BattleLog(
                    timestamp=float(self.elapsed_time),
                    actor_id=actor.id,
                    action_type="BOOST_START",
                    message=(
                        f"{self._format_actor_name(actor)} がブーストダッシュを開始した！"
                    ),
                    position_snapshot=actor.position,
                )
            )

        # ブーストキャンセル判定
        cancelled = self._check_boost_cancel(actor, target, dt)

        if cancelled:
            # キャンセル後は遠距離攻撃試行
            if weapon and isinstance(weapon, Weapon) and distance <= weapon.range:
                self._process_attack(actor, target, distance, pos_actor, weapon)
            else:
                self._process_movement(
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
            self._process_movement(
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
                self._process_attack(actor, target, distance, pos_actor, weapon)
            else:
                self._process_movement(
                    actor, pos_actor, pos_target, diff_vector, distance, dt, target=target
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
        self._process_attack(actor, target, distance, pos_actor, weapon)

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
            self.unit_resources[unit_id]["velocity_vec"] = np.zeros(3)

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
                unit_id = str(unit.id)
                pos_target = target.position.to_numpy()
                distance = float(np.linalg.norm(pos_target - pos_unit))

                if target.id in self.team_detected_units[unit.team_id]:
                    # 既に発見済み — LOS が失われていないか再チェック（障害物がある場合）
                    if self.obstacles and not _has_los(
                        pos_unit, pos_target, self.obstacles
                    ):
                        # LOS 喪失: 発見済みリストから除外し最終座標を記憶
                        self.team_detected_units[unit.team_id].discard(target.id)
                        self.unit_resources[unit_id]["last_known_enemy_position"][
                            str(target.id)
                        ] = pos_target.tolist()
                    continue

                # 索敵判定（ミノフスキー粒子による索敵範囲低下を適用）
                if distance <= effective_sensor_range:
                    # LOS チェック（障害物がある場合のみ）
                    if self.obstacles and not _has_los(
                        pos_unit, pos_target, self.obstacles
                    ):
                        # 障害物により遮断されているため発見不可
                        continue

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

        # 戦略モードに応じたターゲット選択エンジンを選択
        strategy_mode = self._resolve_strategy_mode(actor)
        target_engine = self._strategy_engines.get(strategy_mode, {}).get(
            "target", self._target_selection_fuzzy_engine
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

    def _is_weapon_usable(self, actor: MobileSuit, weapon: Weapon) -> bool:
        """武器が現在使用可能か判定する（クールダウン・EN・弾薬をチェック）.

        Args:
            actor: 使用するユニット
            weapon: チェック対象の武器

        Returns:
            True if the weapon can be used, False otherwise.
        """
        unit_id = str(actor.id)
        resources = self.unit_resources[unit_id]
        weapon_state = self._get_or_init_weapon_state(weapon, resources)
        can_use, _ = self._check_attack_resources(weapon, weapon_state, resources)
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
        resources = self.unit_resources[unit_id]

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
        strategy_mode = self._resolve_strategy_mode(actor)
        weapon_engine = self._strategy_engines.get(strategy_mode, {}).get(
            "weapon", self._weapon_selection_fuzzy_engine
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
        is_melee_weapon = getattr(weapon, "weapon_type", "RANGED") == "MELEE" or getattr(
            weapon, "is_melee", False
        )

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
        is_melee_weapon = getattr(weapon, "weapon_type", "RANGED") == "MELEE" or getattr(
            weapon, "is_melee", False
        )

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
        actor_name = self._format_actor_name(actor)
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
        self.logs.append(
            BattleLog(
                timestamp=self.elapsed_time,
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
        resources = self.unit_resources[unit_id]

        # LOS チェック（格闘武器はスキップ、障害物がある場合のみ）
        is_melee = getattr(weapon, "is_melee", False)
        if not is_melee and self.obstacles:
            pos_target = target.position.to_numpy()
            if not _has_los(pos_actor, pos_target, self.obstacles):
                actor_name = self._format_actor_name(actor)
                weapon_display = f"[{weapon.name}]" if weapon.name else "[武装]"
                self.logs.append(
                    BattleLog(
                        timestamp=self.elapsed_time,
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
            return

        # 格闘コンボシステム (Phase C — MELEE 武器のみ適用)
        is_melee_weapon = (
            getattr(weapon, "weapon_type", "RANGED") == "MELEE"
            or getattr(weapon, "is_melee", False)
        )
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
            self.logs.append(
                BattleLog(
                    timestamp=self.elapsed_time,
                    actor_id=actor.id,
                    action_type="MELEE_COMBO",
                    target_id=target.id,
                    damage=combo_total_damage,
                    target_max_hp=target.max_hp,
                    message=(
                        f"{self._format_actor_name(actor)} の格闘コンボ！"
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
        """命中ダメージへスキル・適性・耐性補正を適用する.

        MELEE 武器は耐性計算をバイパスする（属性なし物理として扱う）(Phase C)。
        """
        if actor.side == "PLAYER":
            damage_skill_level = self.player_skills.get("damage_up", 0)
            damage_multiplier = 1.0 + (damage_skill_level * 3.0) / 100.0  # +3% / Lv
            base_damage = int(base_damage * damage_multiplier)

        is_melee = (
            getattr(weapon, "weapon_type", "RANGED") == "MELEE"
            or getattr(weapon, "is_melee", False)
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

        # ステータスを DESTROYED に更新 (Phase 3-3)
        target_id = str(target.id)
        self.unit_resources[target_id]["status"] = "DESTROYED"

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
        # 勝利判定 (ACTIVE な生存ユニットのteam_idの種類が1つ以下なら戦闘終了)
        active_teams = {
            u.team_id
            for u in self.units
            if u.current_hp > 0 and self.unit_resources[str(u.id)]["status"] == "ACTIVE"
        }
        if len(active_teams) <= 1:
            self.is_finished = True

    def _threat_enemy_repulsion(
        self,
        unit: MobileSuit,
        pos_unit: np.ndarray,
        weapon_range: float,
    ) -> np.ndarray:
        """高脅威敵（自機射程外）への斥力ベクトルを返す."""
        force = np.zeros(3)
        all_enemies = [
            u for u in self.units if u.current_hp > 0 and u.team_id != unit.team_id
        ]
        for enemy in all_enemies:
            vec_to_enemy = enemy.position.to_numpy() - pos_unit
            dist = float(np.linalg.norm(vec_to_enemy))
            threat_score = self._calculate_attack_power(enemy) / max(
                1.0, float(unit.max_hp)
            )
            if threat_score > HIGH_THREAT_THRESHOLD and dist > weapon_range:
                force += 1.5 * (-vec_to_enemy) / max(dist, 1.0)
        return force

    def _ally_repulsion(self, unit: MobileSuit, pos_unit: np.ndarray) -> np.ndarray:
        """味方ユニットへの弱い斥力ベクトルを返す（密集防止）."""
        force = np.zeros(3)
        allies = [
            u
            for u in self.units
            if u.current_hp > 0 and u.team_id == unit.team_id and u.id != unit.id
        ]
        for ally in allies:
            vec_to_ally = ally.position.to_numpy() - pos_unit
            dist = float(np.linalg.norm(vec_to_ally))
            if 0 < dist <= ALLY_REPULSION_RADIUS:
                force += 0.8 * (-vec_to_ally) / max(dist, 1.0)
        return force

    def _boundary_repulsion(self, pos_unit: np.ndarray) -> np.ndarray:
        """マップ境界への斥力ベクトルを返す."""
        force = np.zeros(3)
        map_min, map_max = MAP_BOUNDS
        axes = [(0, np.array([1.0, 0.0, 0.0])), (2, np.array([0.0, 0.0, 1.0]))]
        for axis, direction in axes:
            dist_min = pos_unit[axis] - map_min
            if dist_min < BOUNDARY_MARGIN:
                force += 3.0 * direction / max(dist_min, 1.0)
            dist_max = map_max - pos_unit[axis]
            if dist_max < BOUNDARY_MARGIN:
                force += 3.0 * (-direction) / max(dist_max, 1.0)
        return force

    def _attack_target_attraction(
        self, unit: MobileSuit, pos_unit: np.ndarray, target: MobileSuit | None = None
    ) -> np.ndarray:
        """攻撃ターゲットへの引力ベクトルを返す（ATTACK行動時）."""
        force = np.zeros(3)
        if target is not None:
            vec = target.position.to_numpy() - pos_unit
            dist = float(np.linalg.norm(vec))
            if dist > 0:
                force += 2.0 * vec / dist
        return force

    def _closest_enemy_attraction(
        self, unit: MobileSuit, pos_unit: np.ndarray
    ) -> np.ndarray:
        """最近敵への引力ベクトルを返す（MOVE行動時）."""
        force = np.zeros(3)
        enemies = [
            u for u in self.units if u.current_hp > 0 and u.team_id != unit.team_id
        ]
        if enemies:
            closest_enemy = min(
                enemies,
                key=lambda e: float(np.linalg.norm(e.position.to_numpy() - pos_unit)),
            )
            vec = closest_enemy.position.to_numpy() - pos_unit
            dist = float(np.linalg.norm(vec))
            if dist > 0:
                force += 1.5 * vec / dist
        return force

    def _retreat_points_attraction(
        self, pos_unit: np.ndarray, retreat_points: list[RetreatPoint]
    ) -> np.ndarray:
        """撤退ポイントへの強引力ベクトルを返す（RETREAT行動時）."""
        force = np.zeros(3)
        for rp in retreat_points:
            rp_pos = rp.position.to_numpy()
            vec = rp_pos - pos_unit
            dist = float(np.linalg.norm(vec))
            if dist > 0:
                force += RETREAT_ATTRACTION_COEFF * vec / dist
        return force

    def _calculate_potential_field(
        self,
        unit: MobileSuit,
        target: MobileSuit | None = None,
        retreat_points: list[RetreatPoint] | None = None,
    ) -> np.ndarray:
        """ポテンシャルフィールド法による目標方向ベクトルを計算する.

        攻撃ターゲット・脅威敵・味方・マップ境界などの各ソースからの
        引力・斥力を合成して正規化した 3D 単位ベクトルを返す。
        合算結果がゼロベクトルになった場合はランダム方向を返し
        ローカルミニマムを回避する。

        Args:
            unit: 移動するユニット
            target: 攻撃対象ユニット（ATTACK 行動時に強引力を与える）
            retreat_points: 撤退ポイントのリスト（Phase 3-3 用）

        Returns:
            3D 単位ベクトル（XZ 平面）
        """
        if retreat_points is None:
            retreat_points = []

        pos_unit = unit.position.to_numpy()
        unit_id = str(unit.id)
        current_action = self.unit_resources[unit_id].get("current_action", "MOVE")
        total_force = np.zeros(3)

        # 1. 攻撃ターゲットへの引力 (ATTACK 行動かつターゲット選択済みの場合)
        if current_action == "ATTACK":
            total_force += self._attack_target_attraction(unit, pos_unit, target)

        # 2. MOVE 行動時の最近敵への引力（RETREAT 時は撤退ポイントへ向かうため除外）
        if current_action == "MOVE":
            total_force += self._closest_enemy_attraction(unit, pos_unit)

        # 3. 高脅威敵（自機射程外）への斥力
        weapon = unit.get_active_weapon()
        weapon_range = float(weapon.range) if weapon else 0.0
        total_force += self._threat_enemy_repulsion(unit, pos_unit, weapon_range)

        # 4. 味方ユニットへの弱い斥力 (ALLY_REPULSION_RADIUS 以内)
        total_force += self._ally_repulsion(unit, pos_unit)

        # 5. マップ境界への斥力 (BOUNDARY_MARGIN 以内)
        total_force += self._boundary_repulsion(pos_unit)

        # 6. 撤退ポイントへの強引力 (RETREAT 行動時のみ、Phase 3-3)
        if current_action == "RETREAT":
            applicable_rps = [
                rp
                for rp in retreat_points
                if rp.team_id is None or rp.team_id == unit.team_id
            ]
            total_force += self._retreat_points_attraction(pos_unit, applicable_rps)

        # 7. 障害物への斥力 (Phase A — LOS システム)
        for obs in self.obstacles:
            obs_pos = np.array([obs.position.x, obs.position.y, obs.position.z])
            obs_dist = float(np.linalg.norm(pos_unit - obs_pos))
            if obs_dist <= obs.radius + OBSTACLE_MARGIN:
                away_vec = (pos_unit - obs_pos) / max(obs_dist, 1.0)
                total_force += OBSTACLE_REPULSION_COEFF * away_vec

        # 正規化 — ゼロベクトル時はランダム方向でローカルミニマムを回避
        total_force[1] = 0.0  # Y 成分を XZ 平面に固定
        magnitude = float(np.linalg.norm(total_force))
        if magnitude < 1e-6:
            angle = random.uniform(0.0, 2.0 * math.pi)
            return np.array([math.cos(angle), 0.0, math.sin(angle)])
        return total_force / magnitude

    def _process_movement(
        self,
        actor: MobileSuit,
        pos_actor: np.ndarray,
        pos_target: np.ndarray,
        diff_vector: np.ndarray,
        distance: float,
        dt: float = 0.1,
        target: MobileSuit | None = None,
    ) -> None:
        """移動処理を実行する（ポテンシャルフィールドによる自律移動）."""
        if distance == 0:
            return

        # ポテンシャルフィールドで目標方向を算出し、慣性モデルで位置・速度を更新
        desired_direction = self._calculate_potential_field(
            actor, target, self.retreat_points
        )
        self._apply_inertia(actor, desired_direction, dt)

        # MOVE_LOG_MIN_DIST 以上の残距離のステップのみログ出力（ログ量削減）
        if distance >= MOVE_LOG_MIN_DIST:
            self.logs.append(
                BattleLog(
                    timestamp=self.elapsed_time,
                    actor_id=actor.id,
                    action_type="MOVE",
                    message=f"{self._format_actor_name(actor)}が移動中 (残距離: {int(distance)}m)",
                    position_snapshot=actor.position,
                    velocity_snapshot=Vector3.from_numpy(
                        self.unit_resources[str(actor.id)]["velocity_vec"]
                    ),
                )
            )

    def _apply_inertia(
        self,
        actor: MobileSuit,
        desired_direction: np.ndarray,
        dt: float,
    ) -> None:
        """慣性モデルによる速度・位置更新.

        旋回制限・加速制限を適用したうえで速度ベクトルと位置を更新する。
        `unit_resources` の `velocity_vec` / `heading_deg` を更新し、
        `actor.position` を書き換える。

        Args:
            actor: 移動対象ユニット
            desired_direction: 目標方向の単位ベクトル (3D, XZ平面)
            dt: 時間ステップ幅 (s)
        """
        unit_id = str(actor.id)
        resources = self.unit_resources[unit_id]

        current_velocity: np.ndarray = resources["velocity_vec"]
        current_heading: float = resources["heading_deg"]

        # 目標方向のヘッディング角度を計算 (XZ 平面での atan2)
        desired_heading = math.degrees(
            math.atan2(float(desired_direction[2]), float(desired_direction[0]))
        )

        # 1. 旋回制限
        max_rotation = actor.max_turn_rate * dt
        angular_diff = ((desired_heading - current_heading + 180) % 360) - 180
        actual_rotation = max(-max_rotation, min(max_rotation, angular_diff))
        new_heading = current_heading + actual_rotation

        # 2. 加速・減速制限
        current_speed = float(np.linalg.norm(current_velocity))
        terrain_modifier = self._get_terrain_modifier(actor)

        # ブースト中は effective_max_speed を boost_speed_multiplier 倍にする (Phase B)
        boost_multiplier = getattr(
            actor, "boost_speed_multiplier", DEFAULT_BOOST_SPEED_MULTIPLIER
        )
        if resources.get("is_boosting", False):
            effective_max_speed = actor.max_speed * boost_multiplier * terrain_modifier
        else:
            effective_max_speed = actor.max_speed * terrain_modifier

        if current_speed < effective_max_speed:
            new_speed = min(
                current_speed + actor.acceleration * dt, effective_max_speed
            )
        else:
            new_speed = max(current_speed - actor.deceleration * dt, 0.0)

        # 新しい方向ベクトルと速度ベクトルを計算 (XZ 平面、Y=0)
        heading_rad = math.radians(new_heading)
        new_direction = np.array([math.cos(heading_rad), 0.0, math.sin(heading_rad)])
        new_velocity = new_direction * new_speed

        # 3. 位置更新
        pos_actor = actor.position.to_numpy()
        new_pos = pos_actor + new_velocity * dt

        # unit_resources を更新
        resources["velocity_vec"] = new_velocity
        resources["heading_deg"] = new_heading

        # 位置を更新
        actor.position = Vector3.from_numpy(new_pos)

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

    def _check_boost_cancel(
        self,
        actor: MobileSuit,
        target: MobileSuit | None,
        dt: float,
    ) -> bool:
        """ブーストキャンセル判定を実行し、キャンセルが必要なら状態を更新する (Phase B).

        以下いずれかの条件を満たすとブーストを終了させる:
        1. boost_elapsed >= boost_max_duration
        2. current_en <= 0 (EN 切れ)
        3. ターゲットが MELEE_BOOST_ARRIVAL_RANGE (100m) 以内
        4. 慣性考慮キャンセル: 停止予想位置から遠距離武器の max_range 以内に入っている

        Args:
            actor: ブースト中のユニット
            target: 現在のターゲット（None の場合は条件 3/4 をスキップ）
            dt: 時間ステップ幅 (s)

        Returns:
            True: ブーストをキャンセルした（is_boosting を False に変更）
            False: ブーストを継続
        """
        unit_id = str(actor.id)
        resources = self.unit_resources[unit_id]

        if not resources.get("is_boosting", False):
            return False

        boost_max_duration = getattr(
            actor, "boost_max_duration", DEFAULT_BOOST_MAX_DURATION
        )
        boost_cooldown = getattr(actor, "boost_cooldown", DEFAULT_BOOST_COOLDOWN)
        boost_elapsed = resources.get("boost_elapsed", 0.0)
        current_en = resources.get("current_en", 0.0)

        cancel_reason: str | None = None

        # 条件 1: 最大継続時間超過
        if boost_elapsed >= boost_max_duration:
            cancel_reason = f"max_duration ({boost_max_duration}s) 到達"

        # 条件 2: EN 切れ
        elif current_en <= 0:
            cancel_reason = "EN 枯渇"

        elif target is not None:
            pos_actor = actor.position.to_numpy()
            pos_target = target.position.to_numpy()
            distance_to_target = float(np.linalg.norm(pos_target - pos_actor))

            # 条件 3: ターゲットが格闘到達射程内
            if distance_to_target <= MELEE_BOOST_ARRIVAL_RANGE:
                cancel_reason = f"格闘到達射程 ({MELEE_BOOST_ARRIVAL_RANGE}m) 以内"

            else:
                # 条件 4: 慣性考慮キャンセル判定
                # 使用予定の遠距離武器を取得
                ranged_weapon = next(
                    (
                        w
                        for w in actor.weapons
                        if not w.is_melee
                        and resources["weapon_states"]
                        .get(str(w.id), {})
                        .get("current_cool_down", 0)
                        == 0
                        and (
                            resources["weapon_states"]
                            .get(str(w.id), {})
                            .get("current_ammo")
                            is None
                            or resources["weapon_states"]
                            .get(str(w.id), {})
                            .get("current_ammo", 0)
                            > 0
                        )
                    ),
                    None,
                )

                if ranged_weapon is not None:
                    current_velocity: np.ndarray = resources["velocity_vec"]
                    current_speed = float(np.linalg.norm(current_velocity))
                    deceleration = actor.deceleration

                    # 停止距離: d_stop = v² / (2 × deceleration)
                    if deceleration > 0 and current_speed > 0:
                        d_stop = (current_speed**2) / (2.0 * deceleration)
                        stop_direction = current_velocity / current_speed

                        stop_pos = pos_actor + stop_direction * d_stop
                        d_to_target_from_stop = float(
                            np.linalg.norm(pos_target - stop_pos)
                        )

                        if d_to_target_from_stop <= ranged_weapon.range:
                            cancel_reason = (
                                f"慣性考慮キャンセル (停止予想位置からの射程内: "
                                f"{d_to_target_from_stop:.0f}m <= {ranged_weapon.range}m)"
                            )

        if cancel_reason is None:
            return False

        # ブースト終了処理
        resources["is_boosting"] = False
        resources["boost_cooldown_remaining"] = boost_cooldown

        self.logs.append(
            BattleLog(
                timestamp=float(self.elapsed_time),
                actor_id=actor.id,
                action_type="BOOST_END",
                message=(
                    f"{self._format_actor_name(actor)} のブーストが終了した"
                    f" (理由: {cancel_reason})"
                ),
                position_snapshot=actor.position,
                details={"reason": cancel_reason},
            )
        )

        return True

    def _search_movement(self, actor: MobileSuit, dt: float = 0.1) -> None:
        """索敵移動: 未発見の敵を探すための移動."""
        # 敵対勢力を特定 (team_idが異なるユニットが敵)
        potential_targets = [
            u for u in self.units if u.current_hp > 0 and u.team_id != actor.team_id
        ]

        if not potential_targets:
            return

        pos_actor = actor.position.to_numpy()
        unit_id = str(actor.id)

        # LOS 喪失済みの最終既知座標がある場合はそこへ向かう（Phase A）
        last_known = self.unit_resources[unit_id].get("last_known_enemy_position", {})
        if last_known:
            # 最も近い最終既知座標を選ぶ
            best_pos: np.ndarray | None = None
            best_dist = float("inf")
            for pos_list in last_known.values():
                p = np.array(pos_list)
                d = float(np.linalg.norm(p - pos_actor))
                if d < best_dist:
                    best_dist = d
                    best_pos = p
            if best_pos is not None:
                diff_vector = best_pos - pos_actor
                distance = float(np.linalg.norm(diff_vector))
                if distance > 0:
                    desired_direction = self._calculate_potential_field(
                        actor, target=None, retreat_points=self.retreat_points
                    )
                    self._apply_inertia(actor, desired_direction, dt)
                    if distance >= MOVE_LOG_MIN_DIST:
                        self.logs.append(
                            BattleLog(
                                timestamp=self.elapsed_time,
                                actor_id=actor.id,
                                action_type="MOVE",
                                message=(
                                    f"{self._format_actor_name(actor)}が最終目撃地点へ向かっている"
                                    f" (残距離: {int(distance)}m)"
                                ),
                                position_snapshot=actor.position,
                                velocity_snapshot=Vector3.from_numpy(
                                    self.unit_resources[unit_id]["velocity_vec"]
                                ),
                            )
                        )
                    return

        # 最も近い敵の方向へ移動（まだ発見していなくても）
        closest_enemy = min(
            potential_targets,
            key=lambda t: np.linalg.norm(t.position.to_numpy() - pos_actor),
        )

        pos_target = closest_enemy.position.to_numpy()
        diff_vector = pos_target - pos_actor
        distance = float(np.linalg.norm(diff_vector))

        if distance == 0:
            return

        # ポテンシャルフィールドで目標方向を算出し、慣性モデルで移動
        desired_direction = self._calculate_potential_field(
            actor, target=None, retreat_points=self.retreat_points
        )
        self._apply_inertia(actor, desired_direction, dt)

        # MOVE_LOG_MIN_DIST 以上の残距離のステップのみログ出力
        if distance >= MOVE_LOG_MIN_DIST:
            self.logs.append(
                BattleLog(
                    timestamp=self.elapsed_time,
                    actor_id=actor.id,
                    action_type="MOVE",
                    message=f"{self._format_actor_name(actor)}が索敵中 (残距離: {int(distance)}m)",
                    position_snapshot=actor.position,
                    velocity_snapshot=Vector3.from_numpy(
                        self.unit_resources[str(actor.id)]["velocity_vec"]
                    ),
                )
            )

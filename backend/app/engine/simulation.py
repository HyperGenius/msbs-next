# backend/app/engine/simulation.py
import logging
import uuid

import numpy as np

from app.engine.action_handler import ActionHandlerMixin
from app.engine.ai_decision import AiDecisionMixin
from app.engine.battle_utils import BattleUtilsMixin
from app.engine.calculator import PilotStats
from app.engine.combat import CombatMixin, has_los
from app.engine.constants import (
    FUZZY_RULES_DIR,
    MOVE_LOG_MIN_DIST,
    STRATEGY_UPDATE_INTERVAL,
    VALID_STRATEGY_MODES,
)
from app.engine.fuzzy_engine import FuzzyEngine
from app.engine.fuzzy_rule_cache import FuzzyRuleCache
from app.engine.movement import MovementMixin
from app.engine.strategy_controller import TeamMetrics, TeamStrategyController
from app.engine.targeting import TargetingMixin
from app.models.models import (
    BattleLog,
    MobileSuit,
    Obstacle,
    RetreatPoint,
)

logger = logging.getLogger(__name__)

# モジュールレベル定数（後方互換性のため維持）
_MAX_STEPS = 5000
# チームレベルイベントのダミー actor_id (Phase 4-2)
_TEAM_EVENT_ACTOR_ID: uuid.UUID = uuid.UUID(int=0)

# 後方互換性のため _has_los を re-export する
_has_los = has_los

__all__ = [
    "BattleSimulator",
    "_has_los",
    "MOVE_LOG_MIN_DIST",
]


class BattleSimulator(
    BattleUtilsMixin,
    CombatMixin,
    MovementMixin,
    TargetingMixin,
    AiDecisionMixin,
    ActionHandlerMixin,
):
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

        # チームレベルイベントのダミー actor_id (AiDecisionMixin で参照)
        self._team_event_actor_id: uuid.UUID = _TEAM_EVENT_ACTOR_ID

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
                "movement_heading_deg": 0.0,  # 移動方向の向き (XZ平面, 度) (Phase 6-1: heading_deg からリネーム)
                "body_heading_deg": 0.0,  # 胴体（砲塔）の向き (XZ平面, 度) (Phase 6-1)
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

        # 4. 胴体向き更新フェーズ (Phase 6-1)
        alive_units = [u for u in self.units if u.current_hp > 0]
        for unit in alive_units:
            self._update_body_heading(unit, dt)

        # 5. 行動フェーズ（全ユニットを同一ステップで並列処理）
        alive_units = [u for u in self.units if u.current_hp > 0]
        for unit in alive_units:
            if self.is_finished:
                break
            self._action_phase(unit, dt)

        # 6. 撤退離脱判定フェーズ (Phase 3-3)
        if self.retreat_points:
            self._retreat_check_phase()

        # 7. リソース更新フェーズ（EN回復・クールダウン減少）
        self._refresh_phase(dt)

        # 8. 時間を進める
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

# backend/app/engine/simulation.py
import logging
import math
import uuid

import numpy as np

from app.engine.action_handler import ActionHandlerMixin
from app.engine.ai_decision import AiDecisionMixin
from app.engine.battle_utils import BattleUtilsMixin
from app.engine.calculator import PilotStats
from app.engine.combat import CombatMixin, has_los
from app.engine.constants import (
    ALLY_REPULSION_RADIUS,
    AREA_PER_UNIT,
    FUZZY_RULES_DIR,
    MAX_FIELD_SIZE,
    MIN_FIELD_SIZE,
    MOVE_LOG_MIN_DIST,
    OBSTACLE_GRID_PARAMS,
    SPAWN_CENTER_JITTER_RADIUS,
    SPAWN_CENTER_SEARCH_MAX_TRIES,
    SPAWN_DETECTION_SAFETY_MARGIN,
    SPAWN_INITIAL_SPEED_RATIO,
    SPAWN_ZONE_MAP_OFFSET,
    SPAWN_ZONE_MIN_DIST_RELAXATION_FACTOR,
    SPAWN_ZONE_RADIUS_2TEAM,
    SPAWN_ZONE_RADIUS_3TEAM,
    SPAWN_ZONE_RADIUS_4TEAM,
    SPAWN_ZONE_SAMPLE_MAX_TRIES,
    STRATEGY_UPDATE_INTERVAL,
    VALID_STRATEGY_MODES,
)
from app.engine.fuzzy_engine import FuzzyEngine
from app.engine.fuzzy_rule_cache import FuzzyRuleCache
from app.engine.movement import MovementMixin
from app.engine.spatial_grid import PointSpatialGrid
from app.engine.strategy_controller import TeamMetrics, TeamStrategyController
from app.engine.targeting import TargetingMixin
from app.models.models import (
    BattleField,
    BattleLog,
    MobileSuit,
    Obstacle,
    RetreatPoint,
    SpawnZone,
    Vector3,
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


def _personality_pilot_stats(personality: str | None) -> PilotStats:
    """パーソナリティから NPC デフォルト PilotStats を返す (Phase E-2).

    仕様書 §3.5.3 の値を使用する。未知の personality は None 扱い（全スタット 1）。
    """
    table: dict[str | None, PilotStats] = {
        "AGGRESSIVE": PilotStats(sht=3, mel=4, intel=2, ref=4, tou=3, luk=1),
        "CAUTIOUS": PilotStats(sht=3, mel=1, intel=4, ref=2, tou=2, luk=3),
        "SNIPER": PilotStats(sht=6, mel=1, intel=3, ref=1, tou=1, luk=2),
        None: PilotStats(sht=1, mel=1, intel=1, ref=1, tou=1, luk=1),
    }
    return table.get(personality, table[None])


def _build_unit_pilot_stats(
    player: "MobileSuit",
    enemies: "list[MobileSuit]",
    player_pilot_stats: PilotStats,
    npc_pilot_stats: dict[str, PilotStats] | None,
) -> dict[str, PilotStats]:
    """全ユニットの unit_pilot_stats 辞書を構築する (Phase E-2).

    プレイヤーには player_pilot_stats を使用し、NPC は npc_pilot_stats の
    オーバーライドがあればそれを、なければ personality から解決する。
    """
    result: dict[str, PilotStats] = {str(player.id): player_pilot_stats}
    override = npc_pilot_stats or {}
    for enemy in enemies:
        uid = str(enemy.id)
        if uid in override:
            result[uid] = override[uid]
        else:
            result[uid] = _personality_pilot_stats(getattr(enemy, "personality", None))
    return result


def _resolve_flanking_skill_level(
    unit: "MobileSuit",
    is_player: bool,
    player_skills: dict[str, int] | None,
) -> int:
    """ユニットのフランキングスキルレベルを解決する (Phase E-3.5).

    Args:
        unit: 対象ユニット
        is_player: プレイヤーユニットかどうか
        player_skills: プレイヤーのスキル辞書

    Returns:
        フランキングスキルレベル (0〜3)
    """
    from app.core.npc_data import get_ace_pilot_by_id  # noqa: PLC0415

    if is_player:
        return (player_skills or {}).get("flanking", 0)

    ace_id: str | None = getattr(unit, "ace_id", None)
    if getattr(unit, "is_ace", False) and ace_id is not None:
        ace_data = get_ace_pilot_by_id(ace_id)
        if ace_data and "skills" in ace_data:
            return int(ace_data["skills"].get("flanking", 0))

    return 1 if getattr(unit, "personality", None) == "AGGRESSIVE" else 0


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
        npc_pilot_stats: dict[str, PilotStats] | None = None,
        retreat_points: list[RetreatPoint] | None = None,
        strategy_update_interval: int = STRATEGY_UPDATE_INTERVAL,
        enable_hot_reload: bool = False,
        obstacles: list[Obstacle] | None = None,
        battlefield: BattleField | None = None,
    ):
        """初期化.

        Args:
            player: プレイヤー機体
            enemies: 敵機体リスト
            player_skills: プレイヤーのスキル (skill_id: level)
            environment: 戦闘環境 (SPACE/GROUND/COLONY/UNDERWATER)
            special_effects: 特殊環境効果リスト (MINOVSKY/GRAVITY_WELL/OBSTACLE)
            player_pilot_stats: プレイヤーのパイロットステータス (SHT/MEL/INT/REF/TOU/LUK)
            npc_pilot_stats: ユニット ID → PilotStats の辞書。エース NPC の実ステータスを
                事前ロードして渡す。None の場合は enemy.personality から自動解決する (Phase E-2)。
            retreat_points: 撤退ポイントのリスト (Phase 3-3)
            strategy_update_interval: 何ステップごとに戦略評価を行うか (Phase 4-2)
            enable_hot_reload: True の場合、シミュレーション実行ごとにファジィルール JSON
                の変更を自動検出して再ロードする（ローカル開発用）。False の場合は
                起動時に一度だけロードしてスナップショットとして保持する（デフォルト）。
            obstacles: フィールド上の障害物リスト (Phase A — LOS システム)
            battlefield: バトルフィールド定義 (Phase 6-3)。obstacle_density / spawn_zones を含む。
                obstacles と同時に指定した場合は obstacles が優先される。

        Note:
            team_id が未設定のユニットは in-place で team_id が自動付与されます。
        """
        self.player = player
        self.enemies = enemies
        self.units: list[MobileSuit] = [player] + enemies
        # ユニット ID → ユニット の対応表（索敵・ターゲット選定処理でのO(1)引き当て用。Issue #446）
        # self.units の要素構成（リスト自体）はバトル中不変のため、生成時に一度だけ構築すればよい
        self._units_by_id: dict[uuid.UUID, MobileSuit] = {
            unit.id: unit for unit in self.units
        }
        # ユニット ID → self.units 内での出現順序（ターゲット選定の候補ソートで
        # 従来の走査順（self.units 順）による同点時タイブレークを再現するために使用。Issue #446）
        self._unit_order_index: dict[uuid.UUID, int] = {
            unit.id: i for i, unit in enumerate(self.units)
        }
        self.logs: list[BattleLog] = []
        self.elapsed_time: float = 0.0
        self._step_count: int = 0
        self.is_finished = False
        self.player_skills = player_skills or {}
        self.environment = environment
        self.special_effects: list[str] = special_effects or []
        self.player_pilot_stats: PilotStats = player_pilot_stats or PilotStats()
        self.retreat_points: list[RetreatPoint] = retreat_points or []

        # ユニット ID → パイロットステータス の対応表 (Phase E-2: NPC 全員適用)
        self.unit_pilot_stats: dict[str, PilotStats] = _build_unit_pilot_stats(
            self.player, self.enemies, self.player_pilot_stats, npc_pilot_stats
        )

        # team_id が未設定のユニットにはソロ参加用のIDを自動付与
        # (map_bounds 計算でチーム数を使うため、フィールドサイズ決定より前に行う)
        for unit in self.units:
            if unit.team_id is None:
                unit.team_id = str(unit.id)

        # フィールドスケーリング: 総ユニット数に応じて map_bounds を動的計算 (Phase 6-5)
        # グローバル定数 MAP_BOUNDS を変更せず、インスタンス変数として保持する
        n_total = len(self.units)
        side_len = math.sqrt(n_total * AREA_PER_UNIT)
        side_len = max(MIN_FIELD_SIZE, min(MAX_FIELD_SIZE, side_len))

        # スポーン時の索敵回避: デフォルトスポーン領域を使う場合、チーム間のスポーン領域が
        # 「戦闘参加ユニットの最大 sensor_range + 安全マージン」以上離れるようフィールド
        # サイズを拡張する。ユニット数が少ない戦闘では AREA_PER_UNIT 由来の面積が
        # MIN_FIELD_SIZE にクランプされてしまい、sensor_range に対してフィールドが
        # 狭すぎ、スポーン直後から索敵が成立してしまうケースがあったための対応。
        # battlefield が明示的に渡されなかった場合、_resolve_obstacles_and_spawn_zones
        # 自体が呼ばれず spawn_zones は生成されない（後方互換性）ため、その場合は
        # フィールド拡張も行わない
        uses_default_spawn_zones = (
            battlefield is not None and not battlefield.spawn_zones
        )
        if uses_default_spawn_zones:
            n_teams = len({u.team_id for u in self.units if u.team_id is not None})
            max_sensor_range = max((u.sensor_range for u in self.units), default=500.0)
            # 障害物が生成される場合、スポーン中心は _find_clear_spawn_center() により
            # 最大 SPAWN_CENTER_JITTER_RADIUS だけ障害物回避のためジッターしうる。
            # 最悪ケース（異チームの2ゾーンが互いに近づく向きへジッター）でも
            # required_separation を下回らないよう、両ゾーン分（×2）を安全マージンに
            # 上乗せしておく（Copilotレビュー指摘への対応）。
            required_separation = (
                max_sensor_range
                + SPAWN_DETECTION_SAFETY_MARGIN
                + 2.0 * SPAWN_CENTER_JITTER_RADIUS
            )
            required_field_size = self._min_field_size_for_team_layout(
                n_teams, required_separation
            )
            if required_field_size > MAX_FIELD_SIZE:
                logger.warning(
                    "チーム数 %d・最大索敵範囲 %.1fm では MAX_FIELD_SIZE=%.1fm 内で"
                    "スポーン時の索敵回避を保証できません。フィールドを上限まで拡張します。",
                    n_teams,
                    max_sensor_range,
                    MAX_FIELD_SIZE,
                )
            side_len = max(side_len, min(MAX_FIELD_SIZE, required_field_size))

        self.map_bounds: tuple[float, float] = (0.0, side_len)

        # battlefield パラメータの解決 (Phase 6-3)
        # 明示的な obstacles 引数が渡された場合は後方互換性のためそれを優先する
        # battlefield が明示的に渡された場合のみ自動生成・適用する（後方互換性）
        self._battlefield_explicit: bool = battlefield is not None
        if battlefield is None:
            battlefield = BattleField()
        self.battlefield: BattleField = battlefield
        if obstacles is not None:
            # 後方互換: obstacles 引数が明示的に渡された場合は battlefield を上書き
            self.battlefield = BattleField(
                obstacles=obstacles,
                spawn_zones=battlefield.spawn_zones,
                obstacle_density=battlefield.obstacle_density,
            )
        self.obstacles: list[Obstacle] = self.battlefield.obstacles

        # チームレベルイベントのダミー actor_id (AiDecisionMixin で参照)
        self._team_event_actor_id: uuid.UUID = _TEAM_EVENT_ACTOR_ID

        # 索敵状態管理 (チーム単位で共有)
        self.team_detected_units: dict[str, set] = {
            unit.team_id: set() for unit in self.units if unit.team_id is not None
        }

        # 発見ステップ記録: {team_id: {target_unit_id_str: step_count_at_detection}}
        # _select_target_fuzzy / _select_target_legacy でリアクション遅延チェックに使用する
        self.detection_step_map: dict[str, dict[str, int]] = {
            unit.team_id: {} for unit in self.units if unit.team_id is not None
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
                "flanking_skill_level": 0,  # フランキングスキルレベル (Phase E-3.5)
            }
            # 各武器のリソース状態を初期化
            for weapon in unit.weapons:
                weapon_id = weapon.id
                self.unit_resources[unit_id]["weapon_states"][weapon_id] = {
                    "current_ammo": weapon.max_ammo
                    if weapon.max_ammo is not None
                    else None,
                    "cooldown_remaining_sec": 0.0,  # 残りクールダウン時間（秒）(Phase 6-2)
                }

            # フランキングスキルレベルの解決 (Phase E-3.5)
            self.unit_resources[unit_id]["flanking_skill_level"] = (
                _resolve_flanking_skill_level(
                    unit,
                    is_player=str(unit.id) == str(self.player.id),
                    player_skills=self.player_skills,
                )
            )

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

        # 障害物・スポーン領域の解決と適用 (Phase 6-3)
        # battlefield が明示的に渡された場合のみ自動生成・適用する（後方互換性）
        if self._battlefield_explicit:
            self._resolve_obstacles_and_spawn_zones()

        # シグモイドダメージ計算キャッシュ: 全ユニット分を一括計算 (Phase E-1)
        self._build_combat_multiplier_cache()

    # ---------------------------------------------------------------------------
    # Phase 6-3: スポーン領域・障害物自動生成メソッド
    # ---------------------------------------------------------------------------

    def _resolve_obstacles_and_spawn_zones(self) -> None:
        """障害物・スポーン領域を解決し、self.battlefield / self.obstacles に反映する.

        Issue #437: 障害物を先に配置し、スポーン領域はその配置を踏まえて決定する
        （障害物→スポーンの順）。これにより障害物が実際の交戦エリアに影響を持つ。
        最終的に、ジッター探索で避けきれなかった障害物や明示的に渡されたスポーン
        領域と重なる障害物を除去し、ユニットが障害物に埋まって出現しないことを保証する。
        """
        # 障害物の自動生成（obstacles が空かつ obstacle_density != "NONE" のとき）
        if not self.obstacles and self.battlefield.obstacle_density != "NONE":
            generated = self._generate_obstacles()
            self.battlefield = BattleField(
                obstacles=generated,
                spawn_zones=self.battlefield.spawn_zones,
                obstacle_density=self.battlefield.obstacle_density,
            )
            self.obstacles = self.battlefield.obstacles

        # スポーン領域はこの時点の障害物配置を踏まえて決定する
        # （デフォルト生成の場合は _generate_default_spawn_zones 内でジッター回避する）
        spawn_zones = (
            self.battlefield.spawn_zones or self._generate_default_spawn_zones()
        )

        cleared_obstacles = (
            self._remove_obstacles_overlapping_spawn_zones(self.obstacles, spawn_zones)
            if self.obstacles and spawn_zones
            else self.obstacles
        )

        self.battlefield = BattleField(
            obstacles=cleared_obstacles,
            spawn_zones=spawn_zones,
            obstacle_density=self.battlefield.obstacle_density,
        )
        self.obstacles = self.battlefield.obstacles

        self._apply_spawn_zones()

    @staticmethod
    def _min_field_size_for_team_layout(
        n_teams: int, required_separation: float
    ) -> float:
        """デフォルトスポーン配置で異チーム間隔が required_separation 以上になるために必要な最小フィールド辺長を計算する.

        `_generate_default_spawn_zones` が生成する対称配置（2チーム: 対角、
        3/4チーム: 均等分割、5チーム以上: 円周上均等配置）ごとに、最も近接する
        ペアの中心間距離からスポーン半径を差し引いた間隔が required_separation を
        満たす条件を辺長 L について逆算する。

        Args:
            n_teams: チーム数
            required_separation: 異チームのスポーン領域間で確保したい最小間隔 (m)。
                中心間距離から両ゾーンの radius を差し引いた「縁と縁の距離」を指す。

        Returns:
            必要な最小フィールド辺長 (m)
        """
        offset = SPAWN_ZONE_MAP_OFFSET
        if n_teams <= 1:
            return MIN_FIELD_SIZE

        if n_teams == 2:
            # 対角配置: 中心間距離 = sqrt(2) * (L - 2*offset)
            radius = SPAWN_ZONE_RADIUS_2TEAM
            return 2.0 * offset + (required_separation + 2.0 * radius) / math.sqrt(2.0)

        if n_teams in (3, 4):
            # 最も近接するペア（同一辺上に並ぶ隣接頂点）: 中心間距離 = L - 2*offset
            radius = (
                SPAWN_ZONE_RADIUS_3TEAM if n_teams == 3 else SPAWN_ZONE_RADIUS_4TEAM
            )
            return 2.0 * offset + required_separation + 2.0 * radius

        # 5チーム以上: 円周上の隣接ペアの弦長 = 2 * r_field * sin(pi / n_teams)
        radius = SPAWN_ZONE_RADIUS_4TEAM
        chord_needed = required_separation + 2.0 * radius
        r_field = chord_needed / (2.0 * math.sin(math.pi / n_teams))
        return 2.0 * (r_field + offset)

    def _generate_default_spawn_zones(self) -> list[SpawnZone]:
        """チーム数とマップサイズに応じたデフォルトスポーン領域を生成する (Phase 6-3).

        障害物は本メソッドの実行前に生成済みであるため (#437)、各チームの対称配置
        候補点が障害物と重なる場合は `_find_clear_spawn_center` で近傍の空き位置を探索する。

        Returns:
            生成されたスポーン領域リスト
        """
        map_min, map_max = self.map_bounds
        offset = SPAWN_ZONE_MAP_OFFSET  # マップ端からのオフセット (m)

        # チームIDを収集（順序安定化のためソート）
        team_ids = sorted(
            {unit.team_id for unit in self.units if unit.team_id is not None}
        )
        n_teams = len(team_ids)

        if n_teams == 0:
            return []

        # 2チーム: 対角配置
        if n_teams == 2:
            centers = [
                (map_min + offset, map_min + offset),
                (map_max - offset, map_max - offset),
            ]
            radius = SPAWN_ZONE_RADIUS_2TEAM
        # 3チーム: 三角形頂点
        elif n_teams == 3:
            centers = [
                (map_min + offset, map_min + offset),
                (map_max - offset, map_min + offset),
                ((map_min + map_max) / 2.0, map_max - offset),
            ]
            radius = SPAWN_ZONE_RADIUS_3TEAM
        # 4チーム: 四隅
        elif n_teams == 4:
            centers = [
                (map_min + offset, map_min + offset),
                (map_max - offset, map_min + offset),
                (map_min + offset, map_max - offset),
                (map_max - offset, map_max - offset),
            ]
            radius = SPAWN_ZONE_RADIUS_4TEAM
        else:
            # 5チーム以上: 円周上に均等配置
            cx = (map_min + map_max) / 2.0
            cz = (map_min + map_max) / 2.0
            r_field = (map_max - map_min) / 2.0 - offset
            centers = [
                (
                    cx + r_field * math.cos(2 * math.pi * i / n_teams),
                    cz + r_field * math.sin(2 * math.pi * i / n_teams),
                )
                for i in range(n_teams)
            ]
            radius = SPAWN_ZONE_RADIUS_4TEAM

        rng = np.random.default_rng()
        centers = [
            self._find_clear_spawn_center(center, radius, rng) for center in centers
        ]

        return [
            SpawnZone(
                team_id=team_id,
                center=Vector3(x=cx, y=0.0, z=cz),
                radius=radius,
            )
            for team_id, (cx, cz) in zip(team_ids, centers, strict=True)
        ]

    @staticmethod
    def _remove_obstacles_overlapping_spawn_zones(
        obstacles: list[Obstacle], spawn_zones: list[SpawnZone]
    ) -> list[Obstacle]:
        """スポーン領域と重なる障害物を除去する (#437 の最終保証フォールバック).

        `_find_clear_spawn_center` のジッター探索は障害物密度が高い狭いフィールド
        では回避に失敗する場合がある（フィールド全体が障害物で埋まっているなど）。
        本メソッドは最終的な spawn_zones と障害物リストを突き合わせ、重なりが残って
        いる障害物を取り除くことで、ユニットが障害物に埋まって出現しないことを保証する。

        Args:
            obstacles: 障害物リスト
            spawn_zones: 最終的なスポーン領域リスト（自動生成・明示指定いずれも可）

        Returns:
            スポーン領域と重ならない障害物のみのリスト
        """
        return [
            obs
            for obs in obstacles
            if not any(
                math.sqrt(
                    (obs.position.x - sz.center.x) ** 2
                    + (obs.position.z - sz.center.z) ** 2
                )
                < sz.radius + obs.radius
                for sz in spawn_zones
            )
        ]

    @staticmethod
    def _spawn_center_overlaps_obstacles(
        x: float, z: float, radius: float, obstacles: list[Obstacle]
    ) -> bool:
        """スポーン中心候補が、いずれかの障害物と重なるかを判定する (#437)."""
        for obs in obstacles:
            dist = math.sqrt((x - obs.position.x) ** 2 + (z - obs.position.z) ** 2)
            if dist < radius + obs.radius:
                return True
        return False

    def _find_clear_spawn_center(
        self,
        candidate: tuple[float, float],
        radius: float,
        rng: np.random.Generator,
    ) -> tuple[float, float]:
        """スポーン中心候補が障害物と重なる場合、近傍で重ならない位置を探索する (#437).

        対称配置（対角・三角形・四隅・円周）の形状を大きく崩さないよう、候補点を
        中心とした半径 SPAWN_CENTER_JITTER_RADIUS 以内でジッターさせながら再探索する。
        試行上限に達した場合は候補点をそのまま返す（フィールド全体が障害物で
        埋め尽くされるような極端なケースでのみ発生しうる）。

        Args:
            candidate: 対称配置から算出された候補中心座標 (x, z)
            radius: スポーン領域の半径 (m)
            rng: 乱数生成器

        Returns:
            障害物と重ならない中心座標 (x, z)。見つからない場合は candidate をそのまま返す。
        """
        cx, cz = candidate
        if not self.obstacles or not self._spawn_center_overlaps_obstacles(
            cx, cz, radius, self.obstacles
        ):
            return candidate

        map_min, map_max = self.map_bounds
        # 中心のクランプ範囲は radius ぶんのマージンを確保する（スポーン領域自体が
        # フィールド外へはみ出さないようにするため）。フィールドが radius の2倍より
        # 狭い極端なケースではマージンを縮小してクランプ範囲の逆転を防ぐ。
        margin = min(radius, (map_max - map_min) / 2.0)
        clamp_min, clamp_max = map_min + margin, map_max - margin
        for _ in range(SPAWN_CENTER_SEARCH_MAX_TRIES):
            angle = rng.uniform(0.0, 2.0 * math.pi)
            dist = rng.uniform(0.0, SPAWN_CENTER_JITTER_RADIUS)
            x = min(max(cx + dist * math.cos(angle), clamp_min), clamp_max)
            z = min(max(cz + dist * math.sin(angle), clamp_min), clamp_max)
            if not self._spawn_center_overlaps_obstacles(x, z, radius, self.obstacles):
                return (x, z)

        logger.warning(
            "スポーン中心候補 (%.1f, %.1f) 付近で障害物を回避できる位置が"
            "見つかりませんでした (%d 回試行)。候補点をそのまま使用します。",
            cx,
            cz,
            SPAWN_CENTER_SEARCH_MAX_TRIES,
        )
        return candidate

    @staticmethod
    def _sample_position_in_zone(
        zone: SpawnZone,
        placed_grid: PointSpatialGrid,
        min_dist: float,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        """スポーン領域内でユニットの配置位置をサンプリングする (Phase 6-3, Issue #447).

        円内の一様サンプリング（r = radius * sqrt(U), θ = 2π * V）を使用する。
        既配置ユニットとの最小距離 min_dist が保証されるまでリサンプリングする。
        SPAWN_ZONE_SAMPLE_MAX_TRIES 回試行後も配置できない場合は min_dist を段階的に緩和する。

        既配置位置との距離判定には `placed_grid`（`PointSpatialGrid`）を使い、候補点の
        近傍セルのみを走査する。`placed_grid` のセルサイズは呼び出し側（`_apply_spawn_zones`）
        が min_dist（緩和前の最大値）以上に設定している前提のため、緩和後の
        current_min_dist に対しても近傍セル探索だけで漏れなく判定できる。

        Args:
            zone: スポーン領域
            placed_grid: 既に配置されたユニット位置を格納したグリッド
            min_dist: 既配置ユニットとの最小距離 (m)
            rng: 乱数生成器。None の場合は numpy のデフォルト RNG を使用する。

        Returns:
            配置位置 np.ndarray([x, y, z])
        """
        if rng is None:
            rng = np.random.default_rng()

        # radius=0 の場合は常に中心座標を返す（計算省略）
        if zone.radius == 0.0:
            return np.array([zone.center.x, zone.center.y, zone.center.z])

        current_min_dist = min_dist
        for attempt in range(SPAWN_ZONE_SAMPLE_MAX_TRIES * 3):
            # 段階的に min_dist を緩和する (SPAWN_ZONE_SAMPLE_MAX_TRIES 試行ごとに半減)
            if attempt > 0 and attempt % SPAWN_ZONE_SAMPLE_MAX_TRIES == 0:
                current_min_dist *= SPAWN_ZONE_MIN_DIST_RELAXATION_FACTOR

            r = zone.radius * math.sqrt(rng.random())
            theta = 2.0 * math.pi * rng.random()
            x = zone.center.x + r * math.cos(theta)
            z = zone.center.z + r * math.sin(theta)
            pos = np.array([x, zone.center.y, z])

            neighbor_dists = [
                float(np.linalg.norm(pos - p)) for p in placed_grid.neighbors(pos)
            ]
            if not neighbor_dists or min(neighbor_dists) >= current_min_dist:
                return pos

        # 最終フォールバック: 全試行失敗時は中心座標を返す
        # （ゾーンが狭くユニットが多い場合に発生しうる）
        logger.warning(
            "スポーン領域 %s (radius=%.1f) でユニット配置に失敗 (%d 回試行)。中心座標を使用します。",
            zone.team_id,
            zone.radius,
            SPAWN_ZONE_SAMPLE_MAX_TRIES * 3,
        )
        return np.array([zone.center.x, zone.center.y, zone.center.z])

    def _apply_spawn_zones(self) -> None:
        """スポーン領域に基づいて全ユニットの初期位置・初速を設定する (Phase 6-3).

        self.battlefield.spawn_zones から team_id をキーとした領域マップを作成し、
        各チームのユニットを対応する領域内にランダム配置する。
        ALLY_REPULSION_RADIUS 以上の同チーム内間隔を保証する。
        また、各ユニットにはスポーン領域中心からフィールド中心へ向かう方向へ
        SPAWN_INITIAL_SPEED_RATIO 分の初速を付与し、フィールドに侵入していく
        シチュエーションを表現する。
        """
        zone_map: dict[str, SpawnZone] = {
            sz.team_id: sz for sz in self.battlefield.spawn_zones
        }
        if not zone_map:
            return

        # チームごとに処理
        team_units: dict[str, list[MobileSuit]] = {}
        for unit in self.units:
            if unit.team_id and unit.team_id in zone_map:
                team_units.setdefault(unit.team_id, []).append(unit)

        map_min, map_max = self.map_bounds
        field_center = (map_min + map_max) / 2.0

        rng = np.random.default_rng()
        for team_id, units in team_units.items():
            zone = zone_map[team_id]

            # スポーン領域中心からフィールド中心への単位方向ベクトル (XZ平面)
            direction = np.array(
                [field_center - zone.center.x, 0.0, field_center - zone.center.z]
            )
            direction_norm = float(np.linalg.norm(direction))
            unit_direction = (
                direction / direction_norm if direction_norm > 1e-6 else np.zeros(3)
            )
            heading_deg = math.degrees(
                math.atan2(float(unit_direction[2]), float(unit_direction[0]))
            )

            placed_grid = PointSpatialGrid(cell_size=ALLY_REPULSION_RADIUS)
            for unit in units:
                pos = self._sample_position_in_zone(
                    zone, placed_grid, ALLY_REPULSION_RADIUS, rng
                )
                unit.position = Vector3(
                    x=float(pos[0]), y=float(pos[1]), z=float(pos[2])
                )
                placed_grid.insert(pos)

                initial_velocity = (
                    unit_direction * unit.max_speed * SPAWN_INITIAL_SPEED_RATIO
                )
                unit.velocity = Vector3.from_numpy(initial_velocity)
                resources = self.unit_resources[str(unit.id)]
                resources["velocity_vec"] = initial_velocity
                resources["movement_heading_deg"] = heading_deg
                resources["body_heading_deg"] = heading_deg

    def _generate_obstacles(self) -> list[Obstacle]:
        """障害物をグリッド分割＋ランダムオフセット方式で自動生成する (Phase 6-3).

        フィールドを N×N グリッドに分割し、各セルに確率 p で障害物を配置する。
        本メソッドはスポーン領域の生成前に実行される (#437)。スポーン領域は
        `_generate_default_spawn_zones` 側でこの障害物配置を踏まえて決定される
        ため、ここではスポーン領域との重複回避は行わない。

        Returns:
            生成された障害物リスト
        """
        density = self.battlefield.obstacle_density.upper()
        if density == "NONE" or density not in OBSTACLE_GRID_PARAMS:
            return []

        params = OBSTACLE_GRID_PARAMS[density]
        n: int = params["n"]
        prob: float = params["prob"]
        radius_min: float = params["radius_range"][0]
        radius_max: float = params["radius_range"][1]

        map_min, map_max = self.map_bounds
        cell_size = (map_max - map_min) / n

        obstacles: list[Obstacle] = []
        rng = np.random.default_rng()
        obs_counter = 0

        for i in range(n):
            for j in range(n):
                if rng.random() > prob:
                    continue

                # セル中心 + ランダムオフセット（セルの 40% 以内）
                cell_cx = map_min + (i + 0.5) * cell_size
                cell_cz = map_min + (j + 0.5) * cell_size
                offset_limit = cell_size * 0.4
                ox = rng.uniform(-offset_limit, offset_limit)
                oz = rng.uniform(-offset_limit, offset_limit)
                obs_x = cell_cx + ox
                obs_z = cell_cz + oz
                obs_radius = float(rng.uniform(radius_min, radius_max))

                obstacles.append(
                    Obstacle(
                        obstacle_id=f"auto_obs_{obs_counter}",
                        position=Vector3(x=obs_x, y=0.0, z=obs_z),
                        radius=obs_radius,
                        height=obs_radius * 1.5,
                    )
                )
                obs_counter += 1

        return obstacles

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

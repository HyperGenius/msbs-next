import uuid
from datetime import UTC, datetime
from typing import Any

import numpy as np
from pydantic import field_validator
from sqlalchemy import JSON, UniqueConstraint
from sqlmodel import Column, Field, SQLModel

# --- Component Models (JSONとしてDBに保存される部品) ---


class Vector3(SQLModel):
    """3次元座標・ベクトル定義."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_numpy(self) -> np.ndarray:
        """NumPy配列に変換（計算用）."""
        return np.array([self.x, self.y, self.z])

    @classmethod
    def from_numpy(cls, arr: np.ndarray) -> "Vector3":
        """NumPy配列からインスタンス生成."""
        return cls(x=float(arr[0]), y=float(arr[1]), z=float(arr[2]))


class Weapon(SQLModel):
    """武装データ."""

    id: str
    name: str
    power: int = Field(description="威力")
    range: float = Field(description="射程距離")
    accuracy: float = Field(description="基本命中率(%)")
    type: str = Field(default="PHYSICAL", description="武器属性 (BEAM/PHYSICAL)")
    weapon_type: str = Field(
        default="RANGED",
        description="武器種別 (MELEE/CLOSE_RANGE/RANGED) — Phase C 近接戦闘システム用",
    )
    optimal_range: float = Field(default=300.0, description="最適射程距離")
    decay_rate: float = Field(default=0.05, description="距離による命中率減衰係数")
    is_melee: bool = Field(default=False, description="近接武器かどうか")
    max_ammo: int | None = Field(
        default=None, description="最大弾数 (Noneまたは0の場合は無限/EN兵器)"
    )
    en_cost: int = Field(default=0, description="射撃ごとの消費EN (実弾兵器は通常0)")
    cool_down_turn: int = Field(
        default=0, description="発射後の再使用待機ターン数（後方互換用）"
    )
    cooldown_sec: float = Field(
        default=1.0,
        description="発射後の再使用待機時間（秒）。0.0 は連射可能を意味する",
    )
    fire_arc_deg: float = Field(
        default=30.0,
        description="射撃可能弧（胴体正面からの片側角度、度）。格闘武器は 360 を設定",
    )


class WeaponResponse(Weapon):
    """武器APIレスポンスモデル (ランクフィールド付き)."""

    power_rank: str = "C"
    range_rank: str = "C"
    accuracy_rank: str = "C"

    @classmethod
    def from_weapon(cls, weapon: "Weapon") -> "WeaponResponse":
        """WeaponインスタンスからWeaponResponseを生成する."""
        from app.core.rank_utils import get_rank

        data = weapon.model_dump() if hasattr(weapon, "model_dump") else dict(weapon)
        return cls(
            **data,
            power_rank=get_rank("weapon_power", weapon.power),
            range_rank=get_rank("weapon_range", weapon.range),
            accuracy_rank=get_rank("weapon_accuracy", weapon.accuracy),
        )


# --- Database Models (テーブル定義) ---


class MobileSuit(SQLModel, table=True):
    """モビルスーツ本体データ (DBテーブル)."""

    __tablename__ = "mobile_suits"

    # ID & Ownership
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str | None = Field(default=None, index=True, description="Clerk User ID")

    # Basic Status
    name: str = Field(index=True)
    max_hp: int = Field(description="最大耐久値")
    current_hp: int = Field(default=0, description="現在耐久値")
    armor: int = Field(default=0, description="装甲値(ダメージ軽減)")
    mobility: float = Field(default=1.0, description="機動性(回避・移動速度係数)")
    sensor_range: float = Field(default=500.0, description="索敵範囲")
    side: str = Field(default="PLAYER", description="陣営 (PLAYER/ENEMY)")
    team_id: str | None = Field(
        default=None, description="戦闘チームID (戦闘時のみ使用、Noneの場合はソロ参加)"
    )
    beam_resistance: float = Field(default=0.0, description="対ビーム防御力 (0.0~1.0)")
    physical_resistance: float = Field(
        default=0.0, description="対実弾防御力 (0.0~1.0)"
    )

    # Detailed Parameters (詳細パラメータ)
    melee_aptitude: float = Field(default=1.0, description="格闘適性 (基準値: 1.0)")
    shooting_aptitude: float = Field(default=1.0, description="射撃適性 (基準値: 1.0)")
    accuracy_bonus: float = Field(default=0.0, description="命中補正 (基準値: 0.0)")
    evasion_bonus: float = Field(default=0.0, description="回避補正 (基準値: 0.0)")
    acceleration_bonus: float = Field(
        default=1.0, description="加速補正 (基準値: 1.0, 将来の慣性移動用)"
    )
    turning_bonus: float = Field(
        default=1.0, description="旋回補正 (基準値: 1.0, 将来の向き・旋回速度用)"
    )

    # Physics Parameters for Inertia Model (Phase 3-1)
    max_speed: float = Field(default=80.0, description="最大速度 (m/s)")
    acceleration: float = Field(default=30.0, description="加速度 (m/s²)")
    deceleration: float = Field(default=50.0, description="減速度 (m/s²)")
    max_turn_rate: float = Field(default=360.0, description="最大旋回速度 (deg/s)")
    body_turn_rate: float = Field(
        default=720.0, description="胴体（砲塔）の最大旋回速度 (deg/s) (Phase 6-1)"
    )

    terrain_adaptability: dict[str, str] = Field(
        default_factory=lambda: {
            "SPACE": "A",
            "GROUND": "A",
            "COLONY": "A",
            "UNDERWATER": "C",
        },
        sa_column=Column(JSON),
        description="地形適正 (SPACE/GROUND/COLONY/UNDERWATER: S/A/B/C/D)",
    )

    # Energy & Propellant Systems
    max_en: int = Field(
        default=1000, description="最大エネルギー容量 (ジェネレーター出力)"
    )
    en_recovery: int = Field(default=100, description="ターン毎のEN回復量")
    max_propellant: int = Field(
        default=1000, description="最大推進剤容量 (将来的な移動コスト用)"
    )

    # Boost Dash Parameters (Phase B)
    boost_speed_multiplier: float = Field(
        default=2.0, description="ブースト時速度倍率 (max_speed × multiplier)"
    )
    boost_en_cost: float = Field(default=5.0, description="ブースト中 EN 消費量 (/s)")
    boost_max_duration: float = Field(
        default=3.0, description="1 回のブーストの最大継続時間 (s)"
    )
    boost_cooldown: float = Field(
        default=5.0, description="ブースト終了後の再使用不可時間 (s)"
    )

    # Complex Types (Stored as JSON in Postgres)
    # SQLModel + SQLAlchemy JSON Column mapping
    position: Vector3 = Field(default_factory=Vector3, sa_column=Column(JSON))
    velocity: Vector3 = Field(default_factory=Vector3, sa_column=Column(JSON))
    weapons: list[Weapon] = Field(default_factory=list, sa_column=Column(JSON))

    # Tactics Configuration
    tactics: dict = Field(
        default_factory=lambda: {"priority": "CLOSEST", "range": "BALANCED"},
        sa_column=Column(JSON),
        description="戦術設定 (priority: CLOSEST/WEAKEST/RANDOM, range: MELEE/RANGED/BALANCED/FLEE)",
    )

    active_weapon_index: int = Field(default=0)

    # Strategy Mode
    strategy_mode: str | None = Field(
        default=None,
        description="戦略モード (AGGRESSIVE/DEFENSIVE/SNIPER/ASSAULT/RETREAT)。未設定の場合は AGGRESSIVE にフォールバック",
    )

    # NPC Personality System
    personality: str | None = Field(
        default=None, description="NPC性格 (AGGRESSIVE/CAUTIOUS/SNIPER)"
    )
    is_ace: bool = Field(default=False, description="エースパイロットかどうか")
    ace_id: str | None = Field(default=None, description="エースパイロットID")
    pilot_name: str | None = Field(default=None, description="パイロット名")
    bounty_exp: int = Field(default=0, description="撃破時のボーナス経験値")
    bounty_credits: int = Field(default=0, description="撃破時のボーナスクレジット")

    # Initialize current_hp to max_hp if not set
    @field_validator("current_hp")
    @classmethod
    def set_current_hp(cls, v: int, info) -> int:  # type: ignore
        """現在耐久値を最大耐久値に設定する."""
        # Note: In Pydantic v2, accessing other fields during validation is tricky if they aren't validated yet.
        # But here we just want to ensure it has a value.
        # Logic to sync max_hp is better handled in application logic or @model_validator.
        return v

    def get_active_weapon(self) -> Weapon | None:
        """現在選択中の武器を返す."""
        if 0 <= self.active_weapon_index < len(self.weapons):
            return self.weapons[self.active_weapon_index]
        return None


class MobileSuitUpdate(SQLModel):
    """機体更新用データモデル (Request Body)."""

    name: str | None = None
    max_hp: int | None = None
    armor: int | None = None
    mobility: float | None = None
    tactics: dict | None = None
    melee_aptitude: float | None = None
    shooting_aptitude: float | None = None
    accuracy_bonus: float | None = None
    evasion_bonus: float | None = None
    acceleration_bonus: float | None = None
    turning_bonus: float | None = None
    boost_speed_multiplier: float | None = None
    boost_en_cost: float | None = None
    boost_max_duration: float | None = None
    boost_cooldown: float | None = None


# --- Response Models (APIレスポンス用) ---


class MobileSuitResponse(SQLModel):
    """機体APIレスポンスモデル (ランクフィールド付き)."""

    id: uuid.UUID
    user_id: str | None = None
    name: str
    max_hp: int
    current_hp: int
    armor: int
    mobility: float
    sensor_range: float = 500.0
    side: str = "PLAYER"
    team_id: str | None = None
    beam_resistance: float = 0.0
    physical_resistance: float = 0.0
    melee_aptitude: float = 1.0
    shooting_aptitude: float = 1.0
    accuracy_bonus: float = 0.0
    evasion_bonus: float = 0.0
    acceleration_bonus: float = 1.0
    turning_bonus: float = 1.0
    terrain_adaptability: dict[str, str] = {}
    max_en: int = 1000
    en_recovery: int = 100
    max_propellant: int = 1000
    position: "Vector3" = None  # type: ignore[assignment]
    velocity: "Vector3" = None  # type: ignore[assignment]
    weapons: list["WeaponResponse"] = []
    tactics: dict = {}
    active_weapon_index: int = 0
    personality: str | None = None
    is_ace: bool = False
    ace_id: str | None = None
    pilot_name: str | None = None
    bounty_exp: int = 0
    bounty_credits: int = 0

    # Boost Dash Parameters (Phase B)
    boost_speed_multiplier: float = 2.0
    boost_en_cost: float = 5.0
    boost_max_duration: float = 3.0
    boost_cooldown: float = 5.0

    # Rank fields (computed from raw values)
    hp_rank: str = "C"
    armor_rank: str = "C"
    mobility_rank: str = "C"

    @classmethod
    def from_mobile_suit(cls, ms: "MobileSuit") -> "MobileSuitResponse":
        """MobileSuitインスタンスからMobileSuitResponseを生成する."""
        from app.core.rank_utils import get_rank

        weapons_response = []
        for w in ms.weapons:
            if isinstance(w, dict):
                weapon_obj = Weapon(**w)
            else:
                weapon_obj = w
            weapons_response.append(WeaponResponse.from_weapon(weapon_obj))

        return cls(
            id=ms.id,
            user_id=ms.user_id,
            name=ms.name,
            max_hp=ms.max_hp,
            current_hp=ms.current_hp,
            armor=ms.armor,
            mobility=ms.mobility,
            sensor_range=ms.sensor_range,
            side=ms.side,
            team_id=ms.team_id,
            beam_resistance=ms.beam_resistance,
            physical_resistance=ms.physical_resistance,
            melee_aptitude=ms.melee_aptitude,
            shooting_aptitude=ms.shooting_aptitude,
            accuracy_bonus=ms.accuracy_bonus,
            evasion_bonus=ms.evasion_bonus,
            acceleration_bonus=ms.acceleration_bonus,
            turning_bonus=ms.turning_bonus,
            terrain_adaptability=ms.terrain_adaptability,
            max_en=ms.max_en,
            en_recovery=ms.en_recovery,
            max_propellant=ms.max_propellant,
            position=ms.position,
            velocity=ms.velocity,
            weapons=weapons_response,
            tactics=ms.tactics,
            active_weapon_index=ms.active_weapon_index,
            personality=ms.personality,
            is_ace=ms.is_ace,
            ace_id=ms.ace_id,
            pilot_name=ms.pilot_name,
            bounty_exp=ms.bounty_exp,
            bounty_credits=ms.bounty_credits,
            hp_rank=get_rank("hp", ms.max_hp),
            armor_rank=get_rank("armor", ms.armor),
            mobility_rank=get_rank("mobility", ms.mobility),
            boost_speed_multiplier=ms.boost_speed_multiplier,
            boost_en_cost=ms.boost_en_cost,
            boost_max_duration=ms.boost_max_duration,
            boost_cooldown=ms.boost_cooldown,
        )


# --- Master Mobile Suit Admin Models ---


class MasterMobileSuitSpec(SQLModel):
    """マスター機体スペック定義（管理者用）."""

    max_hp: int
    armor: int
    mobility: float
    sensor_range: float = 500.0
    beam_resistance: float = 0.0
    physical_resistance: float = 0.0
    melee_aptitude: float = 1.0
    shooting_aptitude: float = 1.0
    accuracy_bonus: float = 0.0
    evasion_bonus: float = 0.0
    acceleration_bonus: float = 1.0
    turning_bonus: float = 1.0
    weapons: list[Weapon]


class MasterMobileSuitEntry(SQLModel):
    """マスター機体エントリー定義（管理者用レスポンス）."""

    id: str
    name: str
    price: int
    faction: str = ""
    description: str
    specs: MasterMobileSuitSpec


class MasterMobileSuitCreate(SQLModel):
    """マスター機体新規追加リクエスト."""

    id: str
    name: str
    price: int
    faction: str = ""
    description: str
    specs: MasterMobileSuitSpec


class MasterMobileSuitUpdate(SQLModel):
    """マスター機体更新リクエスト."""

    name: str | None = None
    price: int | None = None
    faction: str | None = None
    description: str | None = None
    specs: MasterMobileSuitSpec | None = None


# --- Master Weapon Admin Models ---


class MasterWeaponEntry(SQLModel):
    """マスター武器エントリー定義（管理者用レスポンス）."""

    id: str
    name: str
    price: int
    description: str
    weapon: Weapon


class MasterWeaponCreate(SQLModel):
    """マスター武器新規追加リクエスト."""

    id: str
    name: str
    price: int
    description: str
    weapon: Weapon


class MasterWeaponUpdate(SQLModel):
    """マスター武器更新リクエスト."""

    name: str | None = None
    price: int | None = None
    description: str | None = None
    weapon: Weapon | None = None


# --- Master Data Table Models (DBテーブル定義) ---


class MasterMobileSuit(SQLModel, table=True):
    """マスター機体データ テーブルモデル (DBテーブル)."""

    __tablename__ = "master_mobile_suits"

    id: str = Field(primary_key=True, description="スネークケースID (例: rx_78_2)")
    name: str = Field(description="機体名")
    price: int = Field(description="購入価格")
    faction: str = Field(default="", description="勢力 (FEDERATION/ZEON/空文字=共通)")
    description: str = Field(description="機体説明文")
    specs: dict = Field(
        sa_column=Column(JSON),
        description="機体スペック (MasterMobileSuitSpec の全フィールド)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="作成日時",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="更新日時",
    )


class MasterWeapon(SQLModel, table=True):
    """マスター武器データ テーブルモデル (DBテーブル)."""

    __tablename__ = "master_weapons"

    id: str = Field(primary_key=True, description="スネークケースID (例: zaku_mg)")
    name: str = Field(description="武器名")
    price: int = Field(description="購入価格")
    description: str = Field(description="武器説明文")
    weapon: dict = Field(
        sa_column=Column(JSON),
        description="武器スペック (Weapon モデルの全フィールド)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="作成日時",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="更新日時",
    )


class RetreatPoint(SQLModel):
    """撤退ポイント定義 (Phase 3-3)."""

    position: Vector3  # 撤退ポイントの座標
    radius: float  # 有効半径 (m)。この範囲に入ると離脱扱い
    team_id: str | None = (
        None  # チームIDを指定すると特定チーム専用。None は全チーム共通
    )


class Obstacle(SQLModel):
    """障害物定義 (Phase A — LOS システム)."""

    obstacle_id: str
    position: Vector3  # 球体中心座標（3D: x, y, z）
    radius: float  # 半径（m）。LOS 判定では 3D 球体として使用
    height: float = 0.0  # 高さ（m）。BattleViewer の視覚的高さ表現用


class SpawnZone(SQLModel):
    """スポーン領域定義 (Phase 6-3)."""

    team_id: str  # 使用チームID
    center: Vector3  # 領域中心座標
    radius: float  # 領域半径 (m)。ユニットはこの円内にランダム配置される


class BattleField(SQLModel):
    """バトルフィールド定義 (Phase A — 障害物システム)."""

    obstacles: list[Obstacle] = []  # フィールド上の障害物リスト
    spawn_zones: list[SpawnZone] = []  # チームごとのスポーン領域 (Phase 6-3)
    obstacle_density: str = (
        "MEDIUM"  # 障害物密度: "NONE" / "SPARSE" / "MEDIUM" / "DENSE" (Phase 6-3)
    )


class BattleTeam(SQLModel):
    """バトルチーム定義 (Phase 4-2)."""

    team_id: str
    units: list[str] = []  # ユニットIDリスト
    default_strategy: str = "AGGRESSIVE"  # チームの初期StrategyMode
    retreat_point_ids: list[str] = []


class BattleLog(SQLModel):
    """戦闘ログ1行分."""

    timestamp: float  # バトル内経過時間 (s)
    actor_id: uuid.UUID
    action_type: str  # "MOVE", "ATTACK", "DAMAGE", "DESTROYED", "MISS", "MELEE_COMBO"
    target_id: uuid.UUID | None = None

    damage: int | None = None
    message: str
    position_snapshot: Vector3  # その瞬間の座標（3D再生用）
    chatter: str | None = None  # NPCのセリフ（戦闘中の掛け声など）
    weapon_name: str | None = None  # 使用した武器名（フロントエンド表示用）
    target_max_hp: int | None = None  # ターゲットの最大HP（ダメージ割合計算用）
    skill_activated: bool | None = None  # スキルが命中/回避の判定を変えた場合True
    velocity_snapshot: Vector3 | None = None  # 行動時点の速度ベクトル
    fuzzy_scores: dict | None = None  # ファジィ推論の中間スコア（デバッグ用）
    strategy_mode: str | None = None  # 行動決定時の戦略モード
    team_id: str | None = None  # チームレベルイベント用チームID (Phase 4-2)
    details: dict | None = None  # 追加詳細情報（STRATEGY_CHANGED 等）(Phase 4-2)
    combo_count: int | None = None  # コンボ連続回数 (Phase C — 格闘コンボシステム)
    combo_message: str | None = (
        None  # コンボ演出メッセージ (Phase C — 例: "2Combo 300ダメージ!!")
    )


class BattleLogRecord(SQLModel, table=True):
    """バトルログ専用テーブル (バトルセッション単位で1レコード)."""

    __tablename__ = "battle_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    room_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="battle_rooms.id",
        index=True,
        description="バッチバトル用ルームID",
    )
    mission_id: int | None = Field(
        default=None,
        foreign_key="missions.id",
        index=True,
        description="ソロミッション用ミッションID",
    )
    logs: list[dict] = Field(
        default_factory=list, sa_column=Column(JSON), description="バトルログ全件"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )


class Mission(SQLModel, table=True):
    """ミッション定義 (DBテーブル)."""

    __tablename__ = "missions"

    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="ミッション名")
    difficulty: int = Field(default=1, description="難易度 (1-5)")
    description: str = Field(default="", description="ミッション説明")
    environment: str = Field(
        default="SPACE", description="戦闘環境 (SPACE/GROUND/COLONY/UNDERWATER)"
    )
    special_effects: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="特殊環境効果 (MINOVSKY/GRAVITY_WELL/OBSTACLE)",
    )
    enemy_config: dict = Field(
        default_factory=dict, sa_column=Column(JSON), description="敵機の構成情報"
    )


class BattleResult(SQLModel, table=True):
    """バトル結果 (DBテーブル)."""

    __tablename__ = "battle_results"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str | None = Field(default=None, index=True, description="Clerk User ID")
    mission_id: int | None = Field(
        default=None, foreign_key="missions.id", index=True, description="ミッションID"
    )
    room_id: uuid.UUID | None = Field(
        default=None, foreign_key="battle_rooms.id", index=True, description="ルームID"
    )
    battle_log_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="battle_logs.id",
        index=True,
        description="バトルログ参照ID (FK → battle_logs.id)",
    )
    win_loss: str = Field(description="勝敗 (WIN/LOSE/DRAW)")
    environment: str = Field(
        default="SPACE",
        description="戦闘環境 (SPACE/GROUND/COLONY/UNDERWATER)",
    )
    player_info: dict | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="プレイヤー機体スナップショット",
    )
    enemies_info: list[dict] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="敵機体スナップショットリスト",
    )
    ms_snapshot: dict | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="参加時の機体データスナップショット（エントリー時点）",
    )
    kills: int = Field(default=0, description="撃墜数")
    exp_gained: int = Field(default=0, description="獲得経験値")
    credits_gained: int = Field(default=0, description="獲得クレジット")
    level_before: int = Field(default=0, description="バトル前のレベル")
    level_after: int = Field(default=0, description="バトル後のレベル")
    level_up: bool = Field(default=False, description="レベルアップが発生したかどうか")
    is_read: bool = Field(default=False, index=True, description="既読フラグ")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )


class BattleResultSummary(SQLModel):
    """バトル結果サマリー (logsを含まない軽量レスポンス用)."""

    id: uuid.UUID
    user_id: str | None = None
    mission_id: int | None = None
    room_id: uuid.UUID | None = None
    battle_log_id: uuid.UUID | None = None
    win_loss: str
    environment: str = "SPACE"
    player_info: dict | None = None
    enemies_info: list[dict] | None = None
    ms_snapshot: dict | None = None
    kills: int = 0
    exp_gained: int = 0
    credits_gained: int = 0
    level_before: int = 0
    level_after: int = 0
    level_up: bool = False
    is_read: bool = False
    created_at: datetime


class BattleRoom(SQLModel, table=True):
    """バトルルーム (定期更新バトルの開催回を管理)."""

    __tablename__ = "battle_rooms"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    status: str = Field(
        default="OPEN", index=True, description="ステータス (OPEN/WAITING/COMPLETED)"
    )
    scheduled_at: datetime = Field(description="実行予定時刻")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )


class BattleEntry(SQLModel, table=True):
    """バトルエントリー (ユーザーの参加登録情報)."""

    __tablename__ = "battle_entries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str | None = Field(
        default=None, index=True, description="Clerk User ID (NPC の場合は None)"
    )
    room_id: uuid.UUID = Field(
        foreign_key="battle_rooms.id", index=True, description="バトルルームID"
    )
    mobile_suit_id: uuid.UUID = Field(
        foreign_key="mobile_suits.id", index=True, description="機体ID"
    )
    mobile_suit_snapshot: dict[str, Any] = Field(
        sa_column=Column(JSON),
        description="エントリー時点の機体データのスナップショット",
    )
    is_npc: bool = Field(default=False, index=True, description="NPC（敵機）かどうか")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )


class Pilot(SQLModel, table=True):
    """パイロットデータ (DBテーブル)."""

    __tablename__ = "pilots"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str = Field(
        unique=True,
        index=True,
        description="Clerk User ID (NPC の場合は npc-{uuid} 形式)",
    )
    name: str = Field(description="パイロット名（ユーザー名）")
    faction: str = Field(
        default="",
        description="所属勢力 (FEDERATION/ZEON)",
    )
    background: str = Field(
        default="",
        description="パイロット経歴 (ACADEMY_ELITE/STREET_SURVIVOR/EX_MECHANIC)",
    )
    is_npc: bool = Field(
        default=False, index=True, description="NPC パイロットかどうか"
    )
    npc_personality: str | None = Field(
        default=None, description="NPC の性格 (AGGRESSIVE/CAUTIOUS/SNIPER)"
    )
    level: int = Field(default=1, description="現在のレベル")
    exp: int = Field(default=0, description="累積経験値")
    credits: int = Field(default=1000, description="所持金")
    skill_points: int = Field(default=0, description="未使用のスキルポイント")
    skills: dict[str, int] = Field(
        default_factory=dict, sa_column=Column(JSON), description="習得済みスキル"
    )

    # ステータスポイントシステム
    status_points: int = Field(default=0, description="未使用のステータスポイント")
    dex: int = Field(
        default=0, description="器用 (DEX) - 命中率・距離減衰緩和・被ダメージカット"
    )
    intel: int = Field(default=0, description="直感 (INT) - クリティカル率・回避率")
    ref: int = Field(default=0, description="反応 (REF) - イニシアチブ・機動性乗算")
    tou: int = Field(
        default=0,
        description="耐久 (TOU) - 攻撃ダメージ加算・被クリティカル率低下・防御加算",
    )
    luk: int = Field(default=0, description="幸運 (LUK) - ダメージ乱数偏り・完全回避")
    awq: int = Field(default=0, description="覚醒 (AWQ/NT) - 将来用隠しステータス")

    inventory: dict[str, int] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="所持武器インベントリ（武器ID: 所持数）",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="更新日時"
    )


class Season(SQLModel, table=True):
    """シーズン管理テーブル."""

    __tablename__ = "seasons"

    id: int = Field(default=None, primary_key=True)
    name: str = Field(description="シーズン名 (例: プレシーズン, Season 1)")
    start_date: datetime = Field(description="シーズン開始日時")
    end_date: datetime | None = Field(default=None, description="シーズン終了日時")
    is_active: bool = Field(
        default=True, index=True, description="アクティブシーズンか"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )


class Leaderboard(SQLModel, table=True):
    """ランキングデータテーブル."""

    __tablename__ = "leaderboards"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    season_id: int = Field(
        foreign_key="seasons.id", index=True, description="シーズンID"
    )
    user_id: str = Field(index=True, description="Clerk User ID")
    pilot_name: str = Field(description="パイロット名")
    wins: int = Field(default=0, description="勝利数")
    losses: int = Field(default=0, description="敗北数")
    kills: int = Field(default=0, description="撃墜数")
    credits_earned: int = Field(default=0, description="獲得クレジット")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="更新日時"
    )


class Friendship(SQLModel, table=True):
    """フレンド関係テーブル."""

    __tablename__ = "friendships"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str = Field(index=True, description="リクエスト送信者の Clerk User ID")
    friend_user_id: str = Field(
        index=True, description="リクエスト受信者の Clerk User ID"
    )
    status: str = Field(
        default="PENDING",
        index=True,
        description="ステータス (PENDING/ACCEPTED/BLOCKED)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="更新日時"
    )


class Team(SQLModel, table=True):
    """チームテーブル."""

    __tablename__ = "teams"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_user_id: str = Field(index=True, description="チームオーナーの Clerk User ID")
    name: str = Field(description="チーム名")
    status: str = Field(
        default="FORMING",
        index=True,
        description="ステータス (FORMING/READY/DISBANDED)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="更新日時"
    )


class TeamMember(SQLModel, table=True):
    """チームメンバーテーブル."""

    __tablename__ = "team_members"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    team_id: uuid.UUID = Field(
        foreign_key="teams.id", index=True, description="チームID"
    )
    user_id: str = Field(index=True, description="メンバーの Clerk User ID")
    is_ready: bool = Field(default=False, description="準備完了フラグ")
    joined_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="参加日時"
    )


class PlayerWeapon(SQLModel, table=True):
    """プレイヤー武器インスタンステーブル."""

    __tablename__ = "player_weapons"
    __table_args__ = (
        UniqueConstraint("equipped_ms_id", "equipped_slot", name="uq_equipped_slot"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str = Field(index=True, description="所有者 (Pilot.user_id)")
    master_weapon_id: str = Field(
        index=True, description="weapons.json の id（論理FK）"
    )
    base_snapshot: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="購入時の Weapon スペックスナップショット",
    )
    custom_stats: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="強化・改造による差分（初期値: {}）",
    )
    equipped_ms_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="mobile_suits.id",
        description="装備中の機体ID（未装備は null）",
    )
    equipped_slot: int | None = Field(
        default=None,
        description="装備スロット（0=メイン, 1=サブ, 未装備は null）",
    )
    acquired_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="取得日時"
    )


class PlayerWeaponResponse(SQLModel):
    """プレイヤー武器インスタンスAPIレスポンスモデル."""

    id: uuid.UUID
    master_weapon_id: str
    base_snapshot: dict
    custom_stats: dict
    equipped_ms_id: uuid.UUID | None
    equipped_slot: int | None
    acquired_at: datetime

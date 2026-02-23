import uuid
from datetime import UTC, datetime
from typing import Any

import numpy as np
from pydantic import field_validator
from sqlalchemy import JSON
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
    optimal_range: float = Field(default=300.0, description="最適射程距離")
    decay_rate: float = Field(default=0.05, description="距離による命中率減衰係数")
    max_ammo: int | None = Field(
        default=None, description="最大弾数 (Noneまたは0の場合は無限/EN兵器)"
    )
    en_cost: int = Field(default=0, description="射撃ごとの消費EN (実弾兵器は通常0)")
    cool_down_turn: int = Field(default=0, description="発射後の再使用待機ターン数")


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
    beam_resistance: float = Field(default=0.0, description="対ビーム防御力 (0.0~1.0)")
    physical_resistance: float = Field(
        default=0.0, description="対実弾防御力 (0.0~1.0)"
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


# --- Response Models (APIレスポンス用) ---


class BattleLog(SQLModel):
    """戦闘ログ1行分."""

    turn: int
    actor_id: uuid.UUID
    action_type: str  # "MOVE", "ATTACK", "DAMAGE", "DESTROYED", "MISS"
    target_id: uuid.UUID | None = None

    damage: int | None = None
    message: str
    position_snapshot: Vector3  # その瞬間の座標（3D再生用）
    chatter: str | None = None  # NPCのセリフ（戦闘中の掛け声など）


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
    win_loss: str = Field(description="勝敗 (WIN/LOSE/DRAW)")
    logs: list[BattleLog] = Field(
        default_factory=list, sa_column=Column(JSON), description="バトルログ"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )


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

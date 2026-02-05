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


class Mission(SQLModel, table=True):
    """ミッション定義 (DBテーブル)."""

    __tablename__ = "missions"

    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="ミッション名")
    difficulty: int = Field(default=1, description="難易度 (1-5)")
    description: str = Field(default="", description="ミッション説明")
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
        default="OPEN", index=True, description="ステータス (OPEN/DOING/CLOSED)"
    )
    scheduled_at: datetime = Field(description="実行予定時刻")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )


class BattleEntry(SQLModel, table=True):
    """バトルエントリー (ユーザーの参加登録情報)."""

    __tablename__ = "battle_entries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str = Field(index=True, description="Clerk User ID")
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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )

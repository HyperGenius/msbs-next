# backend/src/domain/models.py

import numpy as np
from pydantic import BaseModel, Field


class Vector3(BaseModel):
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


class Weapon(BaseModel):
    """武装データ."""

    id: str
    name: str
    power: int = Field(..., description="威力")
    range: float = Field(..., description="射程距離")
    accuracy: float = Field(..., description="基本命中率(%)")


class MobileSuit(BaseModel):
    """モビルスーツ本体データ."""

    id: str
    name: str

    # 基本ステータス
    max_hp: int = Field(..., description="最大耐久値")
    current_hp: int = Field(..., description="現在耐久値")
    armor: int = Field(default=0, description="装甲値(ダメージ軽減)")
    mobility: float = Field(default=1.0, description="機動性(回避・移動速度係数)")
    sensor_range: float = Field(default=500.0, description="索敵範囲")

    # 空間座標データ
    position: Vector3 = Field(default_factory=Vector3)
    velocity: Vector3 = Field(default_factory=Vector3, description="現在の移動ベクトル")

    # 装備
    weapons: list[Weapon] = Field(default_factory=list)
    active_weapon_index: int = 0  # 現在選択中の武器

    def get_active_weapon(self) -> Weapon | None:
        """現在選択中の武器を返す."""
        if 0 <= self.active_weapon_index < len(self.weapons):
            return self.weapons[self.active_weapon_index]
        return None


class BattleLog(BaseModel):
    """フロントエンドに返すための戦闘ログ1行分."""

    turn: int
    actor_id: str
    action_type: str  # "MOVE", "ATTACK", "HIT", "MISS"
    target_id: str | None = None
    damage: int | None = None
    message: str
    position_snapshot: Vector3  # その瞬間の座標（3D再生用）


class MobileSuitUpdate(BaseModel):
    """機体更新用のモデル（ガレージ機能で使用）."""

    name: str | None = None
    max_hp: int | None = None
    armor: int | None = None
    mobility: float | None = None

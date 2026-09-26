import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import numpy as np
from pydantic import field_validator
from sqlalchemy import JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
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


# 武器の狙う部位配分（PartName → 配分割合、合計1.0）の初期値。
# 胴体50% / 右腕10% / 左腕10% / 右脚10% / 左脚10% / 頭部10%（Issue #505）。
# PART_HP_RATIOS 等の部位定義（本ファイル下部）より前で参照する必要があるため、
# 部位名は文字列リテラルで直接記述している。
DEFAULT_AIM_DISTRIBUTION: dict[str, float] = {
    "TORSO": 0.5,
    "RIGHT_ARM": 0.1,
    "LEFT_ARM": 0.1,
    "RIGHT_LEG": 0.1,
    "LEFT_LEG": 0.1,
    "HEAD": 0.1,
}


class WeaponSpecBase(SQLModel):
    """武装データのうち id/name を除いたスペック部分.

    マスター武器（MasterWeapon）の weapon(JSON)列はこのクラスの形で保存する。
    id/name は master_weapons テーブルのカラムを正とし、JSON側には持たせない
    （二重管理によるデータ不整合を防ぐため。Issue #400）。
    """

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
    required_beam_generator_lv: int = Field(
        default=0,
        description="装備に必要なビームジェネレータLv (BEAM属性武器のみ有効。機体のビームジェネレータLv以下でのみ装備可能)",
    )
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
    aim_distribution: dict[str, float] = Field(
        default_factory=lambda: dict(DEFAULT_AIM_DISTRIBUTION),
        description=(
            "この武器が狙う部位配分（部位名→配分割合、合計1.0を想定）。"
            "命中部位決定 (app.engine.combat.determine_hit_part) が、角度セクタ別の"
            "露出係数・距離減衰と掛け合わせて命中部位確率を算出する際に使用する"
            "（Issue #505）。ユーザーは PlayerWeapon.custom_stats 経由で上書き可能"
        ),
    )


class MasterWeaponSpec(WeaponSpecBase):
    """マスター武器の weapon(JSON)列に保存するスペック（id/nameを含まない）."""


class Weapon(WeaponSpecBase):
    """武装データ（機体の武器スロット・武器インスタンス等、id/nameが必要な文脈で使用）."""

    id: str
    name: str
    master_weapon_id: str | None = Field(
        default=None,
        description=(
            "元になった武器マスターのID。武器IDには重複回避の接尾辞が付くため、"
            "武器IDからは逆引きできない"
        ),
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


# --- Mobile Suit Parts (部位別HP/装甲, Issue #503) ---

PART_HEAD = "HEAD"
PART_TORSO = "TORSO"
PART_RIGHT_ARM = "RIGHT_ARM"
PART_LEFT_ARM = "LEFT_ARM"
PART_RIGHT_LEG = "RIGHT_LEG"
PART_LEFT_LEG = "LEFT_LEG"

# 部位ごとの最大HP配分比率（合計1.0）。頭部はコクピットではあるが被弾面積が
# 小さいため低め、胴体は中枢機構が集中するため最も高く設定した。戦術設定・
# 角度・距離に基づく本格的な配分は Phase 4 (#TBD) で見直す前提の暫定値
# (Issue #503)。
PART_HP_RATIOS: dict[str, float] = {
    PART_HEAD: 0.10,
    PART_TORSO: 0.30,
    PART_RIGHT_ARM: 0.15,
    PART_LEFT_ARM: 0.15,
    PART_RIGHT_LEG: 0.15,
    PART_LEFT_LEG: 0.15,
}

ALL_PART_NAMES: list[str] = list(PART_HP_RATIOS.keys())


class PartState(SQLModel):
    """部位単体のHP/装甲状態."""

    max_hp: int = Field(description="部位の最大耐久値")
    current_hp: int = Field(description="部位の現在耐久値")
    armor: int = Field(
        default=0,
        description="部位の装甲値。現状は機体全体のarmorをそのまま踏襲する（部位ごとの個別調整はPhase 4で検討）",
    )
    destroyed: bool = Field(default=False, description="破壊済みかどうか")


def build_default_parts(
    max_hp: int, armor: int, missing_parts: list[str] | None = None
) -> dict[str, PartState]:
    """機体全体のmax_hp/armorから部位別の初期状態を組み立てる.

    欠損部位（missing_parts）は結果の辞書に含めない。これにより、命中部位の
    選択プール自体に欠損部位が含まれなくなり、欠損部位への命中判定・
    再配分ロジックが不要になる（Issue #503のヒントに沿った設計）。
    """
    missing = set(missing_parts or [])
    parts: dict[str, PartState] = {}
    for part_name, ratio in PART_HP_RATIOS.items():
        if part_name in missing:
            continue
        part_max_hp = max(1, round(max_hp * ratio))
        parts[part_name] = PartState(
            max_hp=part_max_hp, current_hp=part_max_hp, armor=armor
        )
    return parts


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
    en_recovery: int = Field(default=100, description="毎秒のEN回復量")
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
    weapon_slot_count: int | None = Field(
        default=None,
        ge=1,
        description=(
            "武器スロット数。NULL の場合は機体名で引いた機体マスターの値を使う"
            "（プレイヤー機は NULL。NPC 機・エース機は機体ごとに保持する。Issue #543）"
        ),
    )

    master_mobile_suit_id: str | None = Field(
        default=None,
        description=(
            "元になった機体マスターのID。機体マスターを削除しても機体を残すため FK は張らない"
        ),
    )

    # Part-based HP/Armor (Issue #503, Phase 2 of #501)
    missing_parts: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description=(
            "欠損部位のリスト (例: 脚部のないMS)。ALL_PART_NAMES のいずれかを指定する。"
            "ここに含めた部位は parts に生成されず、命中部位の選択対象からも除外される"
        ),
    )
    parts: dict[str, PartState] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description=(
            "部位別HP/装甲状態 (Issue #503)。既存の max_hp/current_hp/armor は"
            "全体値として引き続き使用し、parts はそれとは別に管理される並行データ。"
            "未設定(空dict)の場合は max_hp/armor/missing_parts から自動生成される"
        ),
    )

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

    def normalize_parts(self) -> None:
        """parts列を PartState 辞書として正規化する (Issue #503).

        - SQLAlchemyのORM読み込み等で parts の値が生のdictのままの場合、
          PartState へ変換する
        - parts が空(未設定)の場合は max_hp/armor/missing_parts から自動生成する

        SQLModel の table=True クラスは `@model_validator(mode="after")` が
        `__init__`/`model_validate` のいずれでも正しく動作しない
        （SQLAlchemyのインスツルメンテーションと衝突するため）制約があり、
        `current_hp` の `field_validator` に残るコメントの通りこのクラスでは
        従来から「アプリケーション側で明示的に呼び出す」方針を取っている。
        機体をバトルエンジンに渡す・APIレスポンスに変換する前に必ず呼び出すこと。
        """
        if self.parts:
            self.parts = {
                name: (PartState(**part) if isinstance(part, dict) else part)
                for name, part in self.parts.items()
            }
        else:
            self.parts = build_default_parts(
                self.max_hp, self.armor, self.missing_parts
            )

    def get_active_weapon(self) -> Weapon | None:
        """現在選択中の武器を返す."""
        if 0 <= self.active_weapon_index < len(self.weapons):
            return self.weapons[self.active_weapon_index]
        return None


def resolve_weapon_slot_count(
    ms: "MobileSuit", master_weapon_slot_count: int | None = None
) -> int:
    """機体の武器スロット数を解決する.

    機体自身の値 → 機体マスターの値 → 装備数と MAX_WEAPON_SLOTS の大きい方、の順に使う。

    Args:
        ms: 対象の機体
        master_weapon_slot_count: 機体名で引いた機体マスターの武器スロット数。
            引けなかった場合は None
    """
    from app.engine.constants import MAX_WEAPON_SLOTS

    if ms.weapon_slot_count is not None:
        return ms.weapon_slot_count
    if master_weapon_slot_count is not None:
        return master_weapon_slot_count
    return max(len(ms.weapons or []), MAX_WEAPON_SLOTS)


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
    missing_parts: list[str] = []
    parts: dict[str, "PartState"] = {}
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

    # 武器スロット数 (Issue #392, #543)。解決順は resolve_weapon_slot_count() を参照
    weapon_slot_count: int = 1
    # マスター機体由来のビームジェネレータLv (Issue #392)
    beam_generator_lv: int = 0

    @classmethod
    def from_mobile_suit(
        cls,
        ms: "MobileSuit",
        weapon_slot_count: int | None = None,
        beam_generator_lv: int | None = None,
    ) -> "MobileSuitResponse":
        """MobileSuitインスタンスからMobileSuitResponseを生成する.

        Args:
            ms: 変換元の機体データ
            weapon_slot_count: マスター機体から引いた武器スロット数。
                呼び出し側で解決できない場合は None を渡す
                （解決順は resolve_weapon_slot_count() を参照）。
            beam_generator_lv: マスター機体から引いたビームジェネレータLv。
                呼び出し側で解決できない場合は None を渡す（0 にフォールバックする）。
        """
        from app.core.rank_utils import get_rank

        resolved_weapon_slot_count = resolve_weapon_slot_count(ms, weapon_slot_count)
        resolved_beam_generator_lv = (
            beam_generator_lv if beam_generator_lv is not None else 0
        )

        weapons_response = []
        for w in ms.weapons:
            if isinstance(w, dict):
                weapon_obj = Weapon(**w)
            else:
                weapon_obj = w
            weapons_response.append(WeaponResponse.from_weapon(weapon_obj))

        ms.normalize_parts()

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
            missing_parts=ms.missing_parts,
            parts=ms.parts,
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
            weapon_slot_count=resolved_weapon_slot_count,
            beam_generator_lv=resolved_beam_generator_lv,
        )


# --- Master Blueprint Admin Models ---


class MasterBlueprintSettings(SQLModel):
    """機体・武器マスターの設計図設定（管理者用）."""

    is_standard_issue: bool = Field(
        default=True, description="標準配備品か。true なら設計図なしで購入できる"
    )
    duplicate_credit_value: int = Field(
        ge=0, description="入手済みの設計図を再入手したときに付与するクレジット"
    )


class MasterBlueprintSettingsInput(SQLModel):
    """機体・武器マスターの設計図設定の保存リクエスト（管理者用）.

    未指定の項目は変更しない。設計図マスターを新規作成するときは初期値になる。
    """

    is_standard_issue: bool | None = None
    duplicate_credit_value: int | None = Field(default=None, ge=0)


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
    missing_parts: list[str] = Field(
        default_factory=list,
        description="欠損部位のリスト (ALL_PART_NAMES のいずれか。例: 脚部のないMSは [RIGHT_LEG, LEFT_LEG])",
    )


class MasterMobileSuitEntry(SQLModel):
    """マスター機体エントリー定義（管理者用レスポンス）."""

    id: str
    name: str
    name_ja: str = ""
    model_number: str = ""
    price: int
    faction: str = ""
    description: str
    weapon_slot_count: int = 1
    beam_generator_lv: int = 0
    flavor_text: str | None = None
    specs: MasterMobileSuitSpec
    blueprint: MasterBlueprintSettings


class MasterMobileSuitCreate(SQLModel):
    """マスター機体新規追加リクエスト."""

    id: str
    name: str
    name_ja: str = ""
    model_number: str = ""
    price: int
    faction: str = ""
    description: str
    weapon_slot_count: int = Field(default=1, ge=1)
    beam_generator_lv: int = Field(default=0, ge=0)
    flavor_text: str | None = None
    specs: MasterMobileSuitSpec
    blueprint: MasterBlueprintSettingsInput | None = None


class MasterMobileSuitUpdate(SQLModel):
    """マスター機体更新リクエスト."""

    name: str | None = None
    name_ja: str | None = None
    model_number: str | None = None
    price: int | None = None
    faction: str | None = None
    description: str | None = None
    weapon_slot_count: int | None = Field(default=None, ge=1)
    beam_generator_lv: int | None = Field(default=None, ge=0)
    flavor_text: str | None = None
    specs: MasterMobileSuitSpec | None = None
    blueprint: MasterBlueprintSettingsInput | None = None


# --- Master Weapon Admin Models ---


class MasterWeaponEntry(SQLModel):
    """マスター武器エントリー定義（管理者用レスポンス）."""

    id: str
    name: str
    price: int
    description: str
    flavor_text: str | None = None
    weapon: MasterWeaponSpec
    blueprint: MasterBlueprintSettings


class MasterWeaponCreate(SQLModel):
    """マスター武器新規追加リクエスト."""

    id: str
    name: str
    price: int
    description: str
    flavor_text: str | None = None
    weapon: MasterWeaponSpec
    blueprint: MasterBlueprintSettingsInput | None = None


class MasterWeaponUpdate(SQLModel):
    """マスター武器更新リクエスト."""

    name: str | None = None
    price: int | None = None
    description: str | None = None
    flavor_text: str | None = None
    weapon: MasterWeaponSpec | None = None
    blueprint: MasterBlueprintSettingsInput | None = None


# --- Combat Simulation Models (管理画面用 1対1 攻撃シミュレーション, Issue #381) ---


class PilotStatsInput(SQLModel):
    """シミュレーション用パイロットステータス入力."""

    sht: int = Field(default=0, description="射撃精度 (SHT)")
    mel: int = Field(default=0, description="格闘技巧 (MEL)")
    intel: int = Field(default=0, description="直感 (INT)")
    ref: int = Field(default=0, description="反応 (REF)")
    tou: int = Field(default=0, description="耐久 (TOU)")
    luk: int = Field(default=0, description="幸運 (LUK)")


class CombatSimulationRequest(SQLModel):
    """1対1 攻撃シミュレーションリクエスト."""

    attacker_spec: MasterMobileSuitSpec
    attacker_weapon_id: str = Field(description="attacker_spec.weapons 内の武器ID")
    attacker_pilot: PilotStatsInput = Field(default_factory=PilotStatsInput)
    defender_spec: MasterMobileSuitSpec
    defender_pilot: PilotStatsInput = Field(default_factory=PilotStatsInput)
    distance: float | None = Field(
        default=None, description="攻撃距離(m)。省略時は武器の optimal_range"
    )
    attack_sector: str = Field(
        default="FRONT_SIDE", description="攻撃セクタ (FRONT/FRONT_SIDE/REAR_SIDE/REAR)"
    )
    trials: int | None = Field(
        default=None,
        ge=1,
        le=5000,
        description="モンテカルロ試行回数（省略時は理論値のみ）",
    )


class MonteCarloCombatStats(SQLModel):
    """モンテカルロ試行の実測統計."""

    trials: int
    actual_hit_rate: float
    actual_crit_rate: float
    avg_damage: float
    min_damage: int
    max_damage: int
    perfect_evade_rate: float


class CombatSimulationResponse(SQLModel):
    """1対1 攻撃シミュレーションレスポンス."""

    hit_chance: float
    crit_chance: float
    base_damage: int
    crit_damage: int
    resistance_applied_damage: int
    monte_carlo: MonteCarloCombatStats | None = None


# --- Master Data Table Models (DBテーブル定義) ---


class MasterMobileSuit(SQLModel, table=True):
    """マスター機体データ テーブルモデル (DBテーブル)."""

    __tablename__ = "master_mobile_suits"

    id: str = Field(primary_key=True, description="スネークケースID (例: rx_78_2)")
    name: str = Field(description="機体名")
    name_ja: str = Field(default="", description="日本語表示名")
    model_number: str = Field(default="", description="型番 (例: RGM-79)")
    price: int = Field(description="購入価格")
    faction: str = Field(default="", description="勢力 (FEDERATION/ZEON/空文字=共通)")
    description: str = Field(description="機体説明文")
    weapon_slot_count: int = Field(default=1, description="武器スロット数 (1以上)")
    beam_generator_lv: int = Field(
        default=0, description="ビームジェネレータLv (0以上)"
    )
    flavor_text: str | None = Field(
        default=None, description="購入画面用フレーバーテキスト（1〜2行程度）"
    )
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
    flavor_text: str | None = Field(
        default=None, description="購入画面用フレーバーテキスト（1〜2行程度）"
    )
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


class AcePilot(SQLModel, table=True):
    """エースパイロットのマスターデータ テーブルモデル (DBテーブル).

    マッチング時にこの雛形から is_ace=True の MobileSuit が都度生成される。
    生成済み MobileSuit は ace_id 文字列で参照するのみ（FKなし）。
    """

    __tablename__ = "ace_pilots"

    id: str = Field(
        primary_key=True, description="スネークケースID (例: ace_char_aznable)"
    )
    name: str = Field(description="二つ名 (例: 赤い彗星)")
    pilot_name: str = Field(description="パイロット名 (例: Char Aznable)")
    description: str = Field(default="", description="説明文")
    personality: str = Field(description="性格タイプ (AGGRESSIVE/CAUTIOUS/SNIPER)")
    mobile_suit: dict = Field(
        sa_column=Column(JSON),
        description="搭乗機体スペック (AcePilotMobileSuitSpec の全フィールド)",
    )
    bounty_exp: int = Field(default=0, description="撃破時のボーナス経験値")
    bounty_credits: int = Field(default=0, description="撃破時のボーナスクレジット")
    stats: dict = Field(
        sa_column=Column(JSON),
        description="パイロットステータス (sht/mel/intel/ref/tou/luk)",
    )
    skills: dict = Field(
        sa_column=Column(JSON),
        description="スキルレベル (スキルID→レベル。例: {'flanking': 3})",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="作成日時",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="更新日時",
    )


# --- Ace Pilot Admin Models ---


class AcePilotMobileSuitSpec(SQLModel):
    """エースパイロットの搭乗機体スペック（ace_pilots.mobile_suit 列の形式）."""

    name: str
    max_hp: int = Field(gt=0)
    armor: int = Field(ge=0)
    mobility: float = Field(gt=0)
    sensor_range: float = 500.0
    beam_resistance: float = Field(default=0.0, ge=0, le=1)
    physical_resistance: float = Field(default=0.0, ge=0, le=1)
    max_en: int = Field(default=1000, ge=0)
    en_recovery: int = Field(default=100, ge=0)
    weapon_slot_count: int | None = Field(
        default=None,
        ge=1,
        description="武器スロット数。未設定の場合は装備数と MAX_WEAPON_SLOTS の大きい方",
    )
    master_mobile_suit_id: str | None = Field(
        default=None, description="機体マスターから取り込んだ場合の機体マスターID"
    )
    weapons: list[Weapon]
    tactics: dict = Field(
        default_factory=lambda: {"priority": "CLOSEST", "range": "BALANCED"},
        description="戦術設定 (priority / range)",
    )
    missing_parts: list[str] = Field(
        default_factory=list,
        description="欠損部位のリスト (ALL_PART_NAMES のいずれか)",
    )


class AcePilotEntry(SQLModel):
    """エースパイロットエントリー定義（管理者用レスポンス）."""

    id: str
    name: str
    pilot_name: str
    description: str = ""
    personality: str
    mobile_suit: AcePilotMobileSuitSpec
    bounty_exp: int = 0
    bounty_credits: int = 0
    stats: PilotStatsInput
    skills: dict[str, int] = Field(default_factory=dict)


class AcePilotCreate(SQLModel):
    """エースパイロット新規追加リクエスト."""

    id: str
    name: str
    pilot_name: str
    description: str = ""
    personality: str
    mobile_suit: AcePilotMobileSuitSpec
    bounty_exp: int = Field(default=0, ge=0)
    bounty_credits: int = Field(default=0, ge=0)
    stats: PilotStatsInput
    skills: dict[str, int] = Field(default_factory=dict)


class AcePilotUpdate(SQLModel):
    """エースパイロット更新リクエスト."""

    name: str | None = None
    pilot_name: str | None = None
    description: str | None = None
    personality: str | None = None
    mobile_suit: AcePilotMobileSuitSpec | None = None
    bounty_exp: int | None = Field(default=None, ge=0)
    bounty_credits: int | None = Field(default=None, ge=0)
    stats: PilotStatsInput | None = None
    skills: dict[str, int] | None = None


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
    heading: float | None = (
        None  # 行動時点の胴体向き (度数法, XZ平面) (BattleViewer可視化用)
    )
    attack_sector: str | None = (
        None  # "FRONT" / "FRONT_SIDE" / "REAR_SIDE" / "REAR" (Phase E-3)
    )
    weapon_id: str | None = None  # 使用した武器のID（フロントエンドの武器特定用）
    is_crit: bool = False  # クリティカルヒット判定（構造化フラグ）
    hit_part: str | None = (
        None  # 命中部位 (HEAD/TORSO/RIGHT_ARM/LEFT_ARM/RIGHT_LEG/LEFT_LEG) (Issue #503)
    )
    weapon_slot_role: str | None = (
        None  # 使用武器のスロット部位ロール (RIGHT_ARM/LEFT_ARM/RACK) (Issue #504)
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
        default_factory=list,
        sa_column=Column(JSON().with_variant(JSONB, "postgresql")),
        description="バトルログ全件（gcs_path設定後は空リストになる。Issue #493）",
    )
    gcs_path: str | None = Field(
        default=None,
        description=(
            "オフロード済みログのCloud Storageオブジェクトパス（バケット内相対パス、"
            "gs://は含まない）。設定済みの場合、配信は logs 列ではなくこちらを優先する"
            "（Issue #493、Neon Network Transfer対策）。オフロード未完了・失敗時はNULLの"
            "ままとなり、その間は logs 列からの配信にフォールバックする"
        ),
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


class LootKind(StrEnum):
    """戦利品の種別."""

    BLUEPRINT = "BLUEPRINT"


class LootItem(SQLModel):
    """バトルで得た戦利品."""

    kind: str = Field(description="戦利品の種別 (LootKind)")
    blueprint_id: str
    target_type: str
    target_id: str
    is_new: bool = Field(description="未所持の設計図を入手したか")
    credits_awarded: int = Field(
        description="所持済みの設計図を換金したクレジット。未所持なら 0"
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
    obstacles_info: list[dict] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="フィールド障害物スナップショットリスト",
    )
    ms_snapshot: dict | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="参加時の機体データスナップショット（エントリー時点）",
    )
    map_bounds: list[float] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="フィールド範囲 [min, max] (m)。BattleViewerの背景グリッド整列用 (Issue #436)",
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

    # --- 戦闘ダイジェスト (Battle History 一覧の物語化, Issue #415) ---
    # 既存レコードとの互換のためすべて nullable。バトル終了時に一度だけ計算して保存する。
    player_survived: bool | None = Field(default=None, description="生還したかどうか")
    min_hp_percent: int | None = Field(
        default=None, description="バトル中の最低到達HP割合 (%)"
    )
    damage_severity: str | None = Field(
        default=None, description="被弾ランク (無傷/軽微/中破/大破/撃墜)"
    )
    damage_taken_count: int | None = Field(default=None, description="被弾回数")
    max_hit_damage: int | None = Field(default=None, description="与ダメージ最大一撃")
    dodge_count: int | None = Field(default=None, description="回避回数")
    attacks_received_count: int | None = Field(
        default=None, description="被攻撃回数（被弾+回避）"
    )
    pilot_ms_name: str | None = Field(default=None, description="搭乗機体名")
    digest_tag: str | None = Field(
        default=None, description="ダイジェストタグ (辛勝/完封/殲滅 等)"
    )
    digest_text: str | None = Field(default=None, description="一言ログ（生成済み）")

    # --- 部位別命中集計 (Issue #504) ---
    part_hit_summary: dict | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="部位別の被弾/命中集計（taken: 被弾部位別, dealt: 使用武器スロット別）",
    )

    loot: list[dict] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="戦利品の一覧 (LootItem)。ドロップなしは空配列、導入前のバトルは null",
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
    obstacles_info: list[dict] | None = None
    ms_snapshot: dict | None = None
    map_bounds: list[float] | None = None
    kills: int = 0
    exp_gained: int = 0
    credits_gained: int = 0
    level_before: int = 0
    level_after: int = 0
    level_up: bool = False
    is_read: bool = False
    created_at: datetime

    # --- 戦闘ダイジェスト (Issue #415) ---
    player_survived: bool | None = None
    min_hp_percent: int | None = None
    damage_severity: str | None = None
    damage_taken_count: int | None = None
    max_hit_damage: int | None = None
    dodge_count: int | None = None
    attacks_received_count: int | None = None
    pilot_ms_name: str | None = None
    digest_tag: str | None = None
    digest_text: str | None = None
    part_hit_summary: dict | None = None
    loot: list[LootItem] | None = None


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
    sht: int = Field(
        default=0, description="射撃精度 (SHT) - 射撃攻撃力補正率（シグモイド入力）"
    )
    mel: int = Field(
        default=0, description="格闘技巧 (MEL) - 格闘攻撃力補正率（シグモイド入力）"
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
    active_mobile_suit_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="mobile_suits.id",
        ondelete="SET NULL",
        description=(
            "NPC の出撃機体ID。プレイヤーは battle_entries.mobile_suit_id で"
            "出撃機体を指定するため NULL のまま"
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="更新日時"
    )


# --- NPC Admin Models ---


class NpcMobileSuitEntry(SQLModel):
    """NPC所有機体エントリー定義（管理者用レスポンス）."""

    id: uuid.UUID
    name: str
    max_hp: int
    current_hp: int
    armor: int
    mobility: float
    sensor_range: float = 500.0
    beam_resistance: float = 0.0
    physical_resistance: float = 0.0
    max_en: int = 1000
    en_recovery: int = 100
    melee_aptitude: float = 1.0
    shooting_aptitude: float = 1.0
    accuracy_bonus: float = 0.0
    evasion_bonus: float = 0.0
    acceleration_bonus: float = 1.0
    turning_bonus: float = 1.0
    tactics: dict = Field(default_factory=dict)
    missing_parts: list[str] = Field(default_factory=list)
    weapons: list[Weapon] = Field(default_factory=list)
    weapon_slot_count: int = 1
    master_mobile_suit_id: str | None = None
    personality: str | None = None
    is_ace: bool = False
    ace_id: str | None = None
    pilot_name: str | None = None
    bounty_exp: int = 0
    bounty_credits: int = 0


class NpcMobileSuitUpdate(SQLModel):
    """NPC所有機体の更新リクエスト.

    プレイヤー向けの MobileSuitUpdate とは分ける。
    武装を書き換えられるのは管理者だけにするため。
    """

    name: str | None = Field(default=None, min_length=1)
    max_hp: int | None = Field(default=None, gt=0)
    armor: int | None = Field(default=None, ge=0)
    mobility: float | None = Field(default=None, gt=0)
    sensor_range: float | None = Field(default=None, gt=0)
    beam_resistance: float | None = Field(default=None, ge=0, le=1)
    physical_resistance: float | None = Field(default=None, ge=0, le=1)
    max_en: int | None = Field(default=None, ge=0)
    en_recovery: int | None = Field(default=None, ge=0)
    melee_aptitude: float | None = Field(default=None, gt=0)
    shooting_aptitude: float | None = Field(default=None, gt=0)
    accuracy_bonus: float | None = None
    evasion_bonus: float | None = None
    acceleration_bonus: float | None = Field(default=None, gt=0)
    turning_bonus: float | None = Field(default=None, gt=0)
    tactics: dict | None = None
    missing_parts: list[str] | None = None
    weapons: list[Weapon] | None = None
    weapon_slot_count: int | None = Field(default=None, ge=1)


class NpcMobileSuitCreate(SQLModel):
    """NPC機体の追加リクエスト（機体マスターから生成する）."""

    master_mobile_suit_id: str


class NpcPilotEntry(SQLModel):
    """NPCパイロットエントリー定義（管理者用レスポンス）."""

    id: uuid.UUID
    user_id: str
    name: str
    npc_personality: str | None = None
    is_ace: bool = False
    level: int
    exp: int
    credits: int
    skill_points: int
    status_points: int
    sht: int
    mel: int
    intel: int
    ref: int
    tou: int
    luk: int
    awq: int
    mobile_suit_count: int = 0
    active_mobile_suit_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class NpcPilotDetail(NpcPilotEntry):
    """NPCパイロット詳細定義（管理者用レスポンス、所有機体一覧付き）."""

    mobile_suits: list[NpcMobileSuitEntry] = Field(default_factory=list)


class NpcPilotUpdate(SQLModel):
    """NPCパイロット更新リクエスト."""

    npc_personality: str | None = None
    level: int | None = Field(default=None, ge=1)
    exp: int | None = Field(default=None, ge=0)
    credits: int | None = Field(default=None, ge=0)
    skill_points: int | None = Field(default=None, ge=0)
    status_points: int | None = Field(default=None, ge=0)
    sht: int | None = Field(default=None, ge=0)
    mel: int | None = Field(default=None, ge=0)
    intel: int | None = Field(default=None, ge=0)
    ref: int | None = Field(default=None, ge=0)
    tou: int | None = Field(default=None, ge=0)
    luk: int | None = Field(default=None, ge=0)
    awq: int | None = Field(default=None, ge=0)
    active_mobile_suit_id: uuid.UUID | None = None


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


class WeaponCustomStats(SQLModel):
    """武器インスタンスの強化・改造差分スキーマ (Issue #404).

    `PlayerWeapon.custom_stats` (自由形式JSON) に実際に書き込まれる想定のキーを
    型として明示する。キー欠損時はデフォルト0/未変更として扱う（後方互換）。
    `weapon_power`（機体側のパイロット/システム補正、`EngineeringService` 管理）とは
    別軸の、武器インスタンス単位の改造差分。
    """

    power_bonus: int = Field(default=0, description="威力への加算値")
    accuracy_bonus: float = Field(default=0.0, description="命中率への加算値(%)")
    upgrade_level: int = Field(
        default=0, description="改造レベル（将来の改造ツリー・表示用）"
    )
    aim_distribution: dict[str, float] | None = Field(
        default=None,
        description=(
            "狙う部位配分のユーザー設定上書き（Issue #505）。未設定(None)の場合は "
            "base_snapshot 側の aim_distribution（マスター武器の初期値）を使用する。"
            "改造費用を伴う強化とは異なり、ユーザーが無償で変更できる戦術設定"
        ),
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
        description=(
            "強化・改造による差分（初期値: {}）。"
            "スキーマは WeaponCustomStats を参照（power_bonus / accuracy_bonus / "
            "upgrade_level）。実効スペックは WeaponService.apply_effective_spec で "
            "base_snapshot とマージして計算する"
        ),
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


# --- Blueprint Models ---


class BlueprintTargetType(StrEnum):
    """設計図の対象マスターの種別."""

    MOBILE_SUIT = "MOBILE_SUIT"
    WEAPON = "WEAPON"


class BlueprintSource(StrEnum):
    """設計図の入手経路."""

    MIGRATION = "MIGRATION"
    DROP = "DROP"


class MasterBlueprint(SQLModel, table=True):
    """設計図マスター (DBテーブル).

    機体マスター・武器マスターの各アイテムと1対1で対応する。
    """

    __tablename__ = "master_blueprints"
    __table_args__ = (
        UniqueConstraint("target_type", "target_id", name="uq_master_blueprint_target"),
    )

    id: str = Field(
        primary_key=True,
        description="設計図ID。target_type と target_id から決まる (例: mobile_suit:rx_78_2)",
    )
    target_type: str = Field(description="対象の種別 (BlueprintTargetType)")
    target_id: str = Field(
        index=True, description="対象の機体マスターID・武器マスターID"
    )
    is_standard_issue: bool = Field(
        default=True, description="標準配備品か。true なら設計図なしで購入できる"
    )
    duplicate_credit_value: int = Field(
        default=0,
        ge=0,
        description="入手済みの設計図を再入手したときに付与するクレジット",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="更新日時"
    )


class PlayerBlueprint(SQLModel, table=True):
    """プレイヤーの所持設計図 (DBテーブル)."""

    __tablename__ = "player_blueprints"
    __table_args__ = (
        UniqueConstraint("user_id", "blueprint_id", name="uq_player_blueprint"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str = Field(index=True, description="所有者 (Pilot.user_id)")
    blueprint_id: str = Field(
        foreign_key="master_blueprints.id", index=True, description="設計図ID"
    )
    source: str = Field(description="入手経路 (BlueprintSource)")
    source_battle_id: uuid.UUID | None = Field(
        default=None,
        description="入手元のバトル (BattleResult.id)。バトル以外で入手した場合は null",
    )
    acquired_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="入手日時"
    )


class PlayerBlueprintResponse(SQLModel):
    """所持設計図APIレスポンスモデル."""

    blueprint_id: str
    target_type: str
    target_id: str
    source: str
    source_battle_id: uuid.UUID | None
    acquired_at: datetime


# --- Drop Table Models ---


class DropScopeType(StrEnum):
    """ドロップテーブルの適用範囲の種別."""

    MISSION = "MISSION"
    BATCH = "BATCH"


class DropTable(SQLModel, table=True):
    """ドロップテーブル (DBテーブル)."""

    __tablename__ = "drop_tables"
    __table_args__ = (
        UniqueConstraint("scope_type", "scope_key", name="uq_drop_table_scope"),
    )

    id: int = Field(default=None, primary_key=True)
    scope_type: str = Field(description="適用範囲の種別 (DropScopeType)")
    scope_key: str = Field(
        description="適用範囲のキー。MISSION は missions.id の文字列、BATCH は default"
    )
    name: str = Field(description="管理用の名前")
    drop_rate: float = Field(
        ge=0, le=1, description="1回のバトルで何かがドロップする確率"
    )
    win_rate_multiplier: float = Field(
        default=1.0,
        ge=1,
        description="勝利時に drop_rate に掛ける倍率。掛けた結果は1を上限とする",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="作成日時"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="更新日時"
    )


class DropTableEntry(SQLModel, table=True):
    """ドロップテーブルに含まれる設計図 (DBテーブル)."""

    __tablename__ = "drop_table_entries"
    __table_args__ = (
        UniqueConstraint(
            "drop_table_id", "blueprint_id", name="uq_drop_table_entry_blueprint"
        ),
    )

    id: int = Field(default=None, primary_key=True)
    drop_table_id: int = Field(foreign_key="drop_tables.id", index=True)
    blueprint_id: str = Field(
        foreign_key="master_blueprints.id", index=True, description="設計図ID"
    )
    weight: int = Field(default=1, ge=1, description="抽選の重み")
    requires_win: bool = Field(
        default=False, description="true なら勝利時だけ抽選対象になる"
    )


class DropTableEntryInput(SQLModel):
    """ドロップテーブルのエントリーの保存リクエスト（管理者用）."""

    blueprint_id: str = Field(min_length=1)
    weight: int = Field(ge=1, description="抽選の重み")
    requires_win: bool = Field(
        default=False, description="true なら勝利時だけ抽選対象になる"
    )


class DropTableUpdate(SQLModel):
    """ドロップテーブルの保存リクエスト（管理者用）.

    エントリーは `entries` の内容で置き換える。
    """

    name: str = Field(min_length=1)
    drop_rate: float = Field(ge=0, le=1)
    win_rate_multiplier: float = Field(ge=1)
    entries: list[DropTableEntryInput] = Field(default_factory=list)


class BlueprintTargetSummary(SQLModel):
    """設計図と、その対象の機体・武器の表示情報（管理者用）."""

    blueprint_id: str
    target_type: str = Field(description="対象の種別 (BlueprintTargetType)")
    target_id: str
    target_name: str = Field(
        description="対象の表示名。対象のマスターが無ければ target_id"
    )
    faction: str = Field(default="", description="機体の勢力。武器と共通機体は空文字")
    is_standard_issue: bool


class DropTableEntryDetail(BlueprintTargetSummary):
    """ドロップテーブルのエントリー（管理者用）."""

    weight: int
    requires_win: bool


class DropTableDetail(SQLModel):
    """ドロップテーブルの設定とエントリー（管理者用）."""

    id: int | None = Field(description="テーブルID。テーブルが未作成なら null")
    name: str
    drop_rate: float
    win_rate_multiplier: float
    entries: list[DropTableEntryDetail]
    unobtainable_blueprints: list[BlueprintTargetSummary] = Field(
        description="要設計図なのに、このテーブルに入っていない設計図"
    )

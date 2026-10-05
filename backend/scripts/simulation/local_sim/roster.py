"""ローカルシミュレーションのロスター（参加機体と戦域条件）の JSON スキーマ.

このモジュールは `app` を import しない。`app.db` は import 時に接続先を決めるため、
接続先を差し替える前に読み込まれても影響が出ないようにしている。
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

ROSTER_SCHEMA_VERSION = 1

# backend/scripts/simulation/local_sim/roster.py から見たリポジトリのルート。
REPO_ROOT = Path(__file__).resolve().parents[4]
LOCAL_SIM_DIR = REPO_ROOT / "battle_logs" / "local_sim"
ROSTERS_DIR = LOCAL_SIM_DIR / "rosters"

ROSTER_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")

RosterSourceKind = Literal["mobile_suit", "pilot", "npc", "generated_npc", "ace"]


class RosterSource(BaseModel):
    """参加機体の取得元."""

    kind: RosterSourceKind = Field(
        description=(
            "mobile_suit: --ms で指定した機体 / pilot: --pilot のパイロットの出撃機体 / "
            "npc: 本番の永続化NPC / generated_npc: 生成したNPC / ace: エースパイロット"
        )
    )
    mobile_suit_id: str = Field(
        description="機体ID。生成したNPC・エースは本番DBに無いID"
    )
    pilot_id: str | None = Field(default=None, description="パイロットID（pilots.id）")
    pilot_name: str | None = None
    ace_id: str | None = None


class RosterEntry(BaseModel):
    """参加機体1機分."""

    source: RosterSource
    is_npc: bool
    snapshot: dict[str, Any] = Field(
        description=(
            "本番の BattleEntry.mobile_suit_snapshot と同じ形式。"
            "team_id が同じ機体は味方になる。null の機体は個人戦扱い"
        )
    )


class RosterEnvironmentProfile(BaseModel):
    """環境タイプの効果（`EnvironmentProfile` と同じ項目）."""

    environment_id: str
    sensor_range_multiplier: float
    ranged_accuracy_penalty: float
    ranged_penalty_ref_distance: float
    default_obstacle_density: str
    default_terrain_grade: str


class RosterConditions(BaseModel):
    """戦闘に適用する戦域の条件（`BattleConditions` と同じ項目）."""

    theater_id: str | None = None
    environment: str = "SPACE"
    environment_profile: RosterEnvironmentProfile | None = None
    theater_name: str | None = Field(
        default=None,
        description="戦域の表示名。null なら結果には戦域IDを表示名として残す",
    )
    environment_name: str | None = Field(default=None, description="環境タイプの表示名")
    viewer_preset: str | None = Field(
        default=None, description="バトルビューアの背景プリセット"
    )
    minovsky_density: float = Field(default=0.0, ge=0.0, le=1.0)
    battlefield: dict[str, Any] = Field(
        default_factory=dict, description="BattleField の model_dump()"
    )


class Roster(BaseModel):
    """ローカルシミュレーションに参加させる機体と戦域条件."""

    schema_version: int = ROSTER_SCHEMA_VERSION
    name: str
    fetched_at: datetime
    conditions: RosterConditions
    entries: list[RosterEntry]
    ace_pilots: list[dict[str, Any]] = Field(
        default_factory=list,
        description="参加エースの ace_pilots マスター（created_at / updated_at を除く）",
    )


def validate_roster_name(name: str) -> str:
    """ロスター名がファイル名に使える文字だけか確かめる.

    Raises:
        ValueError: 英数字で始まらない、または英数字と `_.-` 以外を含む場合
    """
    if not ROSTER_NAME_PATTERN.fullmatch(name):
        raise ValueError(
            f"ロスター名 '{name}' は使えません。英数字で始め、英数字と _ . - だけを使ってください。"
        )
    return name


def roster_path(name: str, rosters_dir: Path = ROSTERS_DIR) -> Path:
    """ロスター名から保存先のパスを返す."""
    return rosters_dir / f"{validate_roster_name(name)}.json"


def save_roster(
    roster: Roster, rosters_dir: Path = ROSTERS_DIR, overwrite: bool = False
) -> Path:
    """ロスターを整形した JSON で保存する.

    Raises:
        FileExistsError: 同名のロスターがあり、overwrite が False の場合
    """
    path = roster_path(roster.name, rosters_dir)
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"ロスター {path} は既にあります。上書きするなら --force を付けてください。"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        roster.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return path


def resolve_roster_path(name_or_path: str, rosters_dir: Path = ROSTERS_DIR) -> Path:
    """ロスター名またはファイルパス（`.json` で終わるもの）からパスを返す."""
    path = Path(name_or_path)
    if path.suffix != ".json":
        path = roster_path(name_or_path, rosters_dir)
    return path


def load_roster(name_or_path: str, rosters_dir: Path = ROSTERS_DIR) -> Roster:
    """ロスター名またはファイルパスからロスターを読む.

    Raises:
        FileNotFoundError: ロスターが無い場合
    """
    path = resolve_roster_path(name_or_path, rosters_dir)
    if not path.is_file():
        raise FileNotFoundError(f"ロスター {path} が見つかりません。")
    return Roster.model_validate_json(path.read_text(encoding="utf-8"))

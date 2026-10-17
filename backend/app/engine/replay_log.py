# backend/app/engine/replay_log.py
"""エンジンのログ（`BattleLog`）から、プレイヤーに配信する再生用のログを作る.

再生用のログは、先頭のヘッダー行と、描画に使う項目だけを持つ行からなる。
変換は DB・GCS に触れない純粋関数で、同じ入力なら同じ出力になる。
スキーマは `docs/features/battle-log-feature.md` の「配信用ログ（replay）」に書いている。
"""

import uuid
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic_core import to_jsonable_python

from app.models.models import BattleLog, Vector3

# 項目の意味・省き方を変えたら上げる。フロントはこの値で読み方を分ける。
REPLAY_LOG_VERSION = 1

# 描画に使わない行。
_DROPPED_ACTIONS = frozenset({"AI_DECISION"})
# 構造化された項目から文を作れるため、message を省く行。
_MESSAGE_DROPPED_ACTIONS = frozenset({"MOVE", "WAIT", "TARGET_SELECTION"})
# 座標・速度は 0.1m（0.1m/s）、向きは 0.1 度に丸める。
_VECTOR_DIGITS = 1
_HEADING_DIGITS = 1
# ステップ幅より細かい桁で丸める。ステップ幅を 0.01 秒まで縮めても時刻が重ならない。
_TIMESTAMP_DIGITS = 2


class ReplayLogHeader(BaseModel):
    """再生用のログの先頭行。旧形式の行は `replay_version` を持たない."""

    model_config = ConfigDict(extra="forbid")

    replay_version: int = REPLAY_LOG_VERSION


class ReplayVector3(BaseModel):
    """丸めた座標・速度."""

    model_config = ConfigDict(extra="forbid")

    x: float
    y: float
    z: float


class ReplayLogEntry(BaseModel):
    """再生用のログの1行.

    値が無い項目は null にせず、キーごと省く。
    """

    model_config = ConfigDict(extra="forbid")

    timestamp: float
    actor_id: uuid.UUID
    action_type: str
    target_id: uuid.UUID | None = None
    damage: int | None = None
    message: str | None = None
    position_snapshot: ReplayVector3
    # DESTROYED の行には無い。フロントの補間はこの前提で動いている。
    velocity_snapshot: ReplayVector3 | None = None
    heading: float | None = None
    weapon_id: str | None = None
    weapon_name: str | None = None
    target_max_hp: int | None = None
    # true のときだけ持つ。
    is_crit: bool | None = None
    skill_activated: bool | None = None
    combo_count: int | None = None
    combo_message: str | None = None
    chatter: str | None = None
    details: dict[str, Any] | None = None


def _round(value: float, digits: int) -> float:
    # 0.0 を足して -0.0 を 0.0 にする。-0.0 のままだと JSON が "-0.0" になる。
    return round(value, digits) + 0.0


def _vector(vector: Vector3) -> dict[str, float]:
    return {
        "x": _round(vector.x, _VECTOR_DIGITS),
        "y": _round(vector.y, _VECTOR_DIGITS),
        "z": _round(vector.z, _VECTOR_DIGITS),
    }


def _replay_entry(log: BattleLog) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "timestamp": _round(log.timestamp, _TIMESTAMP_DIGITS),
        "actor_id": str(log.actor_id),
        "action_type": log.action_type,
    }
    if log.target_id is not None:
        entry["target_id"] = str(log.target_id)
    if log.damage is not None:
        entry["damage"] = log.damage
    if log.action_type not in _MESSAGE_DROPPED_ACTIONS:
        entry["message"] = log.message
    entry["position_snapshot"] = _vector(log.position_snapshot)
    if log.velocity_snapshot is not None:
        entry["velocity_snapshot"] = _vector(log.velocity_snapshot)
    if log.heading is not None:
        entry["heading"] = _round(log.heading, _HEADING_DIGITS)
    optional = {
        "weapon_id": log.weapon_id,
        "weapon_name": log.weapon_name,
        "target_max_hp": log.target_max_hp,
        "is_crit": True if log.is_crit else None,
        "skill_activated": log.skill_activated,
        "combo_count": log.combo_count,
        "combo_message": log.combo_message,
        "chatter": log.chatter,
        "details": to_jsonable_python(log.details) if log.details else None,
    }
    entry.update((k, v) for k, v in optional.items() if v is not None)
    return entry


def to_replay_logs(logs: Iterable[BattleLog]) -> list[dict[str, Any]]:
    """エンジンのログを、ヘッダー行から始まる再生用のログに変換する.

    `TARGET_SELECTION` は、機体ごとに相手が前の行と変わった行だけ残す。
    ビューアは相手の追跡にこの行を使う。

    Returns:
        JSON にそのまま書ける dict の一覧。先頭は `ReplayLogHeader`、
        残りは `ReplayLogEntry` の形
    """
    lines: list[dict[str, Any]] = [ReplayLogHeader().model_dump()]
    last_targets: dict[uuid.UUID, uuid.UUID | None] = {}
    for log in logs:
        if log.action_type in _DROPPED_ACTIONS:
            continue
        if log.action_type == "TARGET_SELECTION":
            if (
                log.actor_id in last_targets
                and last_targets[log.actor_id] == log.target_id
            ):
                continue
            last_targets[log.actor_id] = log.target_id
        lines.append(_replay_entry(log))
    return lines

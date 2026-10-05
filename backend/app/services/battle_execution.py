# backend/app/services/battle_execution.py
"""ルーム戦の機体組み立てと戦闘実行を行う.

どの関数も DB セッションを使わない。
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from app.engine.battle_digest import compute_unit_kills
from app.engine.battle_utils import serialize_obstacles
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon
from app.services.theater_service import BattleConditions

# 1 step は 0.1 秒。
DEFAULT_MAX_STEPS = 3000


@dataclass
class BattleOutcome:
    """戦闘を実行した結果."""

    simulator: BattleSimulator
    player_win: bool
    kills: int
    """プレイヤー機自身の撃墜数。チーム全体の撃墜数ではない。"""
    steps_used: int


def snapshot_to_mobile_suit(snapshot: dict) -> MobileSuit:
    """機体のスナップショットから `MobileSuit` を組み立てる.

    `snapshot` 内の位置・速度・武器・ID は、モデルの型に置き換えて書き戻す。
    書き換えをやめると、バッチが保存する `BattleResult.ms_snapshot` が変わる。
    元の dict を残したいときは、コピーを渡す。
    """
    if "position" in snapshot and isinstance(snapshot["position"], dict):
        snapshot["position"] = Vector3(**snapshot["position"])
    if "velocity" in snapshot and isinstance(snapshot["velocity"], dict):
        snapshot["velocity"] = Vector3(**snapshot["velocity"])
    if "weapons" in snapshot and isinstance(snapshot["weapons"], list):
        snapshot["weapons"] = [
            Weapon(**w) if isinstance(w, dict) else w for w in snapshot["weapons"]
        ]
    # model_dump(mode="json") 経由のスナップショットは id が str になる。
    if "id" in snapshot and isinstance(snapshot["id"], str):
        snapshot["id"] = uuid.UUID(snapshot["id"])
    ms_fields = set(MobileSuit.model_fields.keys())
    filtered = {k: v for k, v in snapshot.items() if k in ms_fields}
    mobile_suit = MobileSuit(**filtered)
    mobile_suit.normalize_parts()
    return mobile_suit


def resolve_team_id(unit: MobileSuit) -> str:
    """ユニットの所属チームを返す.

    チーム未所属（ソロ参加）のユニットは、ユニット ID を 1 人チームの ID とする。
    """
    return unit.team_id or str(unit.id)


def alive_team_ids(units: Iterable[MobileSuit]) -> set[str | None]:
    """HP が残っているユニットの所属チームを返す."""
    return {u.team_id for u in units if u.current_hp > 0}


def prepare_battle_units(
    player_snapshot: dict, enemy_snapshots: list[dict]
) -> tuple[MobileSuit, list[MobileSuit]]:
    """スナップショットからプレイヤー機と敵機を組み立てる.

    ルーム内の他プレイヤーも敵機として扱う。`team_id` が None のユニットには
    ユニット ID を設定する。
    """
    player_unit = snapshot_to_mobile_suit(player_snapshot)
    player_unit.side = "PLAYER"

    enemy_units = []
    for snapshot in enemy_snapshots:
        enemy_unit = snapshot_to_mobile_suit(snapshot)
        enemy_unit.side = "ENEMY"
        enemy_units.append(enemy_unit)

    for unit in [player_unit, *enemy_units]:
        if unit.team_id is None:
            unit.team_id = str(unit.id)

    return player_unit, enemy_units


def run_battle(
    player_unit: MobileSuit,
    enemy_units: list[MobileSuit],
    conditions: BattleConditions | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> BattleOutcome:
    """戦闘を決着まで実行する.

    渡したユニットの HP 等は、戦闘後の状態に書き換わる。

    Args:
        player_unit: 勝敗と撃墜数を判定する機体。
        enemy_units: プレイヤー機以外の全ユニット。味方チームの機体も含む。
        conditions: 戦域の条件。省略時は既定の条件（宇宙・濃度0）を使う。
        max_steps: 決着しないときに打ち切るステップ数。

    Returns:
        プレイヤー機のチームが生き残れば `player_win` が真になる。
    """
    conditions = conditions or BattleConditions()
    simulator = BattleSimulator(
        player_unit, enemy_units, **conditions.simulator_kwargs()
    )

    steps_used = 0
    for _ in range(max_steps):
        if simulator.is_finished:
            break
        simulator.step()
        steps_used += 1

    player_win = player_unit.team_id in alive_team_ids(simulator.units)
    kills = compute_unit_kills(simulator.logs, player_unit.id)

    return BattleOutcome(
        simulator=simulator,
        player_win=player_win,
        kills=kills,
        steps_used=steps_used,
    )


def build_result_view_fields(
    entry_unit: MobileSuit,
    units: list[MobileSuit],
    simulator: BattleSimulator,
) -> dict[str, Any]:
    """`BattleResult` の表示用フィールドを組み立てる.

    返す dict のキーは `player_info`・`enemies_info`・`obstacles_info`・
    `map_bounds` である。

    Args:
        entry_unit: 結果を受け取るプレイヤーの機体。`player_info` になる。
        units: 戦闘に参加した全ユニット。`entry_unit` と ID が同じユニットを
            除いて `enemies_info` にする。
        simulator: 戦闘を実行したシミュレーター。障害物とマップ範囲を読む。
    """
    return {
        "player_info": entry_unit.model_dump(),
        "enemies_info": [
            u.model_dump() for u in units if str(u.id) != str(entry_unit.id)
        ],
        "obstacles_info": serialize_obstacles(simulator.obstacles),
        "map_bounds": list(simulator.map_bounds),
    }

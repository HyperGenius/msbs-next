# backend/app/engine/objectives.py
"""作戦目標（勝利条件）.

作戦目標は、戦闘を終えるかと、あるチームから見た結果を決める。
DB を参照しない。
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.models.models import MISSION_OBJECTIVE_ANNIHILATION, MobileSuit

UnitResources = Mapping[str, Mapping[str, Any]]
"""ユニット ID（str）→ `BattleSimulator.unit_resources` の値。"""


class ObjectiveStatus(StrEnum):
    """作戦の結果の区分."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DRAW = "DRAW"


@dataclass(frozen=True)
class ObjectiveResult:
    """あるチームから見た作戦の結果."""

    status: ObjectiveStatus
    progress: int = 0
    """達成した数（例: 離脱させた友軍の数）。"""
    required: int = 0
    """成功に必要な数。0 は達成度を数えない目標を表す。"""

    @property
    def is_success(self) -> bool:
        """作戦が成功したか."""
        return self.status == ObjectiveStatus.SUCCESS


def is_active(unit: MobileSuit, unit_resources: UnitResources) -> bool:
    """ユニットが戦闘中か（撃破も撤退もしていないか）を返す."""
    return unit.current_hp > 0 and unit_resources[str(unit.id)]["status"] == "ACTIVE"


class BattleObjective(ABC):
    """作戦目標."""

    @abstractmethod
    def is_complete(
        self, units: Sequence[MobileSuit], unit_resources: UnitResources
    ) -> bool:
        """戦闘を終えるかを返す."""

    @abstractmethod
    def evaluate(
        self,
        units: Sequence[MobileSuit],
        unit_resources: UnitResources,
        team_id: str | None,
    ) -> ObjectiveResult:
        """`team_id` のチームから見た結果を返す.

        最大ステップ数で打ち切ったとき（`is_complete()` が偽のとき）も呼ぶ。
        """


class AnnihilationObjective(BattleObjective):
    """殲滅。戦闘中のチームが 1 つ以下になったら終える."""

    def is_complete(
        self, units: Sequence[MobileSuit], unit_resources: UnitResources
    ) -> bool:
        """戦闘中のユニットが残るチームが 1 つ以下かを返す."""
        active_teams = {u.team_id for u in units if is_active(u, unit_resources)}
        return len(active_teams) <= 1

    def evaluate(
        self,
        units: Sequence[MobileSuit],
        unit_resources: UnitResources,
        team_id: str | None,
    ) -> ObjectiveResult:
        """チームに HP の残る機体があれば成功とする.

        撤退した機体も生き残りに数える。打ち切ったときも同じ基準で決める。
        """
        survived = any(u.team_id == team_id and u.current_hp > 0 for u in units)
        return ObjectiveResult(
            ObjectiveStatus.SUCCESS if survived else ObjectiveStatus.FAILURE
        )


def build_objective(objective_type: str, params: Mapping[str, Any]) -> BattleObjective:
    """作戦マスターの目標の種類と引数から作戦目標を作る.

    Raises:
        ValueError: 目標の種類が無いとき。
    """
    if objective_type == MISSION_OBJECTIVE_ANNIHILATION:
        return AnnihilationObjective()
    raise ValueError(f"unknown objective type: {objective_type}")

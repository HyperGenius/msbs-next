# backend/app/engine/objectives.py
"""作戦目標（勝利条件）.

作戦目標は、戦闘を終えるかと、あるチームから見た結果を決める。
DB を参照しない。
"""

from abc import ABC, abstractmethod
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.models.models import (
    MISSION_OBJECTIVE_ANNIHILATION,
    MISSION_OBJECTIVE_RETREAT_SUPPORT,
    MobileSuit,
)

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
    total: int = 0
    """数える対象の総数（例: 護衛する友軍の数）。"""
    lost: int = 0
    """失った数（例: 撃破された友軍の数）。"""
    player_survived: bool | None = None
    """プレイヤー側の機体が戦場に残ったか。None は数えない目標。"""

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


class RetreatSupportObjective(BattleObjective):
    """撤退支援。護衛する友軍のうち必要数を撤退ポイントまで逃がす.

    * 終了: 護衛する友軍が全員「離脱」か「撃破」になる、または敵が全滅したとき
    * 結果: 離脱した数が必要数に届けば成功。プレイヤー機が撃破・離脱しても、
      友軍が逃げ切れば成功とする（報酬は減る。`PilotService.calculate_battle_rewards()`）
    * 敵が全滅したとき、戦場に残る友軍は離脱したものとして数える
    """

    def __init__(self, protected_unit_ids: Collection[str], required: int) -> None:
        """護衛する友軍のユニット ID（str）と、成功に必要な離脱数で作る.

        Raises:
            ValueError: 友軍がいないとき、必要数が 1 未満か友軍の数を超えるとき。
        """
        self.protected_unit_ids = frozenset(protected_unit_ids)
        if not self.protected_unit_ids:
            raise ValueError("retreat support needs at least one ally")
        if not 1 <= required <= len(self.protected_unit_ids):
            raise ValueError(
                f"required must be between 1 and {len(self.protected_unit_ids)}"
            )
        self.required = required

    def _protected(self, units: Sequence[MobileSuit]) -> list[MobileSuit]:
        return [u for u in units if str(u.id) in self.protected_unit_ids]

    def _enemies_remain(
        self, units: Sequence[MobileSuit], unit_resources: UnitResources
    ) -> bool:
        """護衛する友軍と別のチームに、戦闘中のユニットが残っているかを返す."""
        protected_teams = {u.team_id for u in self._protected(units)}
        return any(
            u.team_id not in protected_teams and is_active(u, unit_resources)
            for u in units
        )

    def is_complete(
        self, units: Sequence[MobileSuit], unit_resources: UnitResources
    ) -> bool:
        """友軍が全員戦闘から外れたか、敵が全滅したかを返す."""
        if not any(is_active(u, unit_resources) for u in self._protected(units)):
            return True
        return not self._enemies_remain(units, unit_resources)

    def evaluate(
        self,
        units: Sequence[MobileSuit],
        unit_resources: UnitResources,
        team_id: str | None,
    ) -> ObjectiveResult:
        """離脱数（敵が全滅していれば残る友軍も含む）で結果を決める.

        打ち切ったときも同じ基準で、その時点の離脱数で判定する。
        """
        protected = self._protected(units)
        enemies_remain = self._enemies_remain(units, unit_resources)
        escaped = 0
        lost = 0
        for unit in protected:
            if unit.current_hp <= 0:
                lost += 1
            elif unit_resources[str(unit.id)]["status"] == "RETREATED" or (
                not enemies_remain
            ):
                escaped += 1
        player_survived = any(
            u.team_id == team_id
            and str(u.id) not in self.protected_unit_ids
            and u.current_hp > 0
            for u in units
        )
        return ObjectiveResult(
            ObjectiveStatus.SUCCESS
            if escaped >= self.required
            else ObjectiveStatus.FAILURE,
            progress=escaped,
            required=self.required,
            total=len(protected),
            lost=lost,
            player_survived=player_survived,
        )


def build_objective(
    objective_type: str,
    params: Mapping[str, Any],
    protected_unit_ids: Collection[str] = (),
) -> BattleObjective:
    """作戦マスターの目標の種類と引数から作戦目標を作る.

    Args:
        objective_type: 目標の種類。
        params: 目標の引数。撤退支援は `required`（必要な離脱数。省略時は友軍の全員）。
        protected_unit_ids: 護衛する友軍のユニット ID（str）。撤退支援で使う。

    Raises:
        ValueError: 目標の種類が無いとき、撤退支援の友軍や必要数が不正なとき。
    """
    if objective_type == MISSION_OBJECTIVE_ANNIHILATION:
        return AnnihilationObjective()
    if objective_type == MISSION_OBJECTIVE_RETREAT_SUPPORT:
        return RetreatSupportObjective(
            protected_unit_ids, int(params.get("required", len(protected_unit_ids)))
        )
    raise ValueError(f"unknown objective type: {objective_type}")

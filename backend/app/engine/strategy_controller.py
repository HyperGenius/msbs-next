# backend/app/engine/strategy_controller.py
"""チームレベルの戦略モード管理コンポーネント (Phase 4-2 / 4-3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from app.engine.constants import (
    AGGRESSIVE_DEFENSIVE_ALIVE_THRESHOLD,
    AGGRESSIVE_DEFENSIVE_HP_THRESHOLD,
    AGGRESSIVE_RETREAT_ALIVE_THRESHOLD,
    AGGRESSIVE_RETREAT_HP_THRESHOLD,
    ASSAULT_AGGRESSIVE_HP_THRESHOLD,
    ASSAULT_RETREAT_ALIVE_THRESHOLD,
    ASSAULT_RETREAT_HP_THRESHOLD,
    DEFENSIVE_AGGRESSIVE_ALIVE_THRESHOLD,
    DEFENSIVE_AGGRESSIVE_HP_THRESHOLD,
    DEFENSIVE_RETREAT_ALIVE_THRESHOLD,
    DEFENSIVE_RETREAT_HP_THRESHOLD,
    RETREAT_WIPE_ALIVE_THRESHOLD,
    SNIPER_DEFENSIVE_HP_THRESHOLD,
    SNIPER_RETREAT_ALIVE_THRESHOLD,
    SNIPER_RETREAT_HP_THRESHOLD,
)


@dataclass
class TeamMetrics:
    """チームのバトルメトリクス.

    BattleSimulator から収集したチームの現状を表すデータクラス。
    _strategy_phase() の先頭で全チームに対して算出される。
    """

    team_id: str
    alive_count: int  # ACTIVE ステータスのユニット数
    total_count: int  # チームの全ユニット数
    alive_ratio: float  # alive_count / total_count (0.0〜1.0)
    avg_hp_ratio: float  # ACTIVE ユニットの平均 HP 割合 (0.0〜1.0)
    min_hp_ratio: float  # ACTIVE ユニットの最低 HP 割合 (0.0〜1.0)
    current_strategy: str  # チームの現在の StrategyMode
    elapsed_time: float  # バトル経過時間 (s)
    retreat_points_empty: bool = field(default=False)  # 撤退ポイント未設定フラグ (Phase 4-3)


@dataclass
class StrategyTransitionRule:
    """戦略遷移ルール定義 (Phase 4-3).

    「現在の StrategyMode × 評価条件 → 遷移先 StrategyMode」を表す。
    """

    rule_id: str
    from_strategy: str | None  # None は any にマッチ
    to_strategy: str
    condition: Callable[[TeamMetrics], bool]
    description: str


# ---------------------------------------------------------------------------
# 戦略遷移ルール一覧 T01〜T10 (Phase 4-3)
# ルール評価は上から順に実施し、最初にマッチしたルールを採用する。
# ---------------------------------------------------------------------------
STRATEGY_TRANSITION_RULES: list[StrategyTransitionRule] = [
    StrategyTransitionRule(
        rule_id="T01",
        from_strategy="AGGRESSIVE",
        to_strategy="RETREAT",
        condition=lambda m: (
            m.avg_hp_ratio < AGGRESSIVE_RETREAT_HP_THRESHOLD
            and m.alive_ratio < AGGRESSIVE_RETREAT_ALIVE_THRESHOLD
        ),
        description="大損害を受けたら撤退",
    ),
    StrategyTransitionRule(
        rule_id="T02",
        from_strategy="AGGRESSIVE",
        to_strategy="DEFENSIVE",
        condition=lambda m: (
            m.avg_hp_ratio < AGGRESSIVE_DEFENSIVE_HP_THRESHOLD
            and m.alive_ratio < AGGRESSIVE_DEFENSIVE_ALIVE_THRESHOLD
        ),
        description="劣勢になったら防衛重視に切替",
    ),
    StrategyTransitionRule(
        rule_id="T03",
        from_strategy="DEFENSIVE",
        to_strategy="RETREAT",
        condition=lambda m: (
            m.avg_hp_ratio < DEFENSIVE_RETREAT_HP_THRESHOLD
            and m.alive_ratio < DEFENSIVE_RETREAT_ALIVE_THRESHOLD
        ),
        description="防衛中も限界なら撤退",
    ),
    StrategyTransitionRule(
        rule_id="T04",
        from_strategy="DEFENSIVE",
        to_strategy="AGGRESSIVE",
        condition=lambda m: (
            m.avg_hp_ratio >= DEFENSIVE_AGGRESSIVE_HP_THRESHOLD
            and m.alive_ratio >= DEFENSIVE_AGGRESSIVE_ALIVE_THRESHOLD
        ),
        description="体勢を立て直したら攻勢へ",
    ),
    StrategyTransitionRule(
        rule_id="T05",
        from_strategy="SNIPER",
        to_strategy="RETREAT",
        condition=lambda m: (
            m.avg_hp_ratio < SNIPER_RETREAT_HP_THRESHOLD
            and m.alive_ratio < SNIPER_RETREAT_ALIVE_THRESHOLD
        ),
        description="スナイパーも大損害なら撤退",
    ),
    StrategyTransitionRule(
        rule_id="T06",
        from_strategy="SNIPER",
        to_strategy="DEFENSIVE",
        condition=lambda m: m.avg_hp_ratio < SNIPER_DEFENSIVE_HP_THRESHOLD,
        description="スナイパーが劣勢なら防衛へ",
    ),
    StrategyTransitionRule(
        rule_id="T07",
        from_strategy="ASSAULT",
        to_strategy="RETREAT",
        condition=lambda m: (
            m.avg_hp_ratio < ASSAULT_RETREAT_HP_THRESHOLD
            and m.alive_ratio < ASSAULT_RETREAT_ALIVE_THRESHOLD
        ),
        description="突撃部隊も壊滅寸前なら撤退",
    ),
    StrategyTransitionRule(
        rule_id="T08",
        from_strategy="ASSAULT",
        to_strategy="AGGRESSIVE",
        condition=lambda m: m.avg_hp_ratio < ASSAULT_AGGRESSIVE_HP_THRESHOLD,
        description="突撃継続が難しければ通常攻撃に切替",
    ),
    StrategyTransitionRule(
        rule_id="T09",
        from_strategy="RETREAT",
        to_strategy="RETREAT",
        condition=lambda m: m.alive_ratio < RETREAT_WIPE_ALIVE_THRESHOLD,
        description="撤退中は変更しない（維持）",
    ),
    StrategyTransitionRule(
        rule_id="T10",
        from_strategy="RETREAT",
        to_strategy="DEFENSIVE",
        condition=lambda m: m.retreat_points_empty,
        description="撤退ポイントなし → 防衛に切替（殲滅戦）",
    ),
]


class TeamStrategyController:
    """チームレベルの戦略モードを管理するコントローラ."""

    def __init__(
        self,
        team_id: str,
        initial_strategy: str = "AGGRESSIVE",
        update_interval: int = 10,
    ) -> None:
        """初期化.

        Args:
            team_id: 管理対象のチームID
            initial_strategy: 初期戦略モード
            update_interval: 何ステップごとに戦略評価を行うか
        """
        self.team_id = team_id
        self.current_strategy = initial_strategy
        self.update_interval = update_interval
        self._step_counter: int = 0
        self._last_matched_rule_id: str | None = None  # 直近でマッチしたルールID (Phase 4-3)

    def should_evaluate(self) -> bool:
        """このステップで戦略評価を行うべきか判定する.

        バトル開始直後（_step_counter == 0）は評価をスキップし、
        初期戦略が即座に上書きされる問題を回避する。

        Returns:
            評価を行うべき場合は True
        """
        self._step_counter += 1
        return self._step_counter % self.update_interval == 0

    def evaluate(self, team_metrics: TeamMetrics) -> str | None:
        """遷移ルールを上から評価し、最初にマッチしたルールの to_strategy を返す.

        変更がない場合は None を返す。
        マッチしたルールの rule_id は _last_matched_rule_id に保存される。

        Args:
            team_metrics: チームの現在のメトリクス

        Returns:
            新しい StrategyMode 文字列、変更なしの場合は None
        """
        self._last_matched_rule_id = None
        for rule in STRATEGY_TRANSITION_RULES:
            # from_strategy が None (any) または現在の戦略と一致する場合のみ評価
            if rule.from_strategy is not None and rule.from_strategy != self.current_strategy:
                continue
            if rule.condition(team_metrics):
                if rule.to_strategy != self.current_strategy:
                    self._last_matched_rule_id = rule.rule_id
                    return rule.to_strategy
        return None

    def apply(self, new_strategy: str, units: list) -> None:
        """チーム内の全 ACTIVE ユニットの strategy_mode を更新する.

        DESTROYED / RETREATED ステータスのユニットは更新しない。

        Args:
            new_strategy: 適用する新しい戦略モード
            units: (unit, unit_resource) のタプルリスト
                   各要素は (MobileSuit, dict) の形式
        """
        self.current_strategy = new_strategy
        for unit, resource in units:
            if resource.get("status") == "ACTIVE":
                unit.strategy_mode = new_strategy

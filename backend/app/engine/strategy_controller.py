# backend/app/engine/strategy_controller.py
"""チームレベルの戦略モード管理コンポーネント (Phase 4-2)."""

from dataclasses import dataclass


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
        """チームのメトリクスを評価し、新しい StrategyMode を返す.

        Phase 4-2 ではスタブ実装として常に None を返す。
        具体的な遷移ルールは Phase 4-3 で実装する。

        Args:
            team_metrics: チームの現在のメトリクス

        Returns:
            新しい StrategyMode 文字列、変更なしの場合は None
        """
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

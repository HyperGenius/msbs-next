#!/usr/bin/env python3
# backend/scripts/sim_compare.py
r"""compare サブコマンドの実処理: 2つの戦略モードを対戦させて比較する.

Usage (経由: run_simulation.py):
    python scripts/run_simulation.py compare \
        --mission-id 1 --strategy-a AGGRESSIVE --strategy-b DEFENSIVE --rounds 20
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.engine.constants import BALANCE_WARN_WIN_RATE
from app.engine.simulation import BattleSimulator


@dataclass
class StrategyStats:
    """1つの戦略モードの集計データ."""

    strategy: str
    win_count: int = 0
    rounds: int = 0
    action_counts: dict[str, int] = field(default_factory=dict)
    survivor_hp_ratios: list[float] = field(default_factory=list)
    survivor_counts: list[int] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        """勝率を返す."""
        if self.rounds == 0:
            return 0.0
        return self.win_count / self.rounds

    @property
    def avg_survivor_hp_ratio(self) -> float:
        """平均生存HP比率を返す."""
        if not self.survivor_hp_ratios:
            return 0.0
        return sum(self.survivor_hp_ratios) / len(self.survivor_hp_ratios)

    @property
    def avg_survivor_count(self) -> float:
        """平均生存ユニット数を返す."""
        if not self.survivor_counts:
            return 0.0
        return sum(self.survivor_counts) / len(self.survivor_counts)

    @property
    def action_total(self) -> int:
        """行動ログの総数を返す."""
        return sum(self.action_counts.values())

    def action_ratio(self, action_type: str) -> float:
        """指定した行動タイプの割合を返す."""
        total = self.action_total
        if total == 0:
            return 0.0
        return self.action_counts.get(action_type, 0) / total


@dataclass
class ComparisonSummary:
    """compare コマンドの比較結果."""

    mission_id: int
    strategy_a: str
    strategy_b: str
    rounds: int
    stats_a: StrategyStats = field(default_factory=lambda: StrategyStats(strategy="A"))
    stats_b: StrategyStats = field(default_factory=lambda: StrategyStats(strategy="B"))
    draw_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        """テキスト形式で比較結果を返す."""
        lines = []
        lines.append(
            f"=== Compare: {self.strategy_a} vs {self.strategy_b}, rounds={self.rounds} ==="
        )
        lines.append("")

        col_a = f"{self.strategy_a:>12}"
        col_b = f"{self.strategy_b:>12}"
        lines.append(f"{'':18}{col_a}  {col_b}")

        lines.append(
            f"{'勝利回数':<18}{self.stats_a.win_count:>12}  {self.stats_b.win_count:>12}"
        )
        lines.append(
            f"{'勝率':<18}{self.stats_a.win_rate:>11.1%}  {self.stats_b.win_rate:>11.1%}"
        )
        lines.append(f"{'引き分け':<18}{'':>12}  {self.draw_count:>12}")
        lines.append("")

        lines.append(
            f"{'平均生存ユニット数':<16}"
            f"{self.stats_a.avg_survivor_count:>12.1f}  "
            f"{self.stats_b.avg_survivor_count:>12.1f}"
        )
        lines.append(
            f"{'平均残HP率':<18}"
            f"{self.stats_a.avg_survivor_hp_ratio:>12.2f}  "
            f"{self.stats_b.avg_survivor_hp_ratio:>12.2f}"
        )

        # 行動分布
        all_actions = sorted(
            set(self.stats_a.action_counts) | set(self.stats_b.action_counts)
        )
        for action_type in all_actions:
            ra = self.stats_a.action_ratio(action_type)
            rb = self.stats_b.action_ratio(action_type)
            lines.append(f"{'平均行動: ' + action_type:<18}{ra:>11.1%}  {rb:>11.1%}")
        lines.append("")

        # 判定
        diff = self.stats_a.win_rate - self.stats_b.win_rate
        if abs(diff) < 0.05:
            verdict = "両者ほぼ互角"
        elif diff > 0:
            verdict = f"{self.strategy_a} が優勢（勝率差 +{diff:.1%}）" + (
                "⚠️  バランス要調整"
                if self.stats_a.win_rate > BALANCE_WARN_WIN_RATE
                else ""
            )
        else:
            verdict = f"{self.strategy_b} が優勢（勝率差 +{-diff:.1%}）" + (
                "⚠️  バランス要調整"
                if self.stats_b.win_rate > BALANCE_WARN_WIN_RATE
                else ""
            )
        lines.append(f"判定: {verdict}")

        if self.warnings:
            lines.append("")
            for w in self.warnings:
                lines.append(f"⚠️  {w}")

        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        """JSON シリアライズ可能な dict を返す."""

        def _stats_dict(s: StrategyStats) -> dict[str, Any]:
            return {
                "strategy": s.strategy,
                "win_count": s.win_count,
                "win_rate": s.win_rate,
                "avg_survivor_count": s.avg_survivor_count,
                "avg_survivor_hp_ratio": s.avg_survivor_hp_ratio,
                "action_counts": s.action_counts,
                "action_ratios": {k: s.action_ratio(k) for k in s.action_counts},
            }

        return {
            "mission_id": self.mission_id,
            "strategy_a": self.strategy_a,
            "strategy_b": self.strategy_b,
            "rounds": self.rounds,
            "draw_count": self.draw_count,
            "stats_a": _stats_dict(self.stats_a),
            "stats_b": _stats_dict(self.stats_b),
            "warnings": self.warnings,
        }


# 集計対象のアクションタイプ（チームイベントを除く）
_UNIT_ACTION_TYPES = {
    "ATTACK",
    "MOVE",
    "USE_SKILL",
    "RETREAT",
    "MISS",
    "DAMAGE",
    "DESTROYED",
}


class CompareRunner:
    """2つの戦略モードを対戦させて比較サマリーを生成する."""

    def __init__(self, max_steps: int = 5000) -> None:
        """初期化."""
        self.max_steps = max_steps

    def run(
        self,
        mission_id: int,
        rounds: int,
        strategy_a: str = "AGGRESSIVE",
        strategy_b: str = "DEFENSIVE",
        enable_hot_reload: bool = False,
    ) -> ComparisonSummary:
        """N 回シミュレーションを実行して比較サマリーを返す.

        チームAに strategy_a、チームBに strategy_b を適用する。
        プレイヤーチームが strategy_a、最大の敵チームが strategy_b を使用。

        Args:
            mission_id: ミッション ID
            rounds: 実行回数
            strategy_a: プレイヤーチームの戦略モード
            strategy_b: 敵チームの戦略モード
            enable_hot_reload: Phase 5-2 のホットリロードを有効化

        Returns:
            ComparisonSummary インスタンス
        """
        from sqlmodel import Session, select

        from app.db import engine
        from app.models.models import Mission, MobileSuit

        with Session(engine) as session:
            mission = session.get(Mission, mission_id)
            if not mission:
                raise ValueError(f"ミッション ID={mission_id} が見つかりません")

            player_results = list(session.exec(select(MobileSuit).limit(1)).all())
            if not player_results:
                raise ValueError("DBにモビルスーツが登録されていません")

            player_base = MobileSuit.model_validate(player_results[0].model_dump())

            from scripts.run_simulation import _build_enemies_from_config

            enemy_configs = mission.enemy_config.get("enemies", [])
            enemies_base = _build_enemies_from_config(enemy_configs)

        return self.run_with_units(
            player_base=player_base,
            enemies_base=enemies_base,
            mission=mission,
            rounds=rounds,
            strategy_a=strategy_a,
            strategy_b=strategy_b,
            enable_hot_reload=enable_hot_reload,
        )

    def run_with_units(
        self,
        player_base: Any,
        enemies_base: list[Any],
        mission: Any,
        rounds: int,
        strategy_a: str = "AGGRESSIVE",
        strategy_b: str = "DEFENSIVE",
        enable_hot_reload: bool = False,
    ) -> ComparisonSummary:
        """ユニットを直接渡してN回シミュレーションを実行する（テスト用）."""
        summary = ComparisonSummary(
            mission_id=getattr(mission, "id", 0),
            strategy_a=strategy_a,
            strategy_b=strategy_b,
            rounds=rounds,
            stats_a=StrategyStats(strategy=strategy_a),
            stats_b=StrategyStats(strategy=strategy_b),
        )
        summary.stats_a.rounds = rounds
        summary.stats_b.rounds = rounds

        for _ in range(rounds):
            self._run_single(
                player_base=player_base,
                enemies_base=enemies_base,
                mission=mission,
                strategy_a=strategy_a,
                strategy_b=strategy_b,
                enable_hot_reload=enable_hot_reload,
                summary=summary,
            )

        self._compute_warnings(summary)
        return summary

    def _determine_winner_compare(
        self,
        player: Any,
        enemies: list[Any],
        summary: ComparisonSummary,
    ) -> None:
        """勝敗を判定してサマリーの win_count / draw_count を更新する."""
        player_alive = player.current_hp > 0
        enemy_alive = any(e.current_hp > 0 for e in enemies)
        if player_alive and not enemy_alive:
            summary.stats_a.win_count += 1
        elif enemy_alive and not player_alive:
            summary.stats_b.win_count += 1
        else:
            summary.draw_count += 1

    def _collect_action_counts_by_team(
        self,
        sim: Any,
        summary: ComparisonSummary,
    ) -> None:
        """チームごとの行動分布をサマリーに積算する."""
        unit_team_map = {str(u.id): u.team_id for u in sim.units}
        for log in sim.logs:
            at = log.action_type
            if at not in _UNIT_ACTION_TYPES:
                continue
            team_of_actor = unit_team_map.get(str(log.actor_id), "")
            if team_of_actor == "PLAYER_TEAM":
                summary.stats_a.action_counts[at] = (
                    summary.stats_a.action_counts.get(at, 0) + 1
                )
            elif team_of_actor == "ENEMY_TEAM":
                summary.stats_b.action_counts[at] = (
                    summary.stats_b.action_counts.get(at, 0) + 1
                )

    @staticmethod
    def _collect_team_survivor_stats(
        units: list[Any], team_id: str
    ) -> tuple[float, int]:
        """指定チームの生存ユニットの平均 HP 比率とユニット数を返す."""
        team_units = [u for u in units if u.team_id == team_id and u.current_hp > 0]
        count = len(team_units)
        if count == 0:
            return 0.0, 0
        avg_hp = (
            sum(u.current_hp / u.max_hp for u in team_units if u.max_hp > 0) / count
        )
        return avg_hp, count

    def _run_single(
        self,
        player_base: Any,
        enemies_base: list[Any],
        mission: Any,
        strategy_a: str,
        strategy_b: str,
        enable_hot_reload: bool,
        summary: ComparisonSummary,
    ) -> None:
        """1ラウンドのシミュレーションを実行してサマリーに積算する."""
        from app.models.models import MobileSuit, Vector3

        player = MobileSuit.model_validate(player_base.model_dump())
        player.current_hp = player.max_hp
        player.position = Vector3(x=0, y=0, z=0)
        player.side = "PLAYER"
        player.team_id = "PLAYER_TEAM"
        player.strategy_mode = strategy_a.upper()

        enemies = []
        for e_base in enemies_base:
            e = MobileSuit.model_validate(e_base.model_dump())
            e.current_hp = e.max_hp
            e.strategy_mode = strategy_b.upper()
            enemies.append(e)

        sim = BattleSimulator(
            player=player,
            enemies=enemies,
            environment=getattr(mission, "environment", "SPACE"),
            special_effects=getattr(mission, "special_effects", None) or [],
            enable_hot_reload=enable_hot_reload,
        )

        step_count = 0
        for _ in range(self.max_steps):
            if sim.is_finished:
                break
            sim.step()
            step_count += 1

        self._determine_winner_compare(player, enemies, summary)
        self._collect_action_counts_by_team(sim, summary)

        hp_a, cnt_a = self._collect_team_survivor_stats(sim.units, "PLAYER_TEAM")
        hp_b, cnt_b = self._collect_team_survivor_stats(sim.units, "ENEMY_TEAM")
        summary.stats_a.survivor_hp_ratios.append(hp_a)
        summary.stats_a.survivor_counts.append(cnt_a)
        summary.stats_b.survivor_hp_ratios.append(hp_b)
        summary.stats_b.survivor_counts.append(cnt_b)

    def _compute_warnings(self, summary: ComparisonSummary) -> None:
        """異常検出: 閾値を超えた場合に警告を追加する."""
        if summary.rounds == 0:
            return

        if summary.stats_a.win_rate > BALANCE_WARN_WIN_RATE:
            summary.warnings.append(
                f"{summary.strategy_a} の勝率が高すぎます "
                f"({summary.stats_a.win_rate:.1%}): バランスが偏っている可能性があります"
            )
        if summary.stats_b.win_rate > BALANCE_WARN_WIN_RATE:
            summary.warnings.append(
                f"{summary.strategy_b} の勝率が高すぎます "
                f"({summary.stats_b.win_rate:.1%}): バランスが偏っている可能性があります"
            )


def run_compare_command(args: Any) -> None:
    """Compare サブコマンドのエントリーポイント."""
    runner = CompareRunner(max_steps=getattr(args, "steps", 5000))
    print(
        f"compare 実行中: mission_id={args.mission_id}, "
        f"strategy_a={args.strategy_a}, strategy_b={args.strategy_b}, "
        f"rounds={args.rounds}"
    )
    summary = runner.run(
        mission_id=args.mission_id,
        rounds=args.rounds,
        strategy_a=args.strategy_a,
        strategy_b=args.strategy_b,
        enable_hot_reload=args.hot_reload,
    )

    output_format = getattr(args, "format", "text")
    output_path = getattr(args, "output", None)

    if output_format == "json":
        content = json.dumps(summary.to_json(), ensure_ascii=False, indent=2)
    else:
        content = summary.to_text()

    if output_path:
        from pathlib import Path

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(f"結果を保存しました: {out.resolve()}")
    else:
        print(content)

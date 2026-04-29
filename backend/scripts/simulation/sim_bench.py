#!/usr/bin/env python3
# backend/scripts/sim_bench.py
"""bench サブコマンドの実処理: 複数回シミュレーションを実行してサマリーを集計する.

Usage (経由: run_simulation.py):
    python scripts/run_simulation.py bench --mission-id 1 --rounds 10
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.engine.constants import (
    BALANCE_WARN_AVG_DURATION,
    BALANCE_WARN_DRAW_RATE,
    BALANCE_WARN_WIN_RATE,
)
from app.engine.simulation import BattleSimulator

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


@dataclass
class RoundResult:
    """1ラウンドのシミュレーション結果."""

    win_team: str  # "PLAYER_TEAM" / "ENEMY_TEAM" / "DRAW"
    elapsed_time: float
    action_counts: dict[str, int]
    strategy_transitions: list[tuple[str, str]]  # (from_strategy, to_strategy) のリスト
    kills: dict[str, int]  # {team_id: kill_count}
    survivor_hp_ratio: dict[str, float]  # {team_id: avg HP ratio of survivors}
    survivor_count: dict[str, int]  # {team_id: count of surviving units}
    is_max_steps: bool  # 最大ステップ到達による終了かどうか


@dataclass
class SimulationSummary:
    """bench コマンドのサマリー結果."""

    mission_id: int
    strategy: str
    rounds: int
    win_counts: dict[str, int] = field(
        default_factory=dict
    )  # {team_id: count, "DRAW": count}
    durations: list[float] = field(default_factory=list)
    action_distribution: dict[str, int] = field(default_factory=dict)
    strategy_transition_counts: dict[str, int] = field(default_factory=dict)
    kills_per_round: dict[str, list[int]] = field(default_factory=dict)
    draw_by_max_steps: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def total_rounds(self) -> int:
        """実際に集計されたラウンド数（win_countsの合計）を返す."""
        return self.rounds

    @property
    def draw_count(self) -> int:
        """引き分けの回数を返す."""
        return self.win_counts.get("DRAW", 0)

    @property
    def draw_rate(self) -> float:
        """引き分け率を返す."""
        if self.rounds == 0:
            return 0.0
        return self.draw_count / self.rounds

    @property
    def avg_duration(self) -> float:
        """平均戦闘時間を返す."""
        if not self.durations:
            return 0.0
        return sum(self.durations) / len(self.durations)

    @property
    def min_duration(self) -> float:
        """最短戦闘時間を返す."""
        return min(self.durations) if self.durations else 0.0

    @property
    def max_duration(self) -> float:
        """最長戦闘時間を返す."""
        return max(self.durations) if self.durations else 0.0

    @property
    def action_total(self) -> int:
        """行動の合計数を返す."""
        return sum(self.action_distribution.values())

    def action_ratio(self, action_type: str) -> float:
        """指定した行動タイプの割合を返す."""
        total = self.action_total
        if total == 0:
            return 0.0
        return self.action_distribution.get(action_type, 0) / total

    def win_rate(self, team_id: str) -> float:
        """指定したチームの勝率を返す."""
        if self.rounds == 0:
            return 0.0
        return self.win_counts.get(team_id, 0) / self.rounds

    def _format_action_section(self) -> list[str]:
        """行動分布セクションのテキスト行を返す."""
        lines: list[str] = []
        if not self.action_distribution:
            return lines
        lines.append("行動分布（全ユニット平均）:")
        for action_type in sorted(self.action_distribution):
            pct = self.action_ratio(action_type) * 100
            lines.append(f"  {action_type:<12}: {pct:.1f}%")
        lines.append("")
        return lines

    def _format_kills_section(self) -> list[str]:
        """撃墜数セクションのテキスト行を返す."""
        lines: list[str] = []
        if not self.kills_per_round:
            return lines
        lines.append("撃墜数（平均）:")
        for team_id, kills_list in self.kills_per_round.items():
            avg = sum(kills_list) / len(kills_list) if kills_list else 0.0
            lines.append(f"  {team_id}: {avg:.1f} 撃墜 / バトル")
        lines.append("")
        return lines

    def to_text(self) -> str:
        """テキスト形式でサマリーを返す."""
        lines = []
        lines.append(
            f"=== Bench Summary: mission_id={self.mission_id}, "
            f"strategy={self.strategy}, rounds={self.rounds} ==="
        )
        lines.append("")

        # 勝敗分布
        lines.append("勝敗分布:")
        for team_id, count in self.win_counts.items():
            pct = count / self.rounds * 100 if self.rounds > 0 else 0.0
            if team_id == "DRAW":
                label = "引き分け   "
            else:
                label = f"{team_id} 勝利"
            lines.append(f"  {label}: {count:2d} 回 ({pct:.1f}%)")
        lines.append("")

        # 平均戦闘時間
        lines.append(
            f"平均戦闘時間: {self.avg_duration:.1f}s "
            f"(最短 {self.min_duration:.1f}s / 最長 {self.max_duration:.1f}s)"
        )
        lines.append("")

        # 行動分布
        lines.extend(self._format_action_section())

        # 戦略遷移
        if self.strategy_transition_counts:
            lines.append("戦略遷移（合計）:")
            for transition, count in sorted(self.strategy_transition_counts.items()):
                avg = count / self.rounds if self.rounds > 0 else 0.0
                lines.append(f"  {transition}: {avg:.1f} 回/バトル")
            lines.append("")

        # 撃墜数
        lines.extend(self._format_kills_section())

        # 引き分け検出
        if self.draw_by_max_steps > 0:
            lines.append(
                f"引き分け検出: {self.draw_by_max_steps} 件（最大ステップ到達）"
            )
            lines.append("")

        # 警告
        for warning in self.warnings:
            lines.append(f"⚠️  {warning}")

        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        """JSON シリアライズ可能な dict を返す."""
        return {
            "mission_id": self.mission_id,
            "strategy": self.strategy,
            "rounds": self.rounds,
            "win_counts": self.win_counts,
            "durations": {
                "avg": self.avg_duration,
                "min": self.min_duration,
                "max": self.max_duration,
                "values": self.durations,
            },
            "action_distribution": self.action_distribution,
            "action_ratios": {
                k: self.action_ratio(k) for k in self.action_distribution
            },
            "strategy_transition_counts": self.strategy_transition_counts,
            "kills_per_round": self.kills_per_round,
            "draw_by_max_steps": self.draw_by_max_steps,
            "warnings": self.warnings,
        }


class BenchRunner:
    """N 回シミュレーションを実行してサマリーを生成する."""

    def __init__(self, max_steps: int = 5000) -> None:
        """初期化.

        Args:
            max_steps: シミュレーションの最大ステップ数
        """
        self.max_steps = max_steps

    def run(
        self,
        mission_id: int,
        rounds: int,
        strategy: str = "AGGRESSIVE",
        enable_hot_reload: bool = False,
    ) -> SimulationSummary:
        """N 回シミュレーションを実行してサマリーを返す.

        Args:
            mission_id: ミッション ID
            rounds: 実行回数
            strategy: 全チームに適用する初期戦略モード
            enable_hot_reload: Phase 5-2 のホットリロードを有効化

        Returns:
            SimulationSummary インスタンス
        """
        from sqlmodel import Session, select

        from app.db import engine
        from app.models.models import Mission, MobileSuit

        # DB からミッションデータを取得（1回だけ）
        with Session(engine) as session:
            mission = session.get(Mission, mission_id)
            if not mission:
                raise ValueError(f"ミッション ID={mission_id} が見つかりません")

            player_results = list(session.exec(select(MobileSuit).limit(1)).all())
            if not player_results:
                raise ValueError("DBにモビルスーツが登録されていません")

            player_raw = player_results[0]
            player_base = MobileSuit.model_validate(player_raw.model_dump())

            # ミッション設定から敵ユニットを構築
            from scripts.simulation.run_simulation import _build_enemies_from_config

            enemy_configs = mission.enemy_config.get("enemies", [])
            enemies_base = _build_enemies_from_config(enemy_configs)

        summary = SimulationSummary(
            mission_id=mission_id,
            strategy=strategy,
            rounds=rounds,
        )
        summary.win_counts = {"PLAYER_TEAM": 0, "ENEMY_TEAM": 0, "DRAW": 0}

        for _ in range(rounds):
            result = self._run_single(
                player_base=player_base,
                enemies_base=enemies_base,
                mission=mission,
                strategy=strategy,
                enable_hot_reload=enable_hot_reload,
            )
            self._accumulate(summary, result)

        self._compute_warnings(summary)
        return summary

    def run_with_units(
        self,
        player_base: Any,
        enemies_base: list[Any],
        mission: Any,
        rounds: int,
        strategy: str = "AGGRESSIVE",
        enable_hot_reload: bool = False,
    ) -> SimulationSummary:
        """ユニットを直接渡してN回シミュレーションを実行する（テスト用）.

        Args:
            player_base: プレイヤーユニット（コピーして使用）
            enemies_base: 敵ユニットリスト（コピーして使用）
            mission: ミッションオブジェクト
            rounds: 実行回数
            strategy: 全チームに適用する初期戦略モード
            enable_hot_reload: Phase 5-2 のホットリロードを有効化

        Returns:
            SimulationSummary インスタンス
        """
        summary = SimulationSummary(
            mission_id=getattr(mission, "id", 0),
            strategy=strategy,
            rounds=rounds,
        )
        summary.win_counts = {"PLAYER_TEAM": 0, "ENEMY_TEAM": 0, "DRAW": 0}

        for _ in range(rounds):
            result = self._run_single(
                player_base=player_base,
                enemies_base=enemies_base,
                mission=mission,
                strategy=strategy,
                enable_hot_reload=enable_hot_reload,
            )
            self._accumulate(summary, result)

        self._compute_warnings(summary)
        return summary

    def _determine_win_team_bench(self, sim: Any, player: Any) -> str:
        """シミュレーション結果から勝利チームIDを返す."""
        player_alive = player.current_hp > 0
        enemy_alive = any(
            u.team_id != player.team_id and u.current_hp > 0 for u in sim.units
        )
        if player_alive and not enemy_alive:
            return player.team_id
        if enemy_alive and not player_alive:
            alive_team_ids = {u.team_id for u in sim.units if u.current_hp > 0}
            return next(
                (tid for tid in alive_team_ids if tid != player.team_id), "DRAW"
            )
        return "DRAW"

    def _collect_action_and_transitions(
        self, sim_logs: list[Any]
    ) -> tuple[dict[str, int], list[tuple[str, str]]]:
        """ログから行動カウントと戦略遷移リストを収集する."""
        action_counts: dict[str, int] = {}
        strategy_transitions: list[tuple[str, str]] = []
        for log in sim_logs:
            at = log.action_type
            if at in _UNIT_ACTION_TYPES:
                action_counts[at] = action_counts.get(at, 0) + 1
            if log.action_type == "STRATEGY_CHANGED" and log.details:
                prev = log.details.get("previous_strategy", "")
                nxt = log.details.get("new_strategy", "")
                if prev and nxt:
                    strategy_transitions.append((prev, nxt))
        return action_counts, strategy_transitions

    def _collect_survivor_stats_bench(
        self, sim_units: list[Any]
    ) -> tuple[dict[str, float], dict[str, int]]:
        """生存ユニットの HP 比率とユニット数をチームごとに集計する."""
        survivor_hp_ratio: dict[str, float] = {}
        survivor_count: dict[str, int] = {}
        for u in sim_units:
            if u.current_hp > 0 and u.max_hp > 0 and u.team_id:
                team_id = u.team_id
                if team_id not in survivor_hp_ratio:
                    survivor_hp_ratio[team_id] = 0.0
                    survivor_count[team_id] = 0
                survivor_hp_ratio[team_id] += u.current_hp / u.max_hp
                survivor_count[team_id] += 1
        for tid in survivor_hp_ratio:
            cnt = survivor_count[tid]
            if cnt > 0:
                survivor_hp_ratio[tid] /= cnt
        return survivor_hp_ratio, survivor_count

    def _run_single(
        self,
        player_base: Any,
        enemies_base: list[Any],
        mission: Any,
        strategy: str,
        enable_hot_reload: bool,
    ) -> RoundResult:
        """1ラウンドのシミュレーションを実行する.

        Args:
            player_base: プレイヤーユニット（コピーして使用）
            enemies_base: 敵ユニットリスト（コピーして使用）
            mission: ミッションオブジェクト
            strategy: 全チームに適用する初期戦略モード
            enable_hot_reload: Phase 5-2 のホットリロードを有効化

        Returns:
            RoundResult インスタンス
        """
        from app.models.models import MobileSuit, Vector3

        # ユニットのフレッシュコピーを作成
        player = MobileSuit.model_validate(player_base.model_dump())
        player.current_hp = player.max_hp
        player.position = Vector3(x=0, y=0, z=0)
        player.side = "PLAYER"
        player.team_id = "PLAYER_TEAM"
        player.strategy_mode = strategy.upper()

        enemies = []
        for e_base in enemies_base:
            e = MobileSuit.model_validate(e_base.model_dump())
            e.current_hp = e.max_hp
            e.strategy_mode = strategy.upper()
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

        is_max_steps = step_count >= self.max_steps
        win_team = self._determine_win_team_bench(sim, player)
        action_counts, strategy_transitions = self._collect_action_and_transitions(
            sim.logs
        )

        # 撃墜数（DESTROYED ログの actor_id をユニットの team_id で分類）
        unit_team_map = {str(u.id): u.team_id for u in sim.units}
        kills: dict[str, int] = {}
        for log in sim.logs:
            if log.action_type == "DESTROYED":
                tid = unit_team_map.get(str(log.actor_id), "UNKNOWN")
                kills[tid] = kills.get(tid, 0) + 1

        survivor_hp_ratio, survivor_count = self._collect_survivor_stats_bench(
            sim.units
        )

        return RoundResult(
            win_team=win_team,
            elapsed_time=sim.elapsed_time,
            action_counts=action_counts,
            strategy_transitions=strategy_transitions,
            kills=kills,
            survivor_hp_ratio=survivor_hp_ratio,
            survivor_count=survivor_count,
            is_max_steps=is_max_steps,
        )

    def _accumulate(self, summary: SimulationSummary, result: RoundResult) -> None:
        """1ラウンドの結果をサマリーに積算する."""
        summary.win_counts[result.win_team] = (
            summary.win_counts.get(result.win_team, 0) + 1
        )
        summary.durations.append(result.elapsed_time)

        for action_type, count in result.action_counts.items():
            summary.action_distribution[action_type] = (
                summary.action_distribution.get(action_type, 0) + count
            )

        for prev, nxt in result.strategy_transitions:
            key = f"{prev} → {nxt}"
            summary.strategy_transition_counts[key] = (
                summary.strategy_transition_counts.get(key, 0) + 1
            )

        for team_id, kill_count in result.kills.items():
            if team_id not in summary.kills_per_round:
                summary.kills_per_round[team_id] = []
            summary.kills_per_round[team_id].append(kill_count)

        if result.is_max_steps and result.win_team == "DRAW":
            summary.draw_by_max_steps += 1

    def _compute_warnings(self, summary: SimulationSummary) -> None:
        """異常検出: 閾値を超えた場合に警告を追加する."""
        if summary.rounds == 0:
            return

        draw_rate = summary.draw_rate
        if draw_rate > BALANCE_WARN_DRAW_RATE:
            summary.warnings.append(
                f"引き分け率が高すぎます ({draw_rate:.1%} > {BALANCE_WARN_DRAW_RATE:.0%}): "
                "戦闘が長期化しすぎている可能性があります"
            )

        for team_id, count in summary.win_counts.items():
            if team_id == "DRAW":
                continue
            win_rate = count / summary.rounds
            if win_rate > BALANCE_WARN_WIN_RATE:
                summary.warnings.append(
                    f"{team_id} の勝率が高すぎます ({win_rate:.1%} > {BALANCE_WARN_WIN_RATE:.0%}): "
                    "バランスが偏っている可能性があります"
                )

        avg_duration = summary.avg_duration
        if avg_duration > BALANCE_WARN_AVG_DURATION:
            summary.warnings.append(
                f"平均戦闘時間が長すぎます ({avg_duration:.1f}s > {BALANCE_WARN_AVG_DURATION:.0f}s): "
                "ステップ数が多すぎる可能性があります"
            )


def run_bench_command(args: Any) -> None:
    """Bench サブコマンドのエントリーポイント."""
    runner = BenchRunner(max_steps=getattr(args, "steps", 5000))
    print(
        f"bench 実行中: mission_id={args.mission_id}, "
        f"strategy={args.strategy}, rounds={args.rounds}"
    )
    summary = runner.run(
        mission_id=args.mission_id,
        rounds=args.rounds,
        strategy=args.strategy,
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

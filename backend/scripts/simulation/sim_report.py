#!/usr/bin/env python3
# backend/scripts/sim_report.py
"""report サブコマンドの実処理: シミュレーション結果JSONからレポートを生成する.

Usage (経由: run_simulation.py):
    python scripts/run_simulation.py report --input data/sim_results/result_*.json
"""

from __future__ import annotations

import glob as glob_module
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


@dataclass
class Report:
    """report コマンドのレポート結果."""

    file_count: int
    total_rounds: int

    # ユニットごとの行動ログ集計（全ファイル合算）
    action_distribution: dict[str, int] = field(default_factory=dict)

    # 戦略遷移ログ集計 (STRATEGY_CHANGED イベント)
    strategy_transitions: dict[str, int] = field(default_factory=dict)

    # 武器選択ログ（武器名ごとの使用回数）
    weapon_usage: dict[str, int] = field(default_factory=dict)

    # ターゲット選択の fuzzy_score 分布（スコアのリスト）
    fuzzy_score_samples: list[float] = field(default_factory=list)

    # 勝敗集計
    win_counts: dict[str, int] = field(default_factory=dict)

    @property
    def action_total(self) -> int:
        """行動ログの総数を返す."""
        return sum(self.action_distribution.values())

    def action_ratio(self, action_type: str) -> float:
        """指定した行動タイプの割合を返す."""
        total = self.action_total
        if total == 0:
            return 0.0
        return self.action_distribution.get(action_type, 0) / total

    @property
    def weapon_total(self) -> int:
        """武器使用ログの総数を返す."""
        return sum(self.weapon_usage.values())

    def weapon_ratio(self, weapon_name: str) -> float:
        """指定した武器の使用割合を返す."""
        total = self.weapon_total
        if total == 0:
            return 0.0
        return self.weapon_usage.get(weapon_name, 0) / total

    def to_text(self) -> str:
        """テキスト形式でレポートを返す."""
        lines = []
        lines.append(
            f"=== Simulation Report: {self.file_count} ファイル, "
            f"{self.total_rounds} ラウンド ==="
        )
        lines.append("")

        # 勝敗集計
        if self.win_counts:
            lines.append("勝敗集計:")
            total = sum(self.win_counts.values())
            for result, count in sorted(self.win_counts.items()):
                pct = count / total * 100 if total > 0 else 0.0
                lines.append(f"  {result}: {count} 回 ({pct:.1f}%)")
            lines.append("")

        # 行動分布
        if self.action_distribution:
            lines.append("行動分布（全ユニット合計）:")
            for action_type, count in sorted(self.action_distribution.items()):
                pct = self.action_ratio(action_type) * 100
                lines.append(f"  {action_type:<12}: {count:6d} 回 ({pct:.1f}%)")
            lines.append("")

        # 戦略遷移
        if self.strategy_transitions:
            lines.append("戦略遷移ログ（STRATEGY_CHANGED）:")
            for transition, count in sorted(
                self.strategy_transitions.items(), key=lambda x: -x[1]
            ):
                lines.append(f"  {transition}: {count} 回")
            lines.append("")

        # 武器選択
        if self.weapon_usage:
            lines.append("武器選択ログ（ATTACK 時の武器使用回数）:")
            for weapon_name, count in sorted(
                self.weapon_usage.items(), key=lambda x: -x[1]
            ):
                pct = self.weapon_ratio(weapon_name) * 100
                lines.append(f"  {weapon_name}: {count} 回 ({pct:.1f}%)")
            lines.append("")

        # ファジィスコア分布（サンプルがある場合）
        if self.fuzzy_score_samples:
            samples = self.fuzzy_score_samples
            avg = sum(samples) / len(samples)
            mn = min(samples)
            mx = max(samples)
            lines.append(
                f"ファジィスコア分布: "
                f"avg={avg:.3f}, min={mn:.3f}, max={mx:.3f}, "
                f"サンプル数={len(samples)}"
            )
            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        """JSON シリアライズ可能な dict を返す."""
        return {
            "file_count": self.file_count,
            "total_rounds": self.total_rounds,
            "win_counts": self.win_counts,
            "action_distribution": self.action_distribution,
            "action_ratios": {
                k: self.action_ratio(k) for k in self.action_distribution
            },
            "strategy_transitions": self.strategy_transitions,
            "weapon_usage": self.weapon_usage,
            "weapon_ratios": {k: self.weapon_ratio(k) for k in self.weapon_usage},
            "fuzzy_score_samples_count": len(self.fuzzy_score_samples),
            "fuzzy_score_avg": (
                sum(self.fuzzy_score_samples) / len(self.fuzzy_score_samples)
                if self.fuzzy_score_samples
                else None
            ),
        }


class ReportGenerator:
    """シミュレーション結果 JSON ファイルを読み込んでレポートを生成する."""

    def from_files(self, paths: list[str | Path]) -> Report:
        """ファイルリストからレポートを生成する.

        Args:
            paths: JSON ファイルパスのリスト（ワイルドカード展開済み）

        Returns:
            Report インスタンス
        """
        resolved: list[Path] = []
        for p in paths:
            expanded = glob_module.glob(str(p))
            if expanded:
                resolved.extend(Path(x) for x in sorted(expanded))
            else:
                resolved.append(Path(p))

        # 存在するファイルのみを対象に
        existing = [p for p in resolved if p.exists()]

        if not existing:
            raise FileNotFoundError(
                f"入力ファイルが見つかりません: {[str(p) for p in resolved]}"
            )

        report = Report(file_count=len(existing), total_rounds=len(existing))

        for file_path in existing:
            with file_path.open(encoding="utf-8") as f:
                data = json.load(f)
            self._process_file(data, report)

        return report

    def _process_file(self, data: dict[str, Any], report: Report) -> None:
        """1ファイル分のデータをレポートに積算する."""
        # 勝敗集計
        win_loss = data.get("win_loss", "UNKNOWN")
        report.win_counts[win_loss] = report.win_counts.get(win_loss, 0) + 1

        logs = data.get("logs", [])
        for log_entry in logs:
            action_type = log_entry.get("action_type", "")

            # 行動分布
            if action_type in {
                "ATTACK",
                "MOVE",
                "USE_SKILL",
                "RETREAT",
                "MISS",
                "DAMAGE",
                "DESTROYED",
            }:
                report.action_distribution[action_type] = (
                    report.action_distribution.get(action_type, 0) + 1
                )

            # 戦略遷移
            if action_type == "STRATEGY_CHANGED":
                details = log_entry.get("details") or {}
                prev = details.get("previous_strategy", "")
                nxt = details.get("new_strategy", "")
                if prev and nxt:
                    key = f"{prev} → {nxt}"
                    report.strategy_transitions[key] = (
                        report.strategy_transitions.get(key, 0) + 1
                    )

            # 武器使用
            if action_type == "ATTACK":
                weapon_name = log_entry.get("weapon_name")
                if weapon_name:
                    report.weapon_usage[weapon_name] = (
                        report.weapon_usage.get(weapon_name, 0) + 1
                    )

            # ファジィスコア
            fuzzy_scores = log_entry.get("fuzzy_scores")
            if fuzzy_scores and isinstance(fuzzy_scores, dict):
                for score_val in fuzzy_scores.values():
                    if isinstance(score_val, (int, float)):
                        report.fuzzy_score_samples.append(float(score_val))


def run_report_command(args: Any) -> None:
    """Report サブコマンドのエントリーポイント."""
    input_patterns = args.input
    generator = ReportGenerator()

    print(f"report 生成中: {len(input_patterns)} パターン")
    try:
        report = generator.from_files(input_patterns)
    except FileNotFoundError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"{report.file_count} ファイルを処理しました")

    output_format = getattr(args, "format", "text")
    output_path = getattr(args, "output", None)

    if output_format == "json":
        content = json.dumps(report.to_json(), ensure_ascii=False, indent=2)
    else:
        content = report.to_text()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(f"結果を保存しました: {out.resolve()}")
    else:
        print(content)

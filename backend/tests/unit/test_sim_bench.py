"""Tests for sim_bench, sim_compare, and sim_report modules (Phase 5-3)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from types import SimpleNamespace
from typing import Any

import pytest

# パスを通す（scripts/ と app/ の両方が使えるようにする）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.models.models import MobileSuit, Vector3, Weapon

# ---------------------------------------------------------------------------
# Helper: テスト用ユニットファクトリ
# ---------------------------------------------------------------------------


def _make_player(strategy_mode: str | None = None) -> MobileSuit:
    return MobileSuit(
        name="Test Gundam",
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=2.0,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="beam_rifle",
                name="Beam Rifle",
                power=30,
                range=500,
                accuracy=85,
            )
        ],
        side="PLAYER",
        team_id="PLAYER_TEAM",
        strategy_mode=strategy_mode,
    )


def _make_enemy(position_x: float = 500.0) -> MobileSuit:
    return MobileSuit(
        name="Zaku II",
        max_hp=80,
        current_hp=80,
        armor=5,
        mobility=1.2,
        position=Vector3(x=position_x, y=0, z=0),
        weapons=[
            Weapon(
                id="zaku_mg",
                name="Zaku Machine Gun",
                power=15,
                range=400,
                accuracy=70,
            )
        ],
        side="ENEMY",
        team_id="ENEMY_TEAM",
    )


def _make_mission(mission_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=mission_id,
        name="テストミッション",
        environment="SPACE",
        special_effects=[],
        enemy_config={"enemies": []},
    )


# ---------------------------------------------------------------------------
# sim_bench テスト
# ---------------------------------------------------------------------------


class TestSimBench:
    """sim_bench のベンチ機能のテスト."""

    def test_bench_summary_structure(self) -> None:
        """Bench 実行結果に win_counts / avg_duration / action_distribution キーが含まれること."""
        from sim_bench import BenchRunner

        player = _make_player()
        enemies = [_make_enemy()]
        mission = _make_mission()

        runner = BenchRunner(max_steps=200)
        summary = runner.run_with_units(
            player_base=player,
            enemies_base=enemies,
            mission=mission,
            rounds=3,
            strategy="AGGRESSIVE",
        )

        # 必須キーの存在確認
        assert hasattr(summary, "win_counts"), "win_counts が存在すること"
        assert hasattr(summary, "durations"), "durations が存在すること"
        assert hasattr(summary, "action_distribution"), (
            "action_distribution が存在すること"
        )

        # win_counts の形式確認
        assert isinstance(summary.win_counts, dict)
        # PLAYER_TEAM / ENEMY_TEAM / DRAW のいずれかが含まれること
        valid_keys = {"PLAYER_TEAM", "ENEMY_TEAM", "DRAW"}
        assert any(k in valid_keys for k in summary.win_counts), (
            f"win_counts のキーが不正: {summary.win_counts}"
        )

        # rounds 分の duration が記録されていること
        assert len(summary.durations) == 3

        # avg_duration は正の実数
        assert summary.avg_duration > 0

        # to_json() が dict を返すこと
        json_data = summary.to_json()
        assert "win_counts" in json_data
        assert "durations" in json_data
        assert "action_distribution" in json_data

    def test_bench_draw_rate_warning(self) -> None:
        """引き分け率 > 20% のとき警告フラグが True になること."""
        from sim_bench import BenchRunner, SimulationSummary

        from app.engine.constants import BALANCE_WARN_DRAW_RATE

        # 大部分が引き分けとなるサマリーを手動で構築して警告計算を検証
        runner = BenchRunner(max_steps=100)
        summary = SimulationSummary(
            mission_id=1,
            strategy="AGGRESSIVE",
            rounds=10,
        )
        summary.win_counts = {"PLAYER_TEAM": 2, "ENEMY_TEAM": 2, "DRAW": 6}
        summary.durations = [50.0] * 10

        # 引き分け率 = 6/10 = 0.6 > 0.20
        assert summary.draw_rate > BALANCE_WARN_DRAW_RATE, (
            f"draw_rate={summary.draw_rate} は BALANCE_WARN_DRAW_RATE={BALANCE_WARN_DRAW_RATE} を超えていること"
        )

        # 警告計算を実行
        runner._compute_warnings(summary)

        assert len(summary.warnings) > 0, "引き分け率超過の警告が生成されること"
        assert any("引き分け" in w for w in summary.warnings), (
            "引き分け率に関する警告が含まれること"
        )

    def test_bench_win_rate_warning(self) -> None:
        """勝率 > 80% のとき不均衡警告フラグが True になること."""
        from sim_bench import BenchRunner, SimulationSummary

        runner = BenchRunner(max_steps=100)
        summary = SimulationSummary(
            mission_id=1,
            strategy="AGGRESSIVE",
            rounds=10,
        )
        # PLAYER_TEAM の勝率 = 9/10 = 0.9 > 0.80
        summary.win_counts = {"PLAYER_TEAM": 9, "ENEMY_TEAM": 1, "DRAW": 0}
        summary.durations = [30.0] * 10

        runner._compute_warnings(summary)

        assert len(summary.warnings) > 0, "勝率超過の警告が生成されること"
        assert any("勝率" in w for w in summary.warnings), (
            "勝率に関する警告が含まれること"
        )

    def test_bench_to_text_output(self) -> None:
        """to_text() が適切なテキストを返すこと."""
        from sim_bench import BenchRunner

        player = _make_player()
        enemies = [_make_enemy()]
        mission = _make_mission()

        runner = BenchRunner(max_steps=200)
        summary = runner.run_with_units(
            player_base=player,
            enemies_base=enemies,
            mission=mission,
            rounds=2,
            strategy="AGGRESSIVE",
        )

        text = summary.to_text()
        assert "Bench Summary" in text
        assert "勝敗分布" in text
        assert "平均戦闘時間" in text


# ---------------------------------------------------------------------------
# sim_compare テスト
# ---------------------------------------------------------------------------


class TestSimCompare:
    """sim_compare の比較機能のテスト."""

    def test_compare_outputs_both_strategies(self) -> None:
        """Compare 結果に strategy_a / strategy_b の統計が含まれること."""
        from sim_compare import CompareRunner

        player = _make_player()
        enemies = [_make_enemy()]
        mission = _make_mission()

        runner = CompareRunner(max_steps=200)
        summary = runner.run_with_units(
            player_base=player,
            enemies_base=enemies,
            mission=mission,
            rounds=3,
            strategy_a="AGGRESSIVE",
            strategy_b="DEFENSIVE",
        )

        # strategy_a / strategy_b の統計が存在すること
        assert summary.strategy_a == "AGGRESSIVE"
        assert summary.strategy_b == "DEFENSIVE"
        assert hasattr(summary, "stats_a")
        assert hasattr(summary, "stats_b")

        # to_json() の内容確認
        json_data = summary.to_json()
        assert "strategy_a" in json_data
        assert "strategy_b" in json_data
        assert "stats_a" in json_data
        assert "stats_b" in json_data
        assert json_data["strategy_a"] == "AGGRESSIVE"
        assert json_data["strategy_b"] == "DEFENSIVE"

        # rounds 分の統計が積算されていること
        assert summary.stats_a.rounds == 3
        assert summary.stats_b.rounds == 3

        # 勝利 + 引き分けの合計が rounds と一致すること
        total = (
            summary.stats_a.win_count + summary.stats_b.win_count + summary.draw_count
        )
        assert total == 3, f"勝利 + 引き分けの合計={total} が rounds=3 と一致すること"

    def test_compare_to_text_output(self) -> None:
        """to_text() が両戦略のヘッダーを含むテキストを返すこと."""
        from sim_compare import CompareRunner

        player = _make_player()
        enemies = [_make_enemy()]
        mission = _make_mission()

        runner = CompareRunner(max_steps=200)
        summary = runner.run_with_units(
            player_base=player,
            enemies_base=enemies,
            mission=mission,
            rounds=2,
            strategy_a="AGGRESSIVE",
            strategy_b="DEFENSIVE",
        )

        text = summary.to_text()
        assert "Compare" in text
        assert "AGGRESSIVE" in text
        assert "DEFENSIVE" in text


# ---------------------------------------------------------------------------
# sim_report テスト
# ---------------------------------------------------------------------------


def _make_sim_result_json(
    win_loss: str = "WIN",
    action_logs: list[dict] | None = None,
    strategy_changed_logs: list[dict] | None = None,
) -> dict[str, Any]:
    """テスト用シミュレーション結果 JSON データを生成する."""
    logs: list[dict] = []

    if action_logs:
        logs.extend(action_logs)

    if strategy_changed_logs:
        logs.extend(strategy_changed_logs)

    return {
        "mission_id": 1,
        "mission_name": "テストミッション",
        "environment": "SPACE",
        "win_loss": win_loss,
        "elapsed_time": 42.0,
        "step_count": 420,
        "kills": 1,
        "player": {"name": "Gundam", "final_hp": 80, "max_hp": 100},
        "enemies": [{"name": "Zaku II", "final_hp": 0, "max_hp": 80}],
        "logs": logs,
    }


class TestSimReport:
    """sim_report のレポート機能のテスト."""

    def test_report_parses_action_logs(self) -> None:
        """既存のログ JSON から行動分布が正しく集計されること."""
        from sim_report import ReportGenerator

        logs = [
            {
                "action_type": "ATTACK",
                "weapon_name": "Beam Rifle",
                "actor_id": "00000000-0000-0000-0000-000000000001",
                "timestamp": 1.0,
                "message": "攻撃",
            },
            {
                "action_type": "ATTACK",
                "weapon_name": "Beam Rifle",
                "actor_id": "00000000-0000-0000-0000-000000000001",
                "timestamp": 2.0,
                "message": "攻撃",
            },
            {
                "action_type": "MOVE",
                "actor_id": "00000000-0000-0000-0000-000000000001",
                "timestamp": 3.0,
                "message": "移動",
            },
            {
                "action_type": "USE_SKILL",
                "actor_id": "00000000-0000-0000-0000-000000000001",
                "timestamp": 4.0,
                "message": "スキル使用",
            },
            {
                "action_type": "DAMAGE",
                "actor_id": "00000000-0000-0000-0000-000000000002",
                "timestamp": 5.0,
                "message": "ダメージ",
            },
        ]
        data = _make_sim_result_json(win_loss="WIN", action_logs=logs)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f, ensure_ascii=False)
            tmp_path = f.name

        try:
            generator = ReportGenerator()
            report = generator.from_files([tmp_path])

            assert report.action_distribution.get("ATTACK", 0) == 2
            assert report.action_distribution.get("MOVE", 0) == 1
            assert report.action_distribution.get("USE_SKILL", 0) == 1
            assert report.action_distribution.get("DAMAGE", 0) == 1

            # 武器使用回数
            assert report.weapon_usage.get("Beam Rifle", 0) == 2
        finally:
            os.unlink(tmp_path)

    def test_report_parses_strategy_changed_logs(self) -> None:
        """STRATEGY_CHANGED ログが正しくカウントされること."""
        from sim_report import ReportGenerator

        strategy_logs = [
            {
                "action_type": "STRATEGY_CHANGED",
                "actor_id": "00000000-0000-0000-0000-000000000000",
                "timestamp": 10.0,
                "message": "AGGRESSIVE → DEFENSIVE",
                "team_id": "PLAYER_TEAM",
                "strategy_mode": "DEFENSIVE",
                "details": {
                    "previous_strategy": "AGGRESSIVE",
                    "new_strategy": "DEFENSIVE",
                },
            },
            {
                "action_type": "STRATEGY_CHANGED",
                "actor_id": "00000000-0000-0000-0000-000000000000",
                "timestamp": 20.0,
                "message": "AGGRESSIVE → DEFENSIVE",
                "team_id": "ENEMY_TEAM",
                "strategy_mode": "DEFENSIVE",
                "details": {
                    "previous_strategy": "AGGRESSIVE",
                    "new_strategy": "DEFENSIVE",
                },
            },
            {
                "action_type": "STRATEGY_CHANGED",
                "actor_id": "00000000-0000-0000-0000-000000000000",
                "timestamp": 30.0,
                "message": "DEFENSIVE → RETREAT",
                "team_id": "PLAYER_TEAM",
                "strategy_mode": "RETREAT",
                "details": {
                    "previous_strategy": "DEFENSIVE",
                    "new_strategy": "RETREAT",
                },
            },
        ]
        data = _make_sim_result_json(
            win_loss="LOSE", strategy_changed_logs=strategy_logs
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f, ensure_ascii=False)
            tmp_path = f.name

        try:
            generator = ReportGenerator()
            report = generator.from_files([tmp_path])

            assert report.strategy_transitions.get("AGGRESSIVE → DEFENSIVE", 0) == 2
            assert report.strategy_transitions.get("DEFENSIVE → RETREAT", 0) == 1
        finally:
            os.unlink(tmp_path)

    def test_report_multiple_files(self) -> None:
        """複数ファイルの行動分布が合算されること."""
        from sim_report import ReportGenerator

        logs1 = [
            {
                "action_type": "ATTACK",
                "weapon_name": "Beam Rifle",
                "actor_id": "00000000-0000-0000-0000-000000000001",
                "timestamp": 1.0,
                "message": "攻撃",
            },
        ]
        logs2 = [
            {
                "action_type": "ATTACK",
                "weapon_name": "Beam Rifle",
                "actor_id": "00000000-0000-0000-0000-000000000002",
                "timestamp": 1.0,
                "message": "攻撃",
            },
            {
                "action_type": "MOVE",
                "actor_id": "00000000-0000-0000-0000-000000000002",
                "timestamp": 2.0,
                "message": "移動",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = os.path.join(tmpdir, "result_1.json")
            f2 = os.path.join(tmpdir, "result_2.json")
            with open(f1, "w", encoding="utf-8") as fp:
                json.dump(_make_sim_result_json(win_loss="WIN", action_logs=logs1), fp)
            with open(f2, "w", encoding="utf-8") as fp:
                json.dump(_make_sim_result_json(win_loss="LOSE", action_logs=logs2), fp)

            generator = ReportGenerator()
            report = generator.from_files([f1, f2])

            assert report.file_count == 2
            assert report.action_distribution.get("ATTACK", 0) == 2
            assert report.action_distribution.get("MOVE", 0) == 1

    def test_report_file_not_found_raises(self) -> None:
        """存在しないファイルを指定したとき FileNotFoundError が発生すること."""
        from sim_report import ReportGenerator

        generator = ReportGenerator()
        with pytest.raises(FileNotFoundError):
            generator.from_files(["/nonexistent/path/result.json"])

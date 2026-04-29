"""Integration tests for Battle Engine Phase 4-3: Dynamic StrategyMode transitions.

本ファイルでは BattleSimulator を実際に実行し、戦況に応じた StrategyMode 動的変更が
正しく機能することを検証する。
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.engine.simulation import BattleSimulator
from app.engine.strategy_controller import TeamMetrics, TeamStrategyController
from app.models.models import MobileSuit, RetreatPoint, Vector3, Weapon


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_unit(
    name: str,
    team_id: str,
    hp: int = 100,
    strategy_mode: str | None = None,
    position: Vector3 | None = None,
) -> MobileSuit:
    """テスト用ユニットを生成する."""
    return MobileSuit(
        name=name,
        max_hp=hp,
        current_hp=hp,
        armor=0,
        mobility=1.0,
        position=position or Vector3(x=0.0, y=0.0, z=0.0),
        weapons=[
            Weapon(
                id="rifle",
                name="Beam Rifle",
                power=20,
                range=500,
                accuracy=80,
            )
        ],
        side="PLAYER",
        team_id=team_id,
        strategy_mode=strategy_mode,
    )


def _make_metrics(
    team_id: str = "TEAM_A",
    current_strategy: str = "AGGRESSIVE",
    avg_hp_ratio: float = 1.0,
    alive_ratio: float = 1.0,
    min_hp_ratio: float = 1.0,
    alive_count: int = 3,
    total_count: int = 3,
    retreat_points_empty: bool = False,
) -> TeamMetrics:
    """テスト用 TeamMetrics を生成するヘルパー."""
    return TeamMetrics(
        team_id=team_id,
        alive_count=alive_count,
        total_count=total_count,
        alive_ratio=alive_ratio,
        avg_hp_ratio=avg_hp_ratio,
        min_hp_ratio=min_hp_ratio,
        current_strategy=current_strategy,
        elapsed_time=10.0,
        retreat_points_empty=retreat_points_empty,
    )


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


def test_strategy_transitions_logged_during_battle() -> None:
    """シミュレーション全体で STRATEGY_CHANGED ログが1件以上記録されること."""
    player = _make_unit("Player", "TEAM_P", hp=100, position=Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "TEAM_E", hp=100, position=Vector3(x=3000, y=0, z=0))
    retreat_point = RetreatPoint(position=Vector3(x=100, y=0, z=100), radius=200.0)

    sim = BattleSimulator(
        player, [enemy], retreat_points=[retreat_point], strategy_update_interval=1
    )
    controller = sim._strategy_controllers["TEAM_P"]
    controller.current_strategy = "AGGRESSIVE"

    # T01 トリガー条件を持つメトリクスを差し込む
    mock_metrics = _make_metrics(
        team_id="TEAM_P",
        current_strategy="AGGRESSIVE",
        avg_hp_ratio=0.25,
        alive_ratio=0.40,
        retreat_points_empty=False,
    )

    with patch.object(sim, "_collect_team_metrics", return_value=mock_metrics):
        controller._step_counter = 0
        sim._strategy_phase()

    strategy_logs = [log for log in sim.logs if log.action_type == "STRATEGY_CHANGED"]
    assert len(strategy_logs) >= 1, "STRATEGY_CHANGED ログが1件以上記録されること"


def test_all_strategy_modes_trigger_correct_ruleset() -> None:
    """各 StrategyMode で対応する遷移ルールが正しく適用されること."""
    player = _make_unit("Player", "TEAM_P", hp=100, position=Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "TEAM_E", hp=100, position=Vector3(x=3000, y=0, z=0))
    retreat_point = RetreatPoint(position=Vector3(x=100, y=0, z=100), radius=200.0)

    test_cases = [
        # (initial_strategy, metrics_kwargs, expected_transition, expected_rule_id)
        (
            "AGGRESSIVE",
            {"avg_hp_ratio": 0.25, "alive_ratio": 0.40},
            "RETREAT",
            "T01",
        ),
        (
            "AGGRESSIVE",
            {"avg_hp_ratio": 0.45, "alive_ratio": 0.55},
            "DEFENSIVE",
            "T02",
        ),
        (
            "DEFENSIVE",
            {"avg_hp_ratio": 0.80, "alive_ratio": 0.90},
            "AGGRESSIVE",
            "T04",
        ),
        (
            "SNIPER",
            {"avg_hp_ratio": 0.45, "alive_ratio": 1.0},
            "DEFENSIVE",
            "T06",
        ),
        (
            "ASSAULT",
            {"avg_hp_ratio": 0.30, "alive_ratio": 0.40},
            "RETREAT",
            "T07",
        ),
    ]

    for initial_strategy, metrics_kwargs, expected_new_strategy, expected_rule_id in test_cases:
        sim = BattleSimulator(
            player, [enemy], retreat_points=[retreat_point], strategy_update_interval=1
        )
        controller = sim._strategy_controllers["TEAM_P"]
        controller.current_strategy = initial_strategy
        player.strategy_mode = initial_strategy

        mock_metrics = _make_metrics(
            team_id="TEAM_P",
            current_strategy=initial_strategy,
            retreat_points_empty=False,
            **metrics_kwargs,
        )

        def _mock_collect(team_id: str, _m: TeamMetrics = mock_metrics) -> TeamMetrics:
            return _m

        with patch.object(sim, "_collect_team_metrics", side_effect=_mock_collect):
            controller._step_counter = 0
            sim._strategy_phase()

        # TEAM_P のログのみを検証
        team_p_logs = [
            log
            for log in sim.logs
            if log.action_type == "STRATEGY_CHANGED" and log.team_id == "TEAM_P"
        ]
        assert len(team_p_logs) >= 1, (
            f"{initial_strategy} → {expected_new_strategy} の遷移ログが記録されること"
        )
        assert team_p_logs[-1].strategy_mode == expected_new_strategy, (
            f"{initial_strategy} → {expected_new_strategy} の遷移が正しく適用されること "
            f"(実際: {team_p_logs[-1].strategy_mode})"
        )
        assert team_p_logs[-1].details is not None
        assert team_p_logs[-1].details.get("rule_id") == expected_rule_id, (
            f"rule_id={expected_rule_id} が期待されるが "
            f"得られた rule_id={team_p_logs[-1].details.get('rule_id')}"
        )


def test_three_team_battle_with_dynamic_strategy() -> None:
    """3チーム乱戦でそれぞれ独立した戦略評価が動作すること."""
    # 3チーム構成: TEAM_P, TEAM_A, TEAM_B
    player = _make_unit(
        "Player", "TEAM_P", hp=100, position=Vector3(x=0, y=0, z=0), strategy_mode="AGGRESSIVE"
    )
    enemy_a = _make_unit(
        "EnemyA", "TEAM_A", hp=100, position=Vector3(x=2000, y=0, z=0), strategy_mode="AGGRESSIVE"
    )
    enemy_b = _make_unit(
        "EnemyB", "TEAM_B", hp=100, position=Vector3(x=4000, y=0, z=0), strategy_mode="DEFENSIVE"
    )

    retreat_point = RetreatPoint(position=Vector3(x=100, y=0, z=100), radius=200.0)
    sim = BattleSimulator(
        player,
        [enemy_a, enemy_b],
        retreat_points=[retreat_point],
        strategy_update_interval=1,
    )

    # 各チームの初期戦略を設定
    for team_id, strategy in [
        ("TEAM_P", "AGGRESSIVE"),
        ("TEAM_A", "AGGRESSIVE"),
        ("TEAM_B", "DEFENSIVE"),
    ]:
        sim._strategy_controllers[team_id].current_strategy = strategy

    # TEAM_P: T01 条件 → RETREAT（撤退ポイントあり → RETREAT 維持）
    metrics_p = _make_metrics(
        team_id="TEAM_P",
        current_strategy="AGGRESSIVE",
        avg_hp_ratio=0.25,
        alive_ratio=0.40,
        retreat_points_empty=False,
    )
    # TEAM_A: T02 条件 → DEFENSIVE
    metrics_a = _make_metrics(
        team_id="TEAM_A",
        current_strategy="AGGRESSIVE",
        avg_hp_ratio=0.45,
        alive_ratio=0.55,
        retreat_points_empty=False,
    )
    # TEAM_B: T04 条件 → AGGRESSIVE（体勢回復）
    metrics_b = _make_metrics(
        team_id="TEAM_B",
        current_strategy="DEFENSIVE",
        avg_hp_ratio=0.80,
        alive_ratio=0.90,
        retreat_points_empty=False,
    )

    metrics_map = {
        "TEAM_P": metrics_p,
        "TEAM_A": metrics_a,
        "TEAM_B": metrics_b,
    }

    def _mock_collect(team_id: str) -> TeamMetrics:
        return metrics_map[team_id]

    with patch.object(sim, "_collect_team_metrics", side_effect=_mock_collect):
        for ctrl in sim._strategy_controllers.values():
            ctrl._step_counter = 0
        sim._strategy_phase()

    strategy_logs = [log for log in sim.logs if log.action_type == "STRATEGY_CHANGED"]
    assert len(strategy_logs) >= 1, "3チーム乱戦で戦略変更ログが1件以上記録されること"

    # 各チームのコントローラが独立して更新されていること
    log_team_ids = {log.team_id for log in strategy_logs}
    assert len(log_team_ids) >= 2, "複数チームで独立した戦略変更が行われること"

    # TEAM_P は RETREAT（撤退ポイントありのため T01 が RETREAT になる）
    team_p_logs = [log for log in strategy_logs if log.team_id == "TEAM_P"]
    assert len(team_p_logs) >= 1
    assert team_p_logs[-1].strategy_mode == "RETREAT"
    assert team_p_logs[-1].details is not None
    assert team_p_logs[-1].details.get("rule_id") == "T01"

    # TEAM_A は T02 で DEFENSIVE
    team_a_logs = [log for log in strategy_logs if log.team_id == "TEAM_A"]
    assert len(team_a_logs) >= 1
    assert team_a_logs[-1].strategy_mode == "DEFENSIVE"
    assert team_a_logs[-1].details is not None
    assert team_a_logs[-1].details.get("rule_id") == "T02"

    # TEAM_B は T04 で AGGRESSIVE（体勢回復）
    team_b_logs = [log for log in strategy_logs if log.team_id == "TEAM_B"]
    assert len(team_b_logs) >= 1
    assert team_b_logs[-1].strategy_mode == "AGGRESSIVE"
    assert team_b_logs[-1].details is not None
    assert team_b_logs[-1].details.get("rule_id") == "T04"

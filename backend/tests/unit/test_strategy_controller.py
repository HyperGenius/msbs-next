"""Tests for TeamStrategyController and TeamMetrics (Phase 4-2)."""

import pytest

from app.engine.simulation import BattleSimulator
from app.engine.strategy_controller import (
    TeamMetrics,
    TeamStrategyController,
)
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


# ---------------------------------------------------------------------------
# TeamStrategyController unit tests
# ---------------------------------------------------------------------------


def test_controller_initializes_with_default_strategy() -> None:
    """初期化後 current_strategy が "AGGRESSIVE" になっていること."""
    ctrl = TeamStrategyController(team_id="TEAM_A")
    assert ctrl.current_strategy == "AGGRESSIVE"


def test_controller_initializes_with_custom_strategy() -> None:
    """initial_strategy を指定した場合にその値が current_strategy に設定されること."""
    ctrl = TeamStrategyController(team_id="TEAM_A", initial_strategy="DEFENSIVE")
    assert ctrl.current_strategy == "DEFENSIVE"


def test_should_evaluate_at_correct_interval() -> None:
    """update_interval=10 のとき 10 ステップ目に should_evaluate() が True を返すこと."""
    ctrl = TeamStrategyController(team_id="TEAM_A", update_interval=10)

    # 1〜9 ステップ目は False
    for _ in range(9):
        assert ctrl.should_evaluate() is False

    # 10 ステップ目は True
    assert ctrl.should_evaluate() is True


def test_should_evaluate_skips_step_zero() -> None:
    """バトル開始直後（_step_counter が 0 の状態）では評価されないこと.

    should_evaluate() は呼び出すたびに _step_counter をインクリメントするため、
    最初の呼び出しは 1 ステップ目に相当し、update_interval=1 でなければ False。
    """
    ctrl = TeamStrategyController(team_id="TEAM_A", update_interval=10)
    # 最初の呼び出しは _step_counter が 1 になるだけで、10 の倍数ではない
    assert ctrl.should_evaluate() is False


def test_apply_updates_active_units_strategy() -> None:
    """apply() が ACTIVE ユニットの strategy_mode を一括更新すること."""
    ctrl = TeamStrategyController(team_id="TEAM_A", initial_strategy="AGGRESSIVE")

    unit_a = _make_unit("UnitA", "TEAM_A", strategy_mode="AGGRESSIVE")
    unit_b = _make_unit("UnitB", "TEAM_A", strategy_mode="AGGRESSIVE")

    resource_a = {"status": "ACTIVE"}
    resource_b = {"status": "ACTIVE"}

    ctrl.apply("DEFENSIVE", [(unit_a, resource_a), (unit_b, resource_b)])

    assert unit_a.strategy_mode == "DEFENSIVE"
    assert unit_b.strategy_mode == "DEFENSIVE"
    assert ctrl.current_strategy == "DEFENSIVE"


def test_apply_does_not_update_destroyed_units() -> None:
    """apply() が DESTROYED / RETREATED ユニットを更新しないこと."""
    ctrl = TeamStrategyController(team_id="TEAM_A", initial_strategy="AGGRESSIVE")

    unit_active = _make_unit("Active", "TEAM_A", strategy_mode="AGGRESSIVE")
    unit_destroyed = _make_unit("Destroyed", "TEAM_A", strategy_mode="AGGRESSIVE")
    unit_retreated = _make_unit("Retreated", "TEAM_A", strategy_mode="AGGRESSIVE")

    res_active = {"status": "ACTIVE"}
    res_destroyed = {"status": "DESTROYED"}
    res_retreated = {"status": "RETREATED"}

    ctrl.apply(
        "SNIPER",
        [
            (unit_active, res_active),
            (unit_destroyed, res_destroyed),
            (unit_retreated, res_retreated),
        ],
    )

    assert unit_active.strategy_mode == "SNIPER"
    assert unit_destroyed.strategy_mode == "AGGRESSIVE"  # 変更されていない
    assert unit_retreated.strategy_mode == "AGGRESSIVE"  # 変更されていない


# ---------------------------------------------------------------------------
# TeamMetrics tests
# ---------------------------------------------------------------------------


def test_team_metrics_calculated_correctly() -> None:
    """TeamMetrics の alive_ratio / avg_hp_ratio / min_hp_ratio が正しく算出されること."""
    player = _make_unit("Player", "TEAM_P", hp=100, position=Vector3(x=0, y=0, z=0))
    player.current_hp = 80  # HP: 80/100

    enemy = _make_unit("Enemy", "TEAM_E", hp=100, position=Vector3(x=3000, y=0, z=0))
    enemy.current_hp = 100  # HP: 100/100

    sim = BattleSimulator(player, [enemy])

    metrics = sim._collect_team_metrics("TEAM_P")

    assert metrics.team_id == "TEAM_P"
    assert metrics.alive_count == 1
    assert metrics.total_count == 1
    assert metrics.alive_ratio == pytest.approx(1.0)
    assert metrics.avg_hp_ratio == pytest.approx(0.8)
    assert metrics.min_hp_ratio == pytest.approx(0.8)


def test_team_metrics_excludes_destroyed_units() -> None:
    """DESTROYED ユニットは alive_count / avg_hp_ratio の計算から除外されること."""
    player = _make_unit("Player", "TEAM_P", hp=100, position=Vector3(x=0, y=0, z=0))
    player.current_hp = 50  # HP: 50/100

    enemy = _make_unit("Enemy", "TEAM_E", hp=100, position=Vector3(x=3000, y=0, z=0))

    sim = BattleSimulator(player, [enemy])
    # プレイヤーを DESTROYED に設定
    sim.unit_resources[str(player.id)]["status"] = "DESTROYED"
    player.current_hp = 0

    metrics = sim._collect_team_metrics("TEAM_P")

    assert metrics.alive_count == 0
    assert metrics.total_count == 1
    assert metrics.alive_ratio == pytest.approx(0.0)
    assert metrics.avg_hp_ratio == pytest.approx(0.0)
    assert metrics.min_hp_ratio == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# BattleSimulator._strategy_phase() integration tests
# ---------------------------------------------------------------------------


class _AlwaysChangeController(TeamStrategyController):
    """テスト用: 常に "DEFENSIVE" を返すコントローラ."""

    def evaluate(self, team_metrics: TeamMetrics) -> str | None:
        return "DEFENSIVE"


def test_strategy_phase_logs_strategy_changed() -> None:
    """_strategy_phase() で戦略変更が発生したとき STRATEGY_CHANGED ログが記録されること."""
    player = _make_unit("Player", "TEAM_P", position=Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "TEAM_E", position=Vector3(x=3000, y=0, z=0))

    # update_interval=1 で毎ステップ評価するシミュレータを作成
    sim = BattleSimulator(player, [enemy], strategy_update_interval=1)

    # プレイヤーチームのコントローラを差し替え
    sim._strategy_controllers["TEAM_P"] = _AlwaysChangeController(
        team_id="TEAM_P",
        initial_strategy="AGGRESSIVE",
        update_interval=1,
    )

    sim._strategy_phase()

    strategy_logs = [log for log in sim.logs if log.action_type == "STRATEGY_CHANGED"]
    assert len(strategy_logs) >= 1

    log = strategy_logs[0]
    assert log.team_id == "TEAM_P"
    assert log.strategy_mode == "DEFENSIVE"
    assert log.details is not None
    assert log.details["previous_strategy"] == "AGGRESSIVE"
    assert "trigger_metrics" in log.details


def test_strategy_phase_no_change_no_log() -> None:
    """戦略変更がない場合は STRATEGY_CHANGED ログが記録されないこと.

    デフォルトの TeamStrategyController.evaluate() は None を返すため、
    ログが記録されない。
    """
    player = _make_unit("Player", "TEAM_P", position=Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "TEAM_E", position=Vector3(x=3000, y=0, z=0))

    # update_interval=1 で毎ステップ評価するが evaluate() は None を返す
    sim = BattleSimulator(player, [enemy], strategy_update_interval=1)
    sim._strategy_phase()

    strategy_logs = [log for log in sim.logs if log.action_type == "STRATEGY_CHANGED"]
    assert len(strategy_logs) == 0


# ---------------------------------------------------------------------------
# Phase 4-3: StrategyTransitionRule / evaluate() tests
# ---------------------------------------------------------------------------


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


def test_t01_aggressive_heavy_damage_retreats() -> None:
    """T01: AGGRESSIVE + avg_hp < 0.30 + alive_ratio < 0.50 → RETREAT."""
    ctrl = TeamStrategyController(team_id="TEAM_A", initial_strategy="AGGRESSIVE")
    metrics = _make_metrics(
        current_strategy="AGGRESSIVE",
        avg_hp_ratio=0.25,
        alive_ratio=0.40,
    )
    result = ctrl.evaluate(metrics)
    assert result == "RETREAT"
    assert ctrl._last_matched_rule_id == "T01"


def test_t02_aggressive_disadvantage_defends() -> None:
    """T02: AGGRESSIVE + avg_hp < 0.50 + alive_ratio < 0.60 → DEFENSIVE."""
    ctrl = TeamStrategyController(team_id="TEAM_A", initial_strategy="AGGRESSIVE")
    metrics = _make_metrics(
        current_strategy="AGGRESSIVE",
        avg_hp_ratio=0.45,
        alive_ratio=0.55,
    )
    result = ctrl.evaluate(metrics)
    assert result == "DEFENSIVE"
    assert ctrl._last_matched_rule_id == "T02"


def test_t04_defensive_recovery_attacks() -> None:
    """T04: DEFENSIVE + avg_hp >= 0.65 + alive_ratio >= 0.70 → AGGRESSIVE."""
    ctrl = TeamStrategyController(team_id="TEAM_A", initial_strategy="DEFENSIVE")
    metrics = _make_metrics(
        current_strategy="DEFENSIVE",
        avg_hp_ratio=0.80,
        alive_ratio=0.90,
    )
    result = ctrl.evaluate(metrics)
    assert result == "AGGRESSIVE"
    assert ctrl._last_matched_rule_id == "T04"


def test_t07_assault_near_wipe_retreats() -> None:
    """T07: ASSAULT + avg_hp < 0.35 + alive_ratio < 0.50 → RETREAT."""
    ctrl = TeamStrategyController(team_id="TEAM_A", initial_strategy="ASSAULT")
    metrics = _make_metrics(
        current_strategy="ASSAULT",
        avg_hp_ratio=0.30,
        alive_ratio=0.40,
    )
    result = ctrl.evaluate(metrics)
    assert result == "RETREAT"
    assert ctrl._last_matched_rule_id == "T07"


def test_no_transition_when_conditions_not_met() -> None:
    """条件未満の場合は evaluate() が None を返すこと."""
    ctrl = TeamStrategyController(team_id="TEAM_A", initial_strategy="AGGRESSIVE")
    # 高HP・高生存率 → いずれのルールも条件未達
    metrics = _make_metrics(
        current_strategy="AGGRESSIVE",
        avg_hp_ratio=0.85,
        alive_ratio=0.90,
    )
    result = ctrl.evaluate(metrics)
    assert result is None
    assert ctrl._last_matched_rule_id is None


def test_retreat_blocked_when_no_retreat_points() -> None:
    """撤退ポイントなし + evaluate()='RETREAT' → _strategy_phase() で 'DEFENSIVE' にフォールバック."""
    player = _make_unit(
        "Player",
        "TEAM_P",
        hp=100,
        position=Vector3(x=0, y=0, z=0),
        strategy_mode="AGGRESSIVE",
    )
    player.current_hp = 20  # 重傷
    enemy = _make_unit("Enemy", "TEAM_E", hp=100, position=Vector3(x=3000, y=0, z=0))

    # retreat_points なし + update_interval=1 で毎ステップ評価
    sim = BattleSimulator(player, [enemy], strategy_update_interval=1)

    # TEAM_P のコントローラを AGGRESSIVE に設定し強制的に T01 条件を満たす
    controller = sim._strategy_controllers["TEAM_P"]
    controller.current_strategy = "AGGRESSIVE"
    player.strategy_mode = "AGGRESSIVE"

    # メトリクスを直接差し込み、T01 が適用されることを確認
    from unittest.mock import patch

    mock_metrics = _make_metrics(
        team_id="TEAM_P",
        current_strategy="AGGRESSIVE",
        avg_hp_ratio=0.25,
        alive_ratio=0.40,
        retreat_points_empty=True,
    )

    with patch.object(sim, "_collect_team_metrics", return_value=mock_metrics):
        # should_evaluate を True にするためカウンターを進める
        controller._step_counter = 0
        sim._strategy_phase()

    strategy_logs = [log for log in sim.logs if log.action_type == "STRATEGY_CHANGED"]
    assert len(strategy_logs) >= 1
    # RETREAT ではなく DEFENSIVE に変更されていること
    last_log = strategy_logs[-1]
    assert last_log.strategy_mode == "DEFENSIVE"
    assert last_log.details is not None
    assert last_log.details.get("rule_id") == "T10"


def test_rule_priority_first_match_wins() -> None:
    """複数条件マッチ時は最初のルール（T01 優先）を採用すること."""
    ctrl = TeamStrategyController(team_id="TEAM_A", initial_strategy="AGGRESSIVE")
    # T01 条件 (avg_hp < 0.30, alive_ratio < 0.50) も T02 条件 (avg_hp < 0.50, alive_ratio < 0.60) も満たす
    metrics = _make_metrics(
        current_strategy="AGGRESSIVE",
        avg_hp_ratio=0.20,
        alive_ratio=0.30,
    )
    result = ctrl.evaluate(metrics)
    # T01 が先にマッチするため RETREAT を返す
    assert result == "RETREAT"
    assert ctrl._last_matched_rule_id == "T01"


def test_strategy_changed_log_contains_rule_id() -> None:
    """STRATEGY_CHANGED ログの details.rule_id にマッチしたルールIDが含まれること."""
    player = _make_unit(
        "Player",
        "TEAM_P",
        hp=100,
        position=Vector3(x=0, y=0, z=0),
        strategy_mode="AGGRESSIVE",
    )
    enemy = _make_unit("Enemy", "TEAM_E", hp=100, position=Vector3(x=3000, y=0, z=0))

    # 撤退ポイントを設定して T01 → RETREAT が最終適用されるようにする
    retreat_point = RetreatPoint(position=Vector3(x=100, y=0, z=100), radius=200.0)
    sim = BattleSimulator(
        player, [enemy], retreat_points=[retreat_point], strategy_update_interval=1
    )

    controller = sim._strategy_controllers["TEAM_P"]
    controller.current_strategy = "AGGRESSIVE"
    player.strategy_mode = "AGGRESSIVE"

    from unittest.mock import patch

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
    assert len(strategy_logs) >= 1
    log = strategy_logs[-1]
    assert log.details is not None
    assert "rule_id" in log.details
    assert log.details["rule_id"] == "T01"
    assert "trigger_metrics" in log.details


def test_full_simulation_strategy_changes() -> None:
    """フルシミュレーションでチームが AGGRESSIVE → DEFENSIVE と遷移すること."""
    from unittest.mock import patch

    player = _make_unit(
        "Player",
        "TEAM_P",
        hp=100,
        position=Vector3(x=0, y=0, z=0),
        strategy_mode="AGGRESSIVE",
    )
    enemy = _make_unit(
        "Enemy",
        "TEAM_E",
        hp=100,
        position=Vector3(x=3000, y=0, z=0),
        strategy_mode="AGGRESSIVE",
    )

    sim = BattleSimulator(player, [enemy], strategy_update_interval=1)
    controller = sim._strategy_controllers["TEAM_P"]
    controller.current_strategy = "AGGRESSIVE"
    player.strategy_mode = "AGGRESSIVE"

    # T02 条件を満たすメトリクス: avg_hp_ratio=0.45 < 0.50, alive_ratio=0.55 < 0.60
    mock_metrics = _make_metrics(
        team_id="TEAM_P",
        current_strategy="AGGRESSIVE",
        avg_hp_ratio=0.45,
        alive_ratio=0.55,
        retreat_points_empty=True,  # RETREAT 遷移がある場合でも DEFENSIVE にフォールバック
    )

    logged_transitions: list[str] = []

    _ = sim._strategy_phase.__func__

    # メトリクスを固定してステップを重ねる（戦略が変わった後は条件が更新される）
    with patch.object(sim, "_collect_team_metrics", return_value=mock_metrics):
        # 1回目: AGGRESSIVE → DEFENSIVE (T02)
        controller._step_counter = 0
        sim._strategy_phase()

    strategy_logs = [log for log in sim.logs if log.action_type == "STRATEGY_CHANGED"]
    # 少なくとも 1 件の戦略変更ログが記録されること
    assert len(strategy_logs) >= 1
    logged_transitions = [log.strategy_mode for log in strategy_logs]
    assert "DEFENSIVE" in logged_transitions

    # rule_id が詳細に含まれること
    for log in strategy_logs:
        assert log.details is not None
        assert "rule_id" in log.details

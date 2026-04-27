"""FuzzyEngine のユニットテスト."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from app.engine.fuzzy_engine import (
    FuzzyEngine,
    FuzzyRuleSet,
    TriangleMF,
    TrapezoidMF,
    _fuzzify,
    _evaluate_rules,
    _defuzzify_centroid,
    FuzzyCondition,
    FuzzyOutput,
    FuzzyRule,
)

# ---------------------------------------------------------------------------
# TriangleMF
# ---------------------------------------------------------------------------

_FUZZY_RULES_DIR = Path(__file__).parent.parent.parent / "data" / "fuzzy_rules"


class TestTriangleMF:
    """三角形型メンバーシップ関数のテスト."""

    def test_peak_returns_one(self) -> None:
        """頂点でメンバーシップ度が 1.0 になる."""
        mf = TriangleMF(0.0, 0.5, 1.0)
        assert mf.evaluate(0.5) == pytest.approx(1.0)

    def test_left_boundary_returns_zero(self) -> None:
        """左端でメンバーシップ度が 0.0 になる."""
        mf = TriangleMF(0.0, 0.5, 1.0)
        assert mf.evaluate(0.0) == pytest.approx(0.0)

    def test_right_boundary_returns_zero(self) -> None:
        """右端でメンバーシップ度が 0.0 になる."""
        mf = TriangleMF(0.0, 0.5, 1.0)
        assert mf.evaluate(1.0) == pytest.approx(0.0)

    def test_outside_left_returns_zero(self) -> None:
        """左端より小さい値でメンバーシップ度が 0.0 になる."""
        mf = TriangleMF(0.0, 0.5, 1.0)
        assert mf.evaluate(-1.0) == pytest.approx(0.0)

    def test_outside_right_returns_zero(self) -> None:
        """右端より大きい値でメンバーシップ度が 0.0 になる."""
        mf = TriangleMF(0.0, 0.5, 1.0)
        assert mf.evaluate(2.0) == pytest.approx(0.0)

    def test_midpoint_left_slope(self) -> None:
        """左スロープの中点で 0.5 になる."""
        mf = TriangleMF(0.0, 1.0, 2.0)
        assert mf.evaluate(0.5) == pytest.approx(0.5)

    def test_midpoint_right_slope(self) -> None:
        """右スロープの中点で 0.5 になる."""
        mf = TriangleMF(0.0, 1.0, 2.0)
        assert mf.evaluate(1.5) == pytest.approx(0.5)

    def test_invalid_params_raises(self) -> None:
        """パラメータ順序が不正な場合 ValueError を送出する."""
        with pytest.raises(ValueError):
            TriangleMF(1.0, 0.5, 2.0)

    def test_support_range(self) -> None:
        """サポート範囲が正しく返される."""
        mf = TriangleMF(1.0, 2.0, 3.0)
        assert mf.support_range() == (1.0, 3.0)


# ---------------------------------------------------------------------------
# TrapezoidMF
# ---------------------------------------------------------------------------


class TestTrapezoidMF:
    """台形型メンバーシップ関数のテスト."""

    def test_flat_top_returns_one(self) -> None:
        """フラットトップ領域でメンバーシップ度が 1.0 になる."""
        mf = TrapezoidMF(0.0, 0.25, 0.75, 1.0)
        for x in [0.25, 0.5, 0.75]:
            assert mf.evaluate(x) == pytest.approx(1.0), f"x={x}"

    def test_left_boundary_returns_zero(self) -> None:
        """左端でメンバーシップ度が 0.0 になる."""
        mf = TrapezoidMF(0.0, 0.25, 0.75, 1.0)
        assert mf.evaluate(0.0) == pytest.approx(0.0)

    def test_right_boundary_returns_zero(self) -> None:
        """右端でメンバーシップ度が 0.0 になる."""
        mf = TrapezoidMF(0.0, 0.25, 0.75, 1.0)
        assert mf.evaluate(1.0) == pytest.approx(0.0)

    def test_outside_left_returns_zero(self) -> None:
        """左端より外でメンバーシップ度が 0.0 になる."""
        mf = TrapezoidMF(0.0, 0.25, 0.75, 1.0)
        assert mf.evaluate(-0.5) == pytest.approx(0.0)

    def test_outside_right_returns_zero(self) -> None:
        """右端より外でメンバーシップ度が 0.0 になる."""
        mf = TrapezoidMF(0.0, 0.25, 0.75, 1.0)
        assert mf.evaluate(1.5) == pytest.approx(0.0)

    def test_left_slope_midpoint(self) -> None:
        """左スロープの中点で 0.5 になる."""
        mf = TrapezoidMF(0.0, 1.0, 2.0, 3.0)
        assert mf.evaluate(0.5) == pytest.approx(0.5)

    def test_right_slope_midpoint(self) -> None:
        """右スロープの中点で 0.5 になる."""
        mf = TrapezoidMF(0.0, 1.0, 2.0, 3.0)
        assert mf.evaluate(2.5) == pytest.approx(0.5)

    def test_degenerate_trapezoid_with_same_ab(self) -> None:
        """a=b（左側スロープが垂直）でも正しく動作する."""
        mf = TrapezoidMF(0.0, 0.0, 1.0, 2.0)
        assert mf.evaluate(-0.1) == pytest.approx(0.0)  # 範囲外（左）
        assert mf.evaluate(0.0) == pytest.approx(1.0)   # a=b=0 のフラットトップ開始
        assert mf.evaluate(0.5) == pytest.approx(1.0)   # フラットトップ内

    def test_degenerate_trapezoid_with_same_cd(self) -> None:
        """c=d（右側スロープが垂直）でも正しく動作する."""
        mf = TrapezoidMF(0.0, 1.0, 2.0, 2.0)
        assert mf.evaluate(1.5) == pytest.approx(1.0)
        assert mf.evaluate(2.0) == pytest.approx(0.0)

    def test_spike_a_eq_b_eq_c_eq_d(self) -> None:
        """a=b=c=d のとき、その点以外はすべて 0.0 になる."""
        mf = TrapezoidMF(1.0, 1.0, 1.0, 1.0)
        assert mf.evaluate(0.9) == pytest.approx(0.0)
        assert mf.evaluate(1.1) == pytest.approx(0.0)

    def test_invalid_params_raises(self) -> None:
        """パラメータ順序が不正な場合 ValueError を送出する."""
        with pytest.raises(ValueError):
            TrapezoidMF(0.0, 0.75, 0.25, 1.0)

    def test_support_range(self) -> None:
        """サポート範囲が正しく返される."""
        mf = TrapezoidMF(0.0, 0.25, 0.75, 1.0)
        assert mf.support_range() == (0.0, 1.0)

    def test_hp_ratio_low_boundary(self) -> None:
        """aggressive.json の hp_ratio LOW（台形）の境界値テスト."""
        # LOW: trapezoid [0.0, 0.0, 0.20, 0.35]
        mf = TrapezoidMF(0.0, 0.0, 0.20, 0.35)
        assert mf.evaluate(-0.1) == pytest.approx(0.0)  # 範囲外（左）
        assert mf.evaluate(0.0) == pytest.approx(1.0)   # a=b=0 のフラットトップ開始
        assert mf.evaluate(0.1) == pytest.approx(1.0)   # フラットトップ内
        assert mf.evaluate(0.20) == pytest.approx(1.0)  # フラットトップ右端
        assert mf.evaluate(0.35) == pytest.approx(0.0)  # 右端 d=0.35 → 0

    def test_hp_ratio_high_boundary(self) -> None:
        """aggressive.json の hp_ratio HIGH（台形）の境界値テスト."""
        # HIGH: trapezoid [0.65, 0.80, 1.0, 1.0]
        mf = TrapezoidMF(0.65, 0.80, 1.0, 1.0)
        assert mf.evaluate(0.65) == pytest.approx(0.0)  # 左端
        assert mf.evaluate(0.80) == pytest.approx(1.0)  # フラット開始
        assert mf.evaluate(1.0) == pytest.approx(0.0)  # 右端 = 1.0 → 0


# ---------------------------------------------------------------------------
# ファジフィケーション
# ---------------------------------------------------------------------------


class TestFuzzify:
    """_fuzzify 関数のテスト."""

    def _mfs(self) -> dict:
        return {
            "hp_ratio": {
                "LOW": TrapezoidMF(0.0, 0.0, 0.20, 0.35),
                "MEDIUM": TriangleMF(0.25, 0.50, 0.75),
                "HIGH": TrapezoidMF(0.65, 0.80, 1.0, 1.0),
            }
        }

    def test_returns_membership_degrees(self) -> None:
        """hp_ratio=0.1 のとき LOW=1.0, MEDIUM=0.0, HIGH=0.0 になる."""
        result = _fuzzify({"hp_ratio": 0.1}, self._mfs())
        assert result["hp_ratio"]["LOW"] == pytest.approx(1.0)
        assert result["hp_ratio"]["MEDIUM"] == pytest.approx(0.0)
        assert result["hp_ratio"]["HIGH"] == pytest.approx(0.0)

    def test_clamp_below_range(self) -> None:
        """入力が最小値より小さい場合はクランプされる（エラーにならない）."""
        result = _fuzzify({"hp_ratio": -10.0}, self._mfs())
        # クランプ後 0.0 になるので LOW=0.0（左端 a=0.0 のため）
        assert "hp_ratio" in result
        assert all(0.0 <= v <= 1.0 for v in result["hp_ratio"].values())

    def test_clamp_above_range(self) -> None:
        """入力が最大値より大きい場合はクランプされる（エラーにならない）."""
        result = _fuzzify({"hp_ratio": 100.0}, self._mfs())
        assert "hp_ratio" in result
        assert all(0.0 <= v <= 1.0 for v in result["hp_ratio"].values())

    def test_unknown_variable_skipped(self) -> None:
        """定義されていない変数は無視される."""
        result = _fuzzify({"unknown_var": 0.5}, self._mfs())
        assert "unknown_var" not in result

    def test_multiple_variables(self) -> None:
        """複数の入力変数を同時に処理できる."""
        mfs = {
            "hp_ratio": {
                "LOW": TrapezoidMF(0.0, 0.0, 0.20, 0.35),
                "HIGH": TrapezoidMF(0.65, 0.80, 1.0, 1.0),
            },
            "enemy_count_near": {
                "FEW": TrapezoidMF(0, 0, 1, 2),
                "MANY": TrapezoidMF(4, 6, 99, 99),
            },
        }
        result = _fuzzify({"hp_ratio": 0.9, "enemy_count_near": 0}, mfs)
        assert result["hp_ratio"]["HIGH"] == pytest.approx(1.0)
        assert result["enemy_count_near"]["FEW"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# ルール評価
# ---------------------------------------------------------------------------


class TestEvaluateRules:
    """_evaluate_rules 関数のテスト."""

    def _make_rule_and(self) -> FuzzyRule:
        return FuzzyRule(
            id="r1",
            conditions=[
                FuzzyCondition(variable="hp_ratio", set="HIGH"),
                FuzzyCondition(variable="enemy_count_near", set="FEW"),
            ],
            operator="AND",
            output=FuzzyOutput(variable="action", set="ATTACK"),
        )

    def _make_rule_or(self) -> FuzzyRule:
        return FuzzyRule(
            id="r2",
            conditions=[
                FuzzyCondition(variable="hp_ratio", set="LOW"),
                FuzzyCondition(variable="enemy_count_near", set="MANY"),
            ],
            operator="OR",
            output=FuzzyOutput(variable="action", set="RETREAT"),
        )

    def test_and_rule_fires_with_min(self) -> None:
        """AND ルールは条件のメンバーシップ度の min で発火する."""
        fuzzified = {
            "hp_ratio": {"HIGH": 0.8},
            "enemy_count_near": {"FEW": 0.6},
        }
        result = _evaluate_rules(fuzzified, [self._make_rule_and()])
        assert result["action"]["ATTACK"] == pytest.approx(0.6)

    def test_or_rule_fires_with_max(self) -> None:
        """OR ルールは条件のメンバーシップ度の max で発火する."""
        fuzzified = {
            "hp_ratio": {"LOW": 0.3},
            "enemy_count_near": {"MANY": 0.7},
        }
        result = _evaluate_rules(fuzzified, [self._make_rule_or()])
        assert result["action"]["RETREAT"] == pytest.approx(0.7)

    def test_no_firing_when_zero_membership(self) -> None:
        """メンバーシップ度が 0 のとき、発火強度 0 でも結果に含まれる."""
        fuzzified = {
            "hp_ratio": {"HIGH": 0.0},
            "enemy_count_near": {"FEW": 0.0},
        }
        result = _evaluate_rules(fuzzified, [self._make_rule_and()])
        # 発火強度 0 は結果に含まれる（最大で採用されるが 0 のまま）
        assert result.get("action", {}).get("ATTACK", 0.0) == pytest.approx(0.0)

    def test_missing_variable_skips_rule(self) -> None:
        """条件変数が fuzzified にない場合、そのルールはスキップされる."""
        fuzzified = {"hp_ratio": {"HIGH": 0.8}}
        result = _evaluate_rules(fuzzified, [self._make_rule_and()])
        assert "action" not in result

    def test_multiple_rules_same_output_uses_max(self) -> None:
        """同一出力集合に複数ルールが発火する場合、最大値を採用する."""
        rule1 = FuzzyRule(
            id="r1",
            conditions=[FuzzyCondition(variable="hp_ratio", set="HIGH")],
            operator="AND",
            output=FuzzyOutput(variable="action", set="ATTACK"),
        )
        rule2 = FuzzyRule(
            id="r2",
            conditions=[FuzzyCondition(variable="enemy_count_near", set="FEW")],
            operator="AND",
            output=FuzzyOutput(variable="action", set="ATTACK"),
        )
        fuzzified = {
            "hp_ratio": {"HIGH": 0.4},
            "enemy_count_near": {"FEW": 0.9},
        }
        result = _evaluate_rules(fuzzified, [rule1, rule2])
        assert result["action"]["ATTACK"] == pytest.approx(0.9)

    def test_empty_rules_returns_empty(self) -> None:
        """ルールが空の場合は空の辞書を返す."""
        result = _evaluate_rules({"hp_ratio": {"HIGH": 1.0}}, [])
        assert result == {}

    def test_weight_applied(self) -> None:
        """ルールの weight が発火強度に掛け合わされる."""
        rule = FuzzyRule(
            id="r1",
            conditions=[FuzzyCondition(variable="hp_ratio", set="HIGH")],
            operator="AND",
            output=FuzzyOutput(variable="action", set="ATTACK"),
            weight=0.5,
        )
        fuzzified = {"hp_ratio": {"HIGH": 1.0}}
        result = _evaluate_rules(fuzzified, [rule])
        assert result["action"]["ATTACK"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# FuzzyEngine (統合テスト)
# ---------------------------------------------------------------------------


class TestFuzzyEngineIntegration:
    """FuzzyEngine の統合テスト."""

    @pytest.fixture()
    def aggressive_engine(self) -> FuzzyEngine:
        """aggressive.json から FuzzyEngine を生成するフィクスチャ."""
        json_path = _FUZZY_RULES_DIR / "aggressive.json"
        return FuzzyEngine.from_json(json_path)

    def test_load_from_json(self, aggressive_engine: FuzzyEngine) -> None:
        """aggressive.json が正常にロードされる."""
        assert aggressive_engine.rule_set.strategy == "AGGRESSIVE"
        assert len(aggressive_engine.rule_set.rules) > 0

    def test_infer_returns_dict(self, aggressive_engine: FuzzyEngine) -> None:
        """infer() が辞書を返す."""
        result = aggressive_engine.infer({"hp_ratio": 0.8, "enemy_count_near": 1.0})
        assert isinstance(result, dict)

    def test_high_hp_few_enemies_attack_dominant(
        self, aggressive_engine: FuzzyEngine
    ) -> None:
        """HP が HIGH かつ 近くの敵が FEW → ATTACK の活性化度が高い."""
        _, debug = aggressive_engine.infer_with_debug(
            {"hp_ratio": 0.9, "enemy_count_near": 0.5}
        )
        activations = debug["activations"].get("action", {})
        assert activations.get("ATTACK", 0.0) > activations.get("RETREAT", 0.0)

    def test_low_hp_many_enemies_retreat_dominant(
        self, aggressive_engine: FuzzyEngine
    ) -> None:
        """HP が LOW かつ 近くの敵が MANY → RETREAT の活性化度が高い."""
        _, debug = aggressive_engine.infer_with_debug(
            {"hp_ratio": 0.1, "enemy_count_near": 8.0}
        )
        activations = debug["activations"].get("action", {})
        assert activations.get("RETREAT", 0.0) > activations.get("ATTACK", 0.0)

    def test_far_enemy_move_fires(self, aggressive_engine: FuzzyEngine) -> None:
        """最近敵との距離が FAR → MOVE が発火する."""
        _, debug = aggressive_engine.infer_with_debug(
            {"hp_ratio": 0.5, "enemy_count_near": 3.0, "distance_to_nearest_enemy": 800.0}
        )
        activations = debug["activations"].get("action", {})
        assert activations.get("MOVE", 0.0) > 0.0

    def test_no_firing_returns_default(self) -> None:
        """全ルール不発火時はデフォルト出力を返す."""
        # 空のルールセットを使用
        rule_set = FuzzyRuleSet(
            strategy="TEST",
            layer="test",
            rules=[],
            membership_functions={},
        )
        engine = FuzzyEngine(rule_set=rule_set, default_output={"action": 0.5})
        result = engine.infer({"hp_ratio": 0.5})
        assert result == {"action": 0.5}

    def test_no_firing_returns_empty_when_no_default(self) -> None:
        """全ルール不発火・デフォルト未設定時は空辞書を返す."""
        rule_set = FuzzyRuleSet(
            strategy="TEST",
            layer="test",
            rules=[],
            membership_functions={},
        )
        engine = FuzzyEngine(rule_set=rule_set)
        result = engine.infer({"hp_ratio": 0.5})
        assert result == {}

    def test_infer_with_debug_returns_tuple(
        self, aggressive_engine: FuzzyEngine
    ) -> None:
        """infer_with_debug() がタプル (結果, デバッグ情報) を返す."""
        result, debug = aggressive_engine.infer_with_debug(
            {"hp_ratio": 0.8, "enemy_count_near": 1.0}
        )
        assert isinstance(result, dict)
        assert "fuzzified" in debug
        assert "activations" in debug

    def test_input_clamped_above_max(self, aggressive_engine: FuzzyEngine) -> None:
        """入力値が範囲外（上限超え）でもエラーにならない."""
        result = aggressive_engine.infer({"hp_ratio": 999.0, "enemy_count_near": 0.0})
        assert isinstance(result, dict)

    def test_input_clamped_below_min(self, aggressive_engine: FuzzyEngine) -> None:
        """入力値が範囲外（下限未満）でもエラーにならない."""
        result = aggressive_engine.infer({"hp_ratio": -999.0, "enemy_count_near": 10.0})
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# FuzzyRuleSet ロード
# ---------------------------------------------------------------------------


class TestFuzzyRuleSetLoad:
    """FuzzyRuleSet のロードテスト."""

    def test_from_dict_basic(self) -> None:
        """from_dict() が正しくルールセットを生成する."""
        data = {
            "strategy": "TEST",
            "layer": "test_layer",
            "rules": [
                {
                    "id": "r1",
                    "conditions": [{"variable": "x", "set": "HIGH"}],
                    "operator": "AND",
                    "output": {"variable": "y", "set": "BIG"},
                }
            ],
            "membership_functions": {
                "x": {"HIGH": {"type": "trapezoid", "params": [0.5, 0.7, 1.0, 1.0]}},
                "y": {"BIG": {"type": "triangle", "params": [0.0, 0.5, 1.0]}},
            },
        }
        rs = FuzzyRuleSet.from_dict(data)
        assert rs.strategy == "TEST"
        assert rs.layer == "test_layer"
        assert len(rs.rules) == 1
        assert rs.rules[0].id == "r1"
        assert "x" in rs.membership_functions
        assert "y" in rs.membership_functions

    def test_from_json_aggressive(self) -> None:
        """aggressive.json からロードできる."""
        json_path = _FUZZY_RULES_DIR / "aggressive.json"
        rs = FuzzyRuleSet.from_json(json_path)
        assert rs.strategy == "AGGRESSIVE"
        assert rs.layer == "behavior_selection"
        assert len(rs.rules) >= 4  # 最低4ルール
        assert "hp_ratio" in rs.membership_functions
        assert "enemy_count_near" in rs.membership_functions
        assert "distance_to_nearest_enemy" in rs.membership_functions

    def test_aggressive_json_has_required_rules(self) -> None:
        """aggressive.json が要件通りのルールを含む."""
        json_path = _FUZZY_RULES_DIR / "aggressive.json"
        rs = FuzzyRuleSet.from_json(json_path)
        rule_ids = {r.id for r in rs.rules}
        # 最低限のルールが存在することを確認
        assert "rule_001" in rule_ids  # HP HIGH + 敵 FEW → ATTACK
        assert "rule_002" in rule_ids  # HP LOW + 敵 MANY → RETREAT
        assert "rule_003" in rule_ids  # 距離 FAR → MOVE

    def test_invalid_mf_type_raises(self) -> None:
        """未知のメンバーシップ関数タイプで ValueError が発生する."""
        data = {
            "strategy": "TEST",
            "rules": [],
            "membership_functions": {
                "x": {"HIGH": {"type": "gaussian", "params": [0.5, 0.1]}}
            },
        }
        with pytest.raises(ValueError, match="未知のメンバーシップ関数タイプ"):
            FuzzyRuleSet.from_dict(data)

    def test_triangle_wrong_param_count_raises(self) -> None:
        """triangle に3つ以外のパラメータを渡すと ValueError が発生する."""
        data = {
            "strategy": "TEST",
            "rules": [],
            "membership_functions": {
                "x": {"HIGH": {"type": "triangle", "params": [0.0, 1.0]}}
            },
        }
        with pytest.raises(ValueError):
            FuzzyRuleSet.from_dict(data)

    def test_trapezoid_wrong_param_count_raises(self) -> None:
        """trapezoid に4つ以外のパラメータを渡すと ValueError が発生する."""
        data = {
            "strategy": "TEST",
            "rules": [],
            "membership_functions": {
                "x": {"HIGH": {"type": "trapezoid", "params": [0.0, 0.5, 1.0]}}
            },
        }
        with pytest.raises(ValueError):
            FuzzyRuleSet.from_dict(data)

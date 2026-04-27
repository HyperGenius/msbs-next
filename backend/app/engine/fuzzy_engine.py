"""ファジィ推論エンジン.

メンバーシップ関数の評価・ルール推論・デファジフィケーションを担うコアライブラリ。
ルールセットは JSON ファイルとして外部化し、StrategyMode に応じてロードする設計。

Usage:
    from app.engine.fuzzy_engine import FuzzyEngine

    engine = FuzzyEngine.from_json("backend/data/fuzzy_rules/aggressive.json")
    result = engine.infer({"hp_ratio": 0.8, "enemy_count_near": 1})
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# メンバーシップ関数（抽象基底 + 具体実装）
# ---------------------------------------------------------------------------


class MembershipFunction(ABC):
    """メンバーシップ関数の抽象基底クラス."""

    @abstractmethod
    def evaluate(self, x: float) -> float:
        """入力値 x に対するメンバーシップ度（0.0〜1.0）を返す.

        Args:
            x: 入力値

        Returns:
            float: メンバーシップ度（0.0〜1.0）
        """

    @abstractmethod
    def support_range(self) -> tuple[float, float]:
        """メンバーシップ関数が非ゼロになる範囲 [min, max] を返す."""


class TriangleMF(MembershipFunction):
    """三角形型メンバーシップ関数.

    Args:
        a: 左端（メンバーシップ度 0 の始点）
        b: 頂点（メンバーシップ度 1 の点）
        c: 右端（メンバーシップ度 0 の終点）
    """

    def __init__(self, a: float, b: float, c: float) -> None:
        if not (a <= b <= c):
            raise ValueError(f"TriangleMF: パラメータ順序違反 a={a}, b={b}, c={c}")
        self.a = a
        self.b = b
        self.c = c

    def evaluate(self, x: float) -> float:
        """三角形メンバーシップ関数の評価."""
        a, b, c = self.a, self.b, self.c
        # 左端は open（x < a で 0）、右端は open（x > c で 0）
        if x < a or x > c:
            return 0.0
        if x <= b:
            return (x - a) / (b - a) if b != a else 1.0
        return (c - x) / (c - b) if c != b else 1.0

    def support_range(self) -> tuple[float, float]:
        return (self.a, self.c)


class TrapezoidMF(MembershipFunction):
    """台形型メンバーシップ関数.

    Args:
        a: 左端（メンバーシップ度 0 の始点）
        b: 左肩（メンバーシップ度 1 の始点）
        c: 右肩（メンバーシップ度 1 の終点）
        d: 右端（メンバーシップ度 0 の終点）
    """

    def __init__(self, a: float, b: float, c: float, d: float) -> None:
        if not (a <= b <= c <= d):
            raise ValueError(
                f"TrapezoidMF: パラメータ順序違反 a={a}, b={b}, c={c}, d={d}"
            )
        self.a = a
        self.b = b
        self.c = c
        self.d = d

    def evaluate(self, x: float) -> float:
        """台形メンバーシップ関数の評価."""
        a, b, c, d = self.a, self.b, self.c, self.d
        # 左端は open（x < a で 0）、右端は open（x > d で 0）
        if x < a or x > d:
            return 0.0
        if b <= x <= c:
            return 1.0
        if x < b:
            return (x - a) / (b - a) if b != a else 1.0
        # c < x <= d
        return (d - x) / (d - c) if d != c else 1.0

    def support_range(self) -> tuple[float, float]:
        return (self.a, self.d)


def _build_mf(mf_type: str, params: list[float]) -> MembershipFunction:
    """JSON の type / params からメンバーシップ関数オブジェクトを生成する."""
    if mf_type == "triangle":
        if len(params) != 3:
            raise ValueError(f"triangle には3つのパラメータが必要です: {params}")
        return TriangleMF(*params)
    if mf_type == "trapezoid":
        if len(params) != 4:
            raise ValueError(f"trapezoid には4つのパラメータが必要です: {params}")
        return TrapezoidMF(*params)
    raise ValueError(f"未知のメンバーシップ関数タイプ: {mf_type}")


# ---------------------------------------------------------------------------
# ルール・ルールセット
# ---------------------------------------------------------------------------


@dataclass
class FuzzyCondition:
    """単一条件: ある入力変数がある集合に属するか."""

    variable: str
    set: str


@dataclass
class FuzzyOutput:
    """ルール出力: ある出力変数にある集合を割り当てる."""

    variable: str
    set: str


@dataclass
class FuzzyRule:
    """単一のファジィルール."""

    id: str
    conditions: list[FuzzyCondition]
    operator: str  # "AND" or "OR"
    output: FuzzyOutput
    weight: float = field(default=1.0)


@dataclass
class FuzzyRuleSet:
    """JSON からロードしたルールセット一式."""

    strategy: str
    layer: str
    rules: list[FuzzyRule]
    # {variable_name: {set_name: MembershipFunction}}
    membership_functions: dict[str, dict[str, MembershipFunction]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FuzzyRuleSet:
        """辞書（JSON デシリアライズ済み）からルールセットを生成する."""
        strategy = data["strategy"]
        layer = data.get("layer", "")

        # メンバーシップ関数のロード
        mfs: dict[str, dict[str, MembershipFunction]] = {}
        for var_name, sets in data.get("membership_functions", {}).items():
            mfs[var_name] = {}
            for set_name, mf_def in sets.items():
                mfs[var_name][set_name] = _build_mf(mf_def["type"], mf_def["params"])

        # ルールのロード
        rules: list[FuzzyRule] = []
        for rule_data in data.get("rules", []):
            conditions = [
                FuzzyCondition(variable=c["variable"], set=c["set"])
                for c in rule_data["conditions"]
            ]
            output = FuzzyOutput(
                variable=rule_data["output"]["variable"],
                set=rule_data["output"]["set"],
            )
            rules.append(
                FuzzyRule(
                    id=rule_data["id"],
                    conditions=conditions,
                    operator=rule_data.get("operator", "AND").upper(),
                    output=output,
                    weight=float(rule_data.get("weight", 1.0)),
                )
            )

        return cls(
            strategy=strategy,
            layer=layer,
            rules=rules,
            membership_functions=mfs,
        )

    @classmethod
    def from_json(cls, path: str | Path) -> FuzzyRuleSet:
        """JSON ファイルからルールセットをロードする."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# ファジフィケーション
# ---------------------------------------------------------------------------


def _fuzzify(
    inputs: dict[str, float],
    membership_functions: dict[str, dict[str, MembershipFunction]],
) -> dict[str, dict[str, float]]:
    """入力値を各ファジィ集合へのメンバーシップ度に変換する（ファジフィケーション）.

    入力変数の値が定義済みメンバーシップ関数のサポート範囲外の場合は
    その変数に定義された全集合の support_range の外端へクランプして処理する。

    Args:
        inputs: {変数名: 数値}
        membership_functions: {変数名: {集合名: MembershipFunction}}

    Returns:
        {変数名: {集合名: メンバーシップ度}}
    """
    fuzzified: dict[str, dict[str, float]] = {}
    for var, mf_sets in membership_functions.items():
        if var not in inputs:
            continue
        x = inputs[var]

        # 全集合の support_range から変数の有効範囲を決定してクランプ
        all_mins = [mf.support_range()[0] for mf in mf_sets.values()]
        all_maxs = [mf.support_range()[1] for mf in mf_sets.values()]
        x_clamped = max(min(all_mins), min(max(all_maxs), x))

        fuzzified[var] = {
            set_name: mf.evaluate(x_clamped)
            for set_name, mf in mf_sets.items()
        }
    return fuzzified


# ---------------------------------------------------------------------------
# ルール評価（推論）
# ---------------------------------------------------------------------------


def _evaluate_rules(
    fuzzified: dict[str, dict[str, float]],
    rules: list[FuzzyRule],
) -> dict[str, dict[str, float]]:
    """各ルールを評価し、出力変数の集合ごとの活性化度を求める.

    Args:
        fuzzified: ファジフィケーション結果
        rules: ルール一覧

    Returns:
        {出力変数名: {集合名: 活性化度}}
    """
    activations: dict[str, dict[str, float]] = {}

    for rule in rules:
        # 条件の評価: AND → min, OR → max
        membership_values: list[float] = []
        skip = False
        for cond in rule.conditions:
            if cond.variable not in fuzzified:
                skip = True
                break
            mu = fuzzified[cond.variable].get(cond.set, 0.0)
            membership_values.append(mu)

        if skip or not membership_values:
            continue

        if rule.operator == "AND":
            firing_strength = min(membership_values)
        else:  # OR
            firing_strength = max(membership_values)

        firing_strength *= rule.weight

        out_var = rule.output.variable
        out_set = rule.output.set

        if out_var not in activations:
            activations[out_var] = {}

        # 同一出力集合に複数ルールが発火する場合は最大値を採用（最大推論法）
        activations[out_var][out_set] = max(
            activations[out_var].get(out_set, 0.0), firing_strength
        )

    return activations


# ---------------------------------------------------------------------------
# デファジフィケーション（重心法）
# ---------------------------------------------------------------------------

_DEFUZZ_RESOLUTION = 200  # 数値積分の分解能


def _defuzzify_centroid(
    activations: dict[str, dict[str, float]],
    output_membership_functions: dict[str, dict[str, MembershipFunction]],
) -> dict[str, float]:
    """重心法（Centroid）でデファジフィケーションを実行する.

    各出力変数について、発火したルールの出力集合をクリッピングして
    合成した集合の重心を求める。

    Args:
        activations: {出力変数名: {集合名: 活性化度}}
        output_membership_functions: {変数名: {集合名: MembershipFunction}}

    Returns:
        {出力変数名: デファジフィケーション値}
    """
    result: dict[str, float] = {}

    for out_var, set_activations in activations.items():
        if out_var not in output_membership_functions:
            continue

        mf_sets = output_membership_functions[out_var]

        # 出力変数のサポート範囲を決定
        all_mins: list[float] = []
        all_maxs: list[float] = []
        for set_name, mf in mf_sets.items():
            if set_name in set_activations and set_activations[set_name] > 0.0:
                lo, hi = mf.support_range()
                all_mins.append(lo)
                all_maxs.append(hi)

        if not all_mins:
            continue

        x_min = min(all_mins)
        x_max = max(all_maxs)
        if x_min >= x_max:
            result[out_var] = x_min
            continue

        # 数値積分による重心計算
        step = (x_max - x_min) / _DEFUZZ_RESOLUTION
        weighted_sum = 0.0
        area_sum = 0.0

        for i in range(_DEFUZZ_RESOLUTION):
            x = x_min + (i + 0.5) * step
            # クリッピング合成: 各集合の MF を発火強度でクリップし最大値を採用
            mu_combined = 0.0
            for set_name, activation in set_activations.items():
                if activation <= 0.0 or set_name not in mf_sets:
                    continue
                mu = mf_sets[set_name].evaluate(x)
                mu_clipped = min(mu, activation)
                mu_combined = max(mu_combined, mu_clipped)

            weighted_sum += x * mu_combined
            area_sum += mu_combined

        if area_sum > 0.0:
            result[out_var] = weighted_sum / area_sum

    return result


# ---------------------------------------------------------------------------
# FuzzyEngine（メインクラス）
# ---------------------------------------------------------------------------


class FuzzyEngine:
    """ファジィ推論エンジン.

    ルールセット（FuzzyRuleSet）をもとに、入力辞書から出力辞書を推論する。

    Args:
        rule_set: ロード済みのルールセット
        default_output: 全ルール不発火時のデフォルト出力（省略時は空辞書）
    """

    def __init__(
        self,
        rule_set: FuzzyRuleSet,
        default_output: dict[str, float] | None = None,
    ) -> None:
        self.rule_set = rule_set
        self._default_output: dict[str, float] = default_output or {}

    @classmethod
    def from_json(
        cls,
        path: str | Path,
        default_output: dict[str, float] | None = None,
    ) -> FuzzyEngine:
        """JSON ファイルから FuzzyEngine を生成する.

        Args:
            path: JSON ファイルのパス
            default_output: 全ルール不発火時のデフォルト出力

        Returns:
            FuzzyEngine インスタンス
        """
        rule_set = FuzzyRuleSet.from_json(path)
        return cls(rule_set=rule_set, default_output=default_output)

    def infer(self, inputs: dict[str, float]) -> dict[str, float]:
        """ファジィ推論を実行し、デファジフィケーション結果を返す.

        処理の流れ:
        1. ファジフィケーション（入力値 → メンバーシップ度）
        2. ルール評価（メンバーシップ度 → 出力集合の活性化度）
        3. デファジフィケーション（活性化度 → スカラー出力値）
        4. 全ルール不発火時はデフォルト出力値を返す

        Args:
            inputs: {入力変数名: 数値}

        Returns:
            {出力変数名: 数値}
        """
        # 1. ファジフィケーション
        fuzzified = _fuzzify(inputs, self.rule_set.membership_functions)

        # 2. ルール評価
        activations = _evaluate_rules(fuzzified, self.rule_set.rules)

        if not activations:
            return dict(self._default_output)

        # 3. デファジフィケーション（重心法）
        result = _defuzzify_centroid(activations, self.rule_set.membership_functions)

        # 4. デファジ結果が空（出力変数のMFが未定義など）の場合はデフォルト出力
        if not result:
            return dict(self._default_output)

        return result

    def infer_with_debug(
        self, inputs: dict[str, float]
    ) -> tuple[dict[str, float], dict[str, Any]]:
        """ファジィ推論を実行し、デバッグ情報も合わせて返す.

        Args:
            inputs: {入力変数名: 数値}

        Returns:
            (デファジフィケーション結果, デバッグ情報辞書)
        """
        fuzzified = _fuzzify(inputs, self.rule_set.membership_functions)
        activations = _evaluate_rules(fuzzified, self.rule_set.rules)

        debug: dict[str, Any] = {
            "fuzzified": fuzzified,
            "activations": activations,
        }

        if not activations:
            return dict(self._default_output), debug

        result = _defuzzify_centroid(activations, self.rule_set.membership_functions)

        if not result:
            return dict(self._default_output), debug

        return result, debug

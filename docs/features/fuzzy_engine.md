# FuzzyEngine 仕様書

**バージョン:** 1.0.0  
**作成日:** 2026-04-27  
**対応 Issue:** Phase 1-2 | FuzzyEngine コア実装

---

## 1. 概要

`FuzzyEngine` は、バトルエンジンの AI 意思決定に使用するファジィ推論の汎用エンジンである。  
メンバーシップ関数の評価・ルール推論・デファジフィケーションを担うコアライブラリで、  
Phase 1-3 以降のすべてのファジィ推論はこのエンジンを通じて動作する。

ルールセットは **JSON ファイル** として外部化されており、コードを変更せずにゲームバランスを調整できる。

---

## 2. ファイル構成

```
backend/
├── app/engine/
│   └── fuzzy_engine.py          # FuzzyEngine コアライブラリ
└── data/fuzzy_rules/
    ├── schema.json              # JSON スキーマ定義
    ├── aggressive.json          # AGGRESSIVE モード用ルールセット（behavior_selection レイヤー）
    ├── aggressive_target_selection.json  # AGGRESSIVE モード用ターゲット選択ルールセット
    ├── aggressive_weapon_selection.json  # AGGRESSIVE モード用武器選択ルールセット
    ├── defensive.json           # DEFENSIVE モード用ルールセット（behavior_selection レイヤー）
    ├── defensive_target_selection.json   # DEFENSIVE モード用ターゲット選択ルールセット
    ├── defensive_weapon_selection.json   # DEFENSIVE モード用武器選択ルールセット
    ├── sniper.json              # SNIPER モード用ルールセット（behavior_selection レイヤー）
    ├── sniper_target_selection.json      # SNIPER モード用ターゲット選択ルールセット
    ├── sniper_weapon_selection.json      # SNIPER モード用武器選択ルールセット
    ├── assault.json             # ASSAULT モード用ルールセット（behavior_selection レイヤー）
    ├── assault_target_selection.json     # ASSAULT モード用ターゲット選択ルールセット
    ├── assault_weapon_selection.json     # ASSAULT モード用武器選択ルールセット
    ├── retreat.json             # RETREAT モード用ルールセット（behavior_selection レイヤー）
    ├── retreat_target_selection.json     # RETREAT モード用ターゲット選択ルールセット
    └── retreat_weapon_selection.json     # RETREAT モード用武器選択ルールセット
```

---

## 3. クラス設計

### 3.1 メンバーシップ関数

#### `MembershipFunction`（抽象基底クラス）

| メソッド | シグネチャ | 説明 |
|---------|-----------|------|
| `evaluate` | `(x: float) -> float` | 入力値 x に対するメンバーシップ度（0.0〜1.0）を返す |
| `support_range` | `() -> tuple[float, float]` | 非ゼロとなる範囲 [min, max] を返す |

#### `TriangleMF`（三角形型）

パラメータ `(a, b, c)` により定義される三角形型メンバーシップ関数。

| パラメータ | 説明 |
|-----------|------|
| `a` | 左端（メンバーシップ度 0 の始点） |
| `b` | 頂点（メンバーシップ度 1 の点） |
| `c` | 右端（メンバーシップ度 0 の終点） |

**制約:** `a <= b <= c`

```
1.0     ▲
        |    /\
        |   /  \
0.0  ───+--+----+──▶ x
           a  b  c
```

#### `TrapezoidMF`（台形型）

パラメータ `(a, b, c, d)` により定義される台形型メンバーシップ関数。

| パラメータ | 説明 |
|-----------|------|
| `a` | 左端（メンバーシップ度 0 の始点） |
| `b` | 左肩（メンバーシップ度 1 の始点） |
| `c` | 右肩（メンバーシップ度 1 の終点） |
| `d` | 右端（メンバーシップ度 0 の終点） |

**制約:** `a <= b <= c <= d`

```
1.0     ▲
        |   /‾‾‾‾\
        |  /      \
0.0  ───+-+--------+──▶ x
         a  b    c  d
```

**Note:** `a == b` の場合は左端が垂直（単調増加なし）、`c == d` の場合は右端が垂直になる。これにより、端を完全に「壁」として定義できる（例: `[0, 0, 0.2, 0.35]`）。左右ともに境界点を包含する（例: a=b=0 のとき x=0 は 1.0、c=d=1 のとき x=1 は 1.0）。

---

### 3.2 データクラス

#### `FuzzyCondition`

```python
@dataclass
class FuzzyCondition:
    variable: str  # 入力変数名
    set: str       # ファジィ集合名
```

#### `FuzzyOutput`

```python
@dataclass
class FuzzyOutput:
    variable: str  # 出力変数名
    set: str       # ファジィ集合名
```

#### `FuzzyRule`

```python
@dataclass
class FuzzyRule:
    id: str
    conditions: list[FuzzyCondition]
    operator: str   # "AND" | "OR"
    output: FuzzyOutput
    weight: float   # デフォルト: 1.0
```

#### `FuzzyRuleSet`

```python
@dataclass
class FuzzyRuleSet:
    strategy: str
    layer: str
    rules: list[FuzzyRule]
    membership_functions: dict[str, dict[str, MembershipFunction]]
```

---

### 3.3 `FuzzyEngine`

#### コンストラクタ

```python
FuzzyEngine(
    rule_set: FuzzyRuleSet,
    default_output: dict[str, float] | None = None,
)
```

#### クラスメソッド

```python
FuzzyEngine.from_json(
    path: str | Path,
    default_output: dict[str, float] | None = None,
) -> FuzzyEngine
```

#### インスタンスメソッド

| メソッド | シグネチャ | 説明 |
|---------|-----------|------|
| `infer` | `(inputs: dict[str, float]) -> dict[str, float]` | ファジィ推論を実行し、デファジフィケーション結果を返す |
| `infer_with_debug` | `(inputs: dict[str, float]) -> tuple[dict, dict]` | 推論結果とデバッグ情報（ファジフィケーション度・活性化度）を返す |

---

## 4. 推論フロー

```
入力辞書 {変数名: 数値}
       ↓
[1] ファジフィケーション（Fuzzification）
       ↓ {変数名: {集合名: メンバーシップ度}}
[2] ルール評価（Rule Evaluation）
       ↓ {出力変数名: {集合名: 活性化度}}
[3] デファジフィケーション（Defuzzification, 重心法）
       ↓ {出力変数名: スカラー値}
出力辞書
```

### 4.1 ファジフィケーション

入力値を各ファジィ集合へのメンバーシップ度に変換する。

- 入力変数の値が全集合のサポート範囲外の場合はクランプして処理する
- 定義されていない変数は無視する

### 4.2 ルール評価

条件演算子に応じて発火強度を計算する。

| 演算子 | 処理 |
|--------|------|
| `AND` | 条件のメンバーシップ度の `min()` |
| `OR`  | 条件のメンバーシップ度の `max()` |

- ルールに `weight` が設定されている場合、発火強度に乗算する
- 同一出力集合に複数ルールが発火する場合、最大値（最大推論法）を採用する
- 条件変数が入力に含まれない場合、そのルールはスキップされる

### 4.3 デファジフィケーション（重心法）

各出力変数について、発火したルールの出力集合をクリッピングして合成し、  
重心（重み付き平均）を求める。

```
出力値 = ∫ x・μ(x) dx / ∫ μ(x) dx
```

分解能: 200 点の数値積分

### 4.4 フォールバック

| 条件 | 動作 |
|------|------|
| 全ルールが不発火 | `default_output` を返す。未設定の場合は空辞書 `{}` |
| 出力変数のMFが未定義 | `default_output` を返す。未設定の場合は空辞書 `{}` |

---

## 5. JSON スキーマ

`backend/data/fuzzy_rules/schema.json` にて定義。

```json
{
  "strategy": "AGGRESSIVE",
  "layer": "behavior_selection",
  "rules": [
    {
      "id": "rule_001",
      "conditions": [
        { "variable": "hp_ratio", "set": "HIGH" },
        { "variable": "enemy_count_near", "set": "FEW" }
      ],
      "operator": "AND",
      "output": { "variable": "action", "set": "ATTACK" },
      "weight": 1.0
    }
  ],
  "membership_functions": {
    "hp_ratio": {
      "LOW":    { "type": "trapezoid", "params": [0.0, 0.0, 0.20, 0.35] },
      "MEDIUM": { "type": "triangle",  "params": [0.25, 0.50, 0.75] },
      "HIGH":   { "type": "trapezoid", "params": [0.65, 0.80, 1.0, 1.0] }
    }
  }
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `strategy` | `string` | ✓ | 戦略モード名 |
| `layer` | `string` | - | AI 意思決定階層名 |
| `rules` | `array` | ✓ | ファジィルールの一覧 |
| `membership_functions` | `object` | ✓ | 変数ごとのMF定義 |
| `rules[].weight` | `number` | - | ルールの重み（デフォルト: 1.0） |

---

## 6. AGGRESSIVE ルールセット（`aggressive.json`）

### 6.1 入力変数

| 変数 | 範囲 | ファジィ集合 |
|------|------|------------|
| `hp_ratio` | 0.0〜1.0 | LOW / MEDIUM / HIGH |
| `enemy_count_near` | 0〜N | FEW / SEVERAL / MANY |
| `ally_count_near` | 0〜N | FEW / SEVERAL / MANY |
| `distance_to_nearest_enemy` | 0〜MAX | CLOSE / MID / FAR |

### 6.2 出力変数

| 変数 | 取りうる値 |
|------|-----------|
| `action` | ATTACK / MOVE / RETREAT |

### 6.3 主要ルール

| ID | 条件 | 演算 | 出力 |
|----|------|------|------|
| rule_001 | hp_ratio=HIGH AND enemy_count_near=FEW | AND | action=ATTACK |
| rule_002 | hp_ratio=LOW AND enemy_count_near=MANY | AND | action=RETREAT |
| rule_003 | distance_to_nearest_enemy=FAR | AND | action=MOVE |
| rule_004〜010 | その他状況（AGGRESSIVEなのでデフォルトも攻撃寄り） | AND | action=ATTACK |

### 6.4 RETREAT フォールバック

`RETREAT` の出力は、呼び出し側で撤退ポイントの有無チェックを行うこと。  
撤退ポイント未設定の場合は `MOVE` にフォールバックする。

---

## 7. AGGRESSIVE ターゲット選択ルールセット（`aggressive_target_selection.json`）

**layer:** `target_selection`

### 7.1 入力変数

| 変数 | 範囲 | ファジィ集合 | 説明 |
|------|------|------------|------|
| `target_hp_ratio` | 0.0〜1.0 | LOW / MEDIUM / HIGH | 対象の残HP割合 |
| `target_distance` | 0〜3000 | CLOSE / MID / FAR | アクターから対象への距離 (m) |
| `target_attack_power` | 0〜∞ | LOW / MEDIUM / HIGH | 対象の武器最大威力 |
| `is_attacking_ally` | 0.0 or 1.0 | FALSE / TRUE | 対象が現在攻撃行動中か |

### 7.2 出力変数

| 変数 | 範囲 | 説明 |
|------|------|------|
| `target_priority` | 0.0〜1.0 | ターゲット優先度スコア。最高スコアの候補を選択する |

### 7.3 主要ルール

| ID | 条件 | 出力 |
|----|------|------|
| ts_rule_001 | target_hp_ratio=LOW AND target_distance=CLOSE | target_priority=HIGH |
| ts_rule_002 | is_attacking_ally=TRUE | target_priority=HIGH |
| ts_rule_003 | target_attack_power=HIGH AND target_distance=CLOSE | target_priority=HIGH |
| ts_rule_004 | target_hp_ratio=LOW AND target_distance=MID | target_priority=HIGH |
| ts_rule_005 | target_attack_power=HIGH AND target_distance=MID | target_priority=HIGH |
| ts_rule_006 | target_hp_ratio=MEDIUM AND target_distance=CLOSE | target_priority=MEDIUM |
| ts_rule_007 | target_attack_power=MEDIUM AND target_distance=CLOSE | target_priority=MEDIUM |
| ts_rule_008 | target_attack_power=LOW AND target_distance=FAR | target_priority=LOW |
| ts_rule_009 | target_hp_ratio=HIGH AND target_distance=FAR | target_priority=LOW |
| ts_rule_010 | target_hp_ratio=LOW AND target_distance=FAR | target_priority=LOW |
| ts_rule_011 | target_attack_power=LOW AND target_hp_ratio=HIGH | target_priority=LOW |
| ts_rule_012 | is_attacking_ally=FALSE AND target_distance=FAR | target_priority=LOW |

### 7.4 推論結果の利用

`BattleSimulator._select_target_fuzzy()` が全索敵済み候補に対して推論を実行し、  
最高スコアの候補を選択する。結果は `BattleLog.fuzzy_scores` に記録される。

推論が失敗した場合は `CLOSEST`（最近傍）フォールバックに自動切替する。

---

## 8. AGGRESSIVE 武器選択ルールセット（`aggressive_weapon_selection.json`）

**layer:** `weapon_selection`

### 8.1 入力変数

| 変数 | 範囲 | ファジィ集合 | 説明 |
|------|------|------------|------|
| `distance_to_target` | 0〜3000 | CLOSE / MID / FAR | アクターからターゲットへの距離 (m) |
| `current_en_ratio` | 0.0〜1.0 | LOW / MEDIUM / HIGH | アクターの現在EN比率 |
| `ammo_ratio` | 0.0〜1.0 | LOW / MEDIUM / HIGH | 対象武器の弾薬残量比率（無制限時は 1.0 固定） |
| `target_beam_resistance` | 0.0〜1.0 | LOW / HIGH | ターゲットのビーム耐性 |
| `target_physical_resistance` | 0.0〜1.0 | LOW / HIGH | ターゲットの実弾耐性 |
| `weapon_is_beam` | 0.0 or 1.0 | FALSE / TRUE | 対象武器がビーム武器か実弾武器か |

### 8.2 出力変数

| 変数 | 範囲 | 説明 |
|------|------|------|
| `weapon_score` | 0.0〜1.0 | 武器の状況適合度スコア。最高スコアの武器を選択する |

### 8.3 主要ルール

| ID | 条件 | 出力 |
|----|------|------|
| ws_rule_001 | CLOSE AND beam_resistance=LOW AND weapon_is_beam=TRUE | weapon_score=HIGH |
| ws_rule_002 | en_ratio=LOW AND weapon_is_beam=TRUE | weapon_score=LOW |
| ws_rule_003 | ammo_ratio=LOW AND weapon_is_beam=FALSE | weapon_score=LOW |
| ws_rule_004 | MID AND physical_resistance=LOW AND weapon_is_beam=FALSE | weapon_score=HIGH |
| ws_rule_005 | en_ratio=HIGH AND CLOSE AND weapon_is_beam=TRUE | weapon_score=HIGH |
| ws_rule_006 | CLOSE AND beam_resistance=HIGH AND weapon_is_beam=TRUE | weapon_score=LOW |
| ws_rule_007 | CLOSE AND physical_resistance=LOW AND weapon_is_beam=FALSE | weapon_score=HIGH |
| ws_rule_008 | en_ratio=HIGH AND beam_resistance=LOW AND weapon_is_beam=TRUE | weapon_score=HIGH |
| ws_rule_009 | ammo_ratio=HIGH AND physical_resistance=LOW AND weapon_is_beam=FALSE | weapon_score=HIGH |
| ws_rule_010 | CLOSE AND en_ratio=LOW AND weapon_is_beam=FALSE | weapon_score=HIGH |
| ws_rule_011 | MID AND en_ratio=MEDIUM AND weapon_is_beam=TRUE | weapon_score=MEDIUM |
| ws_rule_012 | beam_resistance=HIGH AND weapon_is_beam=TRUE | weapon_score=LOW |
| ws_rule_013 | physical_resistance=HIGH AND weapon_is_beam=FALSE | weapon_score=LOW |
| ws_rule_014 | FAR AND beam_resistance=LOW AND weapon_is_beam=TRUE | weapon_score=MEDIUM |

### 8.4 推論結果の利用

`BattleSimulator._select_weapon_fuzzy(actor, target)` が使用可能な全武器に対して推論を実行し、  
最高スコアの武器を選択する。

**使用可能条件（事前フィルタ）:**
- クールダウン残りターン = 0
- 現在EN ≥ 武器の消費EN（`en_cost`）
- 弾薬残量 > 0（`max_ammo` が `None` または 0 の場合は無制限として扱う）

使用可能な武器が0件の場合は `None` を返し、呼び出し元の `_action_phase()` が  
`get_active_weapon()` にフォールバックする。

推論が失敗した場合は最初の使用可能武器にフォールバックする。

---

## 9. 使用例

```python
from app.engine.fuzzy_engine import FuzzyEngine

# JSON からエンジンを生成
engine = FuzzyEngine.from_json("data/fuzzy_rules/aggressive.json")

# 推論実行
result = engine.infer({
    "hp_ratio": 0.8,
    "enemy_count_near": 1.0,
    "distance_to_nearest_enemy": 200.0,
})
# result: {"action": 0.075}  ← action の出力集合の重心値

# デバッグ情報付き推論
result, debug = engine.infer_with_debug({
    "hp_ratio": 0.1,
    "enemy_count_near": 8.0,
})
# debug["fuzzified"]   → ファジフィケーション結果
# debug["activations"] → ルール発火強度
```

---

## 10. 拡張ガイド

### 新しい戦略モードの追加

1. `backend/data/fuzzy_rules/` 配下に新しい JSON ファイルを作成する（例: `defensive.json`）
2. `schema.json` の `strategy` フィールドに新しいモード名を文書化する
3. コードの変更は不要

### 新しいメンバーシップ関数タイプの追加

1. `fuzzy_engine.py` に新しいクラスを追加する（`MembershipFunction` を継承）
2. `_build_mf()` 関数に新しいタイプの分岐を追加する
3. `schema.json` の `type` の `enum` を更新する

---

## 11. テスト

テストファイル: `backend/tests/unit/test_fuzzy_engine.py`

```bash
cd backend && python -m pytest tests/unit/test_fuzzy_engine.py -v
```

主なテストケース:
- `TriangleMF` / `TrapezoidMF` の境界値テスト
- ファジフィケーションのクランプ処理テスト
- AND / OR ルール評価テスト
- 全ルール不発火時のフォールバックテスト
- `aggressive.json` のロード・推論統合テスト
- `defensive.json` / `sniper.json` / `assault.json` / `retreat.json` のロードテスト
- `_select_target_fuzzy()` のターゲット選択テスト（`backend/tests/unit/test_simulation.py`）
- `_select_weapon_fuzzy()` / `_is_weapon_usable()` の武器選択テスト（`backend/tests/unit/test_simulation.py`）
- ASSAULT 近距離攻撃行動・近距離武器優先テスト（`backend/tests/unit/test_simulation.py`）
- RETREAT HP LOW 撤退行動・遠距離武器優先テスト（`backend/tests/unit/test_simulation.py`）

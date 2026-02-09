# 戦略AIの高度化 実装レポート

## 概要

このレポートは、シミュレーションエンジンのAI（ターゲット選択ロジック）強化機能の実装状況をまとめたものです。

## 実装済み機能

### 1. Backend: 評価指標の計算ロジック

**ファイル**: `backend/app/engine/simulation.py`

#### `_calculate_strategic_value(target: MobileSuit) -> float`
- **目的**: 敵を倒すことの戦略価値を計算
- **実装場所**: 200-220行目
- **計算式**: `target.max_hp + weapon_power_avg`
- **特徴**:
  - 敵の最大HPと平均武器威力を合算
  - 高HP・高火力の敵ほど高い価値を持つ
  - パイロットレベルは将来的な拡張ポイント

#### `_calculate_threat_level(actor: MobileSuit, target: MobileSuit) -> float`
- **目的**: 自機にとっての脅威度を計算
- **実装場所**: 222-253行目
- **計算式**: `(attack_power / current_hp) * (1000 / distance)`
- **特徴**:
  - 距離が近いほど脅威度が上昇
  - 敵の火力が高いほど脅威度が上昇
  - 自機のHPが低いほど脅威度が上昇
  - ゼロ除算対策を実装（最小距離1.0m、最小HP1.0）

### 2. Backend: ターゲット選択ロジック

**ファイル**: `backend/app/engine/simulation.py`

#### `_select_target(actor: MobileSuit) -> MobileSuit | None`
- **実装場所**: 255-315行目
- **対応戦術**:

##### WEAKEST (弱敵狙い)
```python
target = min(detected_targets, key=lambda t: t.current_hp)
```
- 現在HPが最も低い敵を優先
- 確実に撃破できる敵を狙う戦術

##### STRONGEST (強敵狙い)
```python
target = max(detected_targets, key=lambda t: self._calculate_strategic_value(t))
```
- 戦略価値が最も高い敵を優先
- 高HP・高火力の強敵を優先排除

##### THREAT (脅威排除)
```python
target = max(detected_targets, key=lambda t: self._calculate_threat_level(actor, t))
```
- 脅威度が最も高い敵を優先
- 自機にとって最も危険な敵を先に排除

##### CLOSEST (近接優先)
```python
target = min(detected_targets, key=lambda t: np.linalg.norm(t.position.to_numpy() - pos_actor))
```
- 最も近い敵を優先（従来の動作）
- 素早く交戦可能な敵を選択

##### RANDOM (ランダム)
```python
target = random.choice(detected_targets)
```
- ランダムに敵を選択
- 予測不可能な動きをする

### 3. ログ出力機能

#### `_log_target_selection(actor, target, reason, details)`
- **実装場所**: 134-157行目
- **機能**: ターゲット選択の理由をログに記録
- **出力例**:
  - `"Test MSがターゲット選択: Zaku (戦術: WEAKEST, HP: 30)"`
  - `"Test MSがターゲット選択: Gundam (戦術: STRONGEST, 戦略価値: 200.0)"`
  - `"Test MSがターゲット選択: Enemy (戦術: THREAT, 脅威度: 1.56)"`
  - `"Test MSがターゲット選択: Close MS (戦術: CLOSEST, 距離: 200m)"`

### 4. Frontend: 戦術設定UI

**ファイル**: `frontend/src/app/garage/page.tsx`

#### 実装場所: 336-363行目

```tsx
<select
  value={formData.tactics.priority}
  onChange={(e) => setFormData({...})}
>
  <option value="CLOSEST">CLOSEST - 最寄りの敵</option>
  <option value="WEAKEST">WEAKEST - HP最小の敵</option>
  <option value="STRONGEST">STRONGEST - 強敵優先 (戦略価値)</option>
  <option value="THREAT">THREAT - 脅威度優先</option>
  <option value="RANDOM">RANDOM - ランダム選択</option>
</select>
```

## テスト結果

### ユニットテスト（15個すべて合格）

1. `test_simulator_initialization` - シミュレータ初期化
2. `test_process_turn_order` - ターン順序処理
3. `test_player_vs_enemies_victory` - プレイヤー勝利シナリオ
4. `test_player_defeat` - プレイヤー敗北シナリオ
5. `test_multiple_enemies` - 複数敵との戦闘
6. `test_logs_generated` - ログ生成
7. `test_tactics_weakest_priority` - WEAKEST戦術
8. `test_tactics_ranged_behavior` - RANGED距離設定
9. `test_tactics_flee_behavior` - FLEE回避設定
10. `test_tactics_default_values` - デフォルト戦術値
11. `test_calculate_strategic_value` - 戦略価値計算
12. `test_calculate_threat_level` - 脅威度計算
13. `test_tactics_strongest_priority` - STRONGEST戦術
14. `test_tactics_threat_priority` - THREAT戦術
15. `test_target_selection_with_multiple_tactics` - 複数戦術の比較

### 統合シナリオテスト

Issue記載のシナリオ「自機の近くにザク（弱・近）、遠くにガンダム（強・遠）」で検証:

- ✓ `CLOSEST` → ザクを狙う
- ✓ `STRONGEST` → ガンダムを狙う
- ✓ `THREAT` → 脅威度に基づいて選択
- ✓ `WEAKEST` → ダメージを受けた敵を選択

## コード品質

### Linting
```
$ ruff check app/engine/simulation.py
All checks passed!
```

### Type Checking
```
$ mypy app/engine/simulation.py
Success: no issues found in 1 source file
```

## 完了条件の達成状況

- ✅ `_calculate_strategic_value` メソッド実装
- ✅ `_calculate_threat_level` メソッド実装
- ✅ `_select_target` メソッドの戦術対応
  - ✅ WEAKEST
  - ✅ STRONGEST
  - ✅ THREAT
  - ✅ CLOSEST
  - ✅ RANDOM
- ✅ ターゲット選択理由のログ出力
- ✅ フロントエンドUI実装
- ✅ テストカバレッジ
- ✅ 戦術に応じたターゲット選択の変化を確認

## 性能考慮事項

### キャッシング戦略
現在の実装では、以下の最適化が施されています:

1. **索敵状態の共有**: チーム単位で索敵済みユニットを管理（`team_detected_units`）
2. **変動しない値**: 武器威力やmax_hpは毎回計算せず、必要時にのみ計算
3. **計算コスト**: O(n) の線形時間で最適ターゲットを選択（nは発見済み敵の数）

### 将来的な拡張案
- パイロットレベルを戦略価値計算に組み込む
- 地形や気象条件を脅威度計算に反映
- 複数ターン先を予測する高度なAI

## まとめ

Issue「[Feature] 戦略AIの高度化 (Strategic Value & Threat Assessment)」で要求された全ての機能が実装され、動作確認が完了しました。

- Backend: 評価指標計算とターゲット選択ロジックが完全実装
- Frontend: 戦術設定UIが実装され、5種類の戦術が選択可能
- Tests: 15個のテストが全て合格
- Quality: Linting、Type checkingともに問題なし

単純な「最近接ターゲット」方式から、状況判断に基づく高度な行動が実現されました。

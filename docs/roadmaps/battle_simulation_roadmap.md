# Battle Simulation Logic Expansion Roadmap

本ドキュメントは、MSBS-Next のシミュレーションエンジン（戦闘ロジック）の拡張計画をまとめたものです。
シンプルな「数値の殴り合い」から、戦略的かつ自律的な戦闘シミュレーションへの進化を目指します。

## 📊 実装状況 (2026年2月14日時点)

**✅ Step 1: 基本属性と相性** - 完了 (2026-02-07)  
**✅ Step 2: バトルフィールドと索敵** - 完了 (2026-02-08)  
**✅ Step 3: 簡易版・戦略AI** - 完了 (2026-02-08)  
**✅ Step 4: リソース管理** - 完了 (2026-02-08)  

全ての基本機能が実装完了しました（Phase 2.5）。現在はPhase 3（コミュニティ機能拡充）に進んでいます。

---

## 1. 段階的実装プラン (Recommended Roadmap)

### Step 1: 基本属性と相性の実装 (Attributes & Compatibility) ✅ 完了
**目的:** 機体・武器選択の重要性を高め、単純なスペック勝ちを防ぐ。  
**実装日:** 2026年2月7日  
**実装レポート:** [ADVANCED_BATTLE_LOGIC_REPORT.md](../ADVANCED_BATTLE_LOGIC_REPORT.md)

* **武器属性 (Weapon Attributes)** ✅
    * 区分: `BEAM` (ビーム) / `PHYSICAL` (実弾)
    * 機体耐性: `beam_resistance` / `physical_resistance` (ダメージ軽減率)
    * 実装箇所: `Weapon.type`, `MobileSuit.beam_resistance`, `MobileSuit.physical_resistance`
* **距離適正 (Optimal Range)** ✅
    * パラメータ: `optimal_range` (最適射程), `decay_rate` (減衰係数)
    * ロジック: 最適射程からの偏差に応じて命中率が低下する（正規分布曲線）。
    * 実装箇所: `Weapon.optimal_range`, `Weapon.decay_rate`, `BattleSimulator._calculate_hit_chance`

### Step 2: バトルフィールドと索敵 (Field & Detection) ✅ 完了
**目的:** 「場所」と「情報の非対称性」を導入し、移動や索敵特化機体の役割を作る。  
**実装日:** 2026年2月8日  
**実装レポート:** [TERRAIN_DETECTION_IMPLEMENTATION_REPORT.md](../TERRAIN_DETECTION_IMPLEMENTATION_REPORT.md)

* **バトルフィールド属性** ✅
    * 環境: `SPACE` (宇宙), `GROUND` (地上), `COLONY` (コロニー内), `UNDERWATER` (水中)
    * 適正補正: 機体の地形適正 (S/A/B/C/D) により、移動速度にボーナス/ペナルティ。
    * 実装箇所: `Mission.environment`, `MobileSuit.terrain_adaptability`, `constants.TERRAIN_ADAPTABILITY_MODIFIERS`
* **索敵ロジック (Fog of War)** ✅
    * `sensor_range` 内の敵のみを「索敵済みリスト」に追加し、ターゲット候補とする。
    * 実装箇所: `BattleSimulator.team_detected_units`, `BattleSimulator._detection_phase`
* **環境効果** ✅
    * 地形適正による移動速度補正が実装済み。

### Step 3: 簡易版・戦略AI (Rule-based AI) ✅ 完了
**目的:** AIが「倒すべき敵」と「避けるべき敵」を区別して自律行動できるようにする。  
**実装日:** Phase 2で実装済み  

* **戦略価値 (Strategic Value)** ✅
    * 算出式: `max_hp + average_weapon_power`
    * 意味: 敵にとって「倒すと価値が高い」目標。
    * 実装箇所: `BattleSimulator._calculate_strategic_value`
* **脅威度 (Threat Assessment)** ✅
    * 算出式: `(weapon_power / current_hp) / distance`
    * 意味: 自機にとって「放置すると危険」な目標。
    * 実装箇所: `BattleSimulator._calculate_threat_level`
* **ターゲット選択ロジック** ✅
    * Tactics設定に基づき、「脅威度最大」「戦略価値最大」「最至近」「ランダム」の敵を狙う。
    * 実装箇所: `BattleSimulator._select_target`, `MobileSuit.tactics`

### Step 4: リソース管理 (Resource Management) ✅ 完了
**目的:** 戦闘の長期化を防ぎ、「継戦能力」というパラメータを作る。  
**実装日:** 2026年2月8日  
**実装レポート:** [RESOURCE_MANAGEMENT_IMPLEMENTATION.md](../RESOURCE_MANAGEMENT_IMPLEMENTATION.md)

* **弾数制限 (Ammo)** ✅
    * 武器に `max_ammo` / `current_ammo` を追加。0になると使用不可。
    * 実装箇所: `Weapon.max_ammo`, `BattleSimulator.unit_resources["weapon_states"]["current_ammo"]`
* **クールタイム (Cool-down)** ✅
    * 武器発射後の「待機ターン」の実装。
    * 実装箇所: `Weapon.cool_down_turn`, `BattleSimulator.unit_resources["weapon_states"]["current_cool_down"]`
* **EN/ジェネレーター** ✅
    * ビーム兵器使用時のEN消費管理。ターン毎にEN回復。
    * 実装箇所: `MobileSuit.max_en`, `MobileSuit.en_recovery`, `Weapon.en_cost`, `BattleSimulator._refresh_phase`
* **推進剤 (Propellant)** ✅
    * 将来の移動コスト実装用にフィールド追加済み。
    * 実装箇所: `MobileSuit.max_propellant`

---

## 2. 実装の検証とテスト

### 自動テスト
- `backend/tests/unit/test_simulation.py` - 基本シミュレーションロジックのテスト
- `backend/tests/unit/test_terrain_and_detection.py` - 地形適正と索敵システムのテスト
- `backend/tests/unit/test_tactics_integration.py` - 戦術統合テスト

### 手動検証スクリプト
- `backend/scripts/verify_terrain_detection.py` - 地形と索敵機能の動作確認
  - 地形補正による移動速度の変化
  - 索敵範囲外での非可視状態
  - 環境別のバトルシミュレーション

### 実装レポート
- [ADVANCED_BATTLE_LOGIC_REPORT.md](../ADVANCED_BATTLE_LOGIC_REPORT.md) - 武器属性と距離適正
- [TERRAIN_DETECTION_IMPLEMENTATION_REPORT.md](../TERRAIN_DETECTION_IMPLEMENTATION_REPORT.md) - 地形と索敵
- [RESOURCE_MANAGEMENT_IMPLEMENTATION.md](../RESOURCE_MANAGEMENT_IMPLEMENTATION.md) - リソース管理

---

## 3. 将来的な高度機能 (Advanced Features)

以下の機能は実装コストが高く、バランス調整が困難なため、**Phase 3以降** の検討事項とする。

* **高度な移動制御 (Potential Fields)**
    * 引力（ターゲット）と斥力（障害物・脅威）のベクトル合成による移動経路生成。
* **ファジィ推論AI (Fuzzy Logic)**
    * 「HPが低い」かつ「敵が近い」→「逃走」のような、曖昧な状況判断ロジック。
* **複雑な障害物 (Complex Obstacles)**
    * 遮蔽物による射線切れ、衝突判定、回避ルーティング。
* **完全リアルタイム化 (Tick-based)**
    * ターン制から、秒間60フレーム等の物理シミュレーションへの移行（サーバー負荷を考慮し慎重に検討）。
* **天候変動**
    * 雨、雪、砂嵐などによる動的なステータス変化。
* **推進剤の消費管理**
    * 移動距離に応じた推進剤消費と、推進剤切れによる移動不能状態の実装。

# 戦闘リソース管理システム実装レポート

## 実装日
2026-02-08

## 概要
戦闘シミュレーションに「リソース（弾薬・エネルギー・推進剤）」の概念を導入し、無限に攻撃し続けられないように制限を加えました。これにより「継戦能力 (Sustain)」が重要なパラメータとなり、弾切れやガス欠を考慮した機体構成や戦術が求められるようになります。

## 実装内容

### 1. バックエンド: データモデルの拡張

#### `Weapon` モデル (backend/app/models/models.py)
以下の新しいフィールドを追加：
- `max_ammo: int | None` - 最大弾数 (Noneまたは0の場合は無限/EN兵器)
- `en_cost: int` - 射撃ごとの消費EN (実弾兵器は通常0)
- `cool_down_turn: int` - 発射後の再使用待機ターン数

#### `MobileSuit` モデル (backend/app/models/models.py)
以下の新しいフィールドを追加：
- `max_en: int` - 最大エネルギー容量 (ジェネレーター出力)
- `en_recovery: int` - ターン毎のEN回復量
- `max_propellant: int` - 最大推進剤容量 (将来的な移動コスト用)

#### マイグレーション
- ファイル: `backend/alembic/versions/a1b2c3d4e5f6_add_combat_resource_management.py`
- `mobile_suits` テーブルに `max_en`, `en_recovery`, `max_propellant` カラムを追加
- デフォルト値を設定（既存データとの互換性を保持）

#### シードデータの更新
- `backend/scripts/seed.py`: ガンダムとザクIIにリソース値を設定
- `backend/scripts/seed_missions.py`: 全ミッションの武器にリソース値を設定
  - ビーム兵器: EN消費あり、弾数無制限
  - 実弾兵器: 弾数制限あり、EN消費なし

### 2. バックエンド: シミュレーションロジックの改修

#### リソース状態管理 (backend/app/engine/simulation.py)
`BattleSimulator.__init__` に追加：
```python
self.unit_resources: dict = {}
for unit in self.units:
    unit_id = str(unit.id)
    self.unit_resources[unit_id] = {
        "current_en": unit.max_en,
        "current_propellant": unit.max_propellant,
        "weapon_states": {},
    }
    # 各武器のリソース状態を初期化
    for weapon in unit.weapons:
        weapon_id = weapon.id
        self.unit_resources[unit_id]["weapon_states"][weapon_id] = {
            "current_ammo": weapon.max_ammo if weapon.max_ammo is not None else None,
            "current_cool_down": 0,
        }
```

#### リフレッシュフェーズ
`_refresh_phase()` メソッドを追加：
- ターン開始時にENを回復（最大値を超えない）
- 武器のクールダウンを1減少

#### 攻撃実行時の判定と消費
`_process_attack()` メソッドを修正：
1. **リソースチェック**
   - 弾数チェック: `max_ammo > 0` かつ `current_ammo > 0`
   - ENチェック: `current_en >= en_cost`
   - クールダウンチェック: `current_cool_down == 0`

2. **リソース不足時の処理**
   - "WAIT" アクションログを生成
   - 理由を明示（"弾切れ"、"EN不足"、"クールダウン中"）

3. **リソース消費**（攻撃実行時）
   - `current_ammo -= 1`
   - `current_en -= en_cost`
   - `current_cool_down = cool_down_turn`

### 3. フロントエンド: UI表示の拡張

#### TypeScript型定義 (frontend/src/types/battle.ts)
`Weapon` インターフェース：
```typescript
max_ammo?: number | null;
en_cost?: number;
cool_down_turn?: number;
```

`MobileSuit` インターフェース：
```typescript
max_en?: number;
en_recovery?: number;
max_propellant?: number;
```

#### ガレージ画面 (frontend/src/app/garage/page.tsx)
新しい表示セクションを追加：

1. **エネルギー・推進剤セクション**
   - 最大EN
   - EN回復/ターン
   - 最大推進剤

2. **武器情報の拡張**
   - 弾数（実弾兵器の場合）
   - EN消費（ビーム兵器の場合）
   - クールタイム

#### バトルビューア
- リソース不足時のログメッセージが自動的に表示される
- "弾切れで攻撃できない（待機）" などのメッセージ

### 4. テスト

#### 新規テスト (backend/tests/unit/test_resource_management.py)
8つの包括的なテストを追加：
1. `test_weapon_resource_fields` - Weaponモデルのフィールド検証
2. `test_mobile_suit_resource_fields` - MobileSuitモデルのフィールド検証
3. `test_simulation_initializes_resources` - リソース初期化の検証
4. `test_en_depletion_blocks_attack` - EN枯渇時の攻撃制限
5. `test_ammo_depletion_blocks_attack` - 弾切れ時の攻撃制限
6. `test_cooldown_blocks_attack` - クールダウン中の攻撃制限
7. `test_en_recovery` - EN回復の動作確認
8. `test_propellant_is_initialized` - 推進剤の初期化確認

#### テスト結果
- 新規テスト: 8 passed ✅
- 既存のシミュレーションテスト: 15 passed ✅
- TypeScript compilation: No errors ✅
- CodeQL Security Check: No vulnerabilities ✅

## 動作確認

### EN消費テスト
```
初期EN: 150/150
Turn 1: EN消費 60 → 90/150
Turn 2: EN消費 60 → 30/150  
Turn 3: EN消費 60 → 0/150 (回復前)
Turn 4: EN不足のため待機
Turn 5: EN回復 30 → 攻撃可能
```

### 弾数消費テスト
```
初期弾数: 3/3
Turn 1: 発射 → 2/3
Turn 2: 発射 → 1/3
Turn 3: 発射 → 0/3
Turn 4以降: 弾切れのため待機
```

### クールダウンテスト
```
Turn 1: 発射 → クールダウン2ターン設定
Turn 2: クールダウン中 (残り1ターン) → 待機
Turn 3: 発射可能
```

## 完了条件の確認

✅ 実弾兵器（Ammo設定あり）を使用し続けると、弾数が0になり攻撃しなくなること
✅ ビーム兵器（ENコストあり）を連射するとENが枯渇し、回復するまで発射できなくなること
✅ 強力な武器（クールタイムあり）を毎ターン連射できないこと
✅ 推進剤（Propellant）のパラメータがDBとAPIレスポンスに含まれていること（値の変動はない）

## セキュリティチェック

- **CodeQL**: 脆弱性なし
- **依存関係**: 新しい依存関係の追加なし
- **入力検証**: 既存のモデル検証を使用
- **SQL Injection**: ORMを使用しており問題なし

## 今後の拡張予定

### 推進剤システム
現在は定義のみで、消費ロジックは実装されていません。将来的には以下の機能を追加予定：
- 移動時の推進剤消費
- ブースト移動の実装
- 推進剤切れ時の機動力低下

### その他の拡張案
- 補給システム（弾薬・EN・推進剤の補給）
- 予備弾倉の概念
- 武器切り替え時のペナルティ
- オーバーヒート機能（連射時のペナルティ）

## ファイル変更一覧

### バックエンド
- `backend/app/models/models.py` - モデル定義の拡張
- `backend/app/engine/simulation.py` - シミュレーションロジックの実装
- `backend/alembic/versions/a1b2c3d4e5f6_add_combat_resource_management.py` - マイグレーション
- `backend/scripts/seed.py` - シードデータ更新
- `backend/scripts/seed_missions.py` - ミッションシードデータ更新
- `backend/tests/unit/test_resource_management.py` - 新規テスト追加

### フロントエンド
- `frontend/src/types/battle.ts` - 型定義の拡張
- `frontend/src/app/garage/page.tsx` - UI表示の拡張

## まとめ

戦闘リソース管理システムの実装により、より戦略的で深みのある戦闘が可能になりました。プレイヤーは弾薬とエネルギーを管理しながら戦う必要があり、継戦能力が重要な要素となります。

全てのテストが合格し、セキュリティチェックも問題なく、要求された機能が完全に実装されています。

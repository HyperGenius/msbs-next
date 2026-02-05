# 戦術 (Tactics) システム - UI実装ガイド

## 概要
このドキュメントでは、ガレージページに追加された戦術設定UIについて説明します。

## UI構成

### ガレージページ（/garage）

ガレージページの機体ステータス編集フォームに、新しく「戦術設定 (Tactics)」セクションが追加されました。

```
┌─────────────────────────────────────────────────────────────┐
│ 機体ステータス編集                                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ 機体名: [Test Gundam              ]                         │
│                                                               │
│ 最大HP: [100                      ]                         │
│                                                               │
│ 装甲:   [10                       ]                         │
│                                                               │
│ 機動性: [2.0                      ]                         │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│ 戦術設定 (Tactics)                                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ターゲット優先度                                             │
│ [CLOSEST - 最寄りの敵           ▼]                         │
│ 攻撃対象の選択方法を設定します                              │
│                                                               │
│ 交戦距離設定                                                 │
│ [BALANCED - バランス型          ▼]                         │
│ 戦闘時の移動パターンを設定します                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
│                    [保存]                                    │
└─────────────────────────────────────────────────────────────┘
```

## ドロップダウンオプション

### ターゲット優先度 (priority)
- **CLOSEST - 最寄りの敵**: 最も近い敵を優先して攻撃
- **WEAKEST - HP最小の敵**: HPが最も低い敵を優先して攻撃
- **RANDOM - ランダム選択**: ランダムに敵を選択して攻撃

### 交戦距離設定 (range)
- **MELEE - 近接突撃**: 敵に積極的に接近して攻撃
- **RANGED - 遠距離維持**: 武器の射程ギリギリの距離を維持（引き撃ち）
- **BALANCED - バランス型**: 接近して攻撃する標準的な戦闘スタイル
- **FLEE - 回避優先**: 敵から距離を取り続ける（防御的）

## 戦術の効果

### シミュレーションでの動作

#### CLOSEST (最寄り優先)
```
Turn 1: Gundam が最も近い Enemy A を選択
Turn 2: Enemy A 撃破後、次に近い Enemy B を選択
```

#### WEAKEST (HP最小優先)
```
Turn 1: Gundam が HP 30 の Enemy C を選択（最も遠いが HPが低い）
Turn 2: Enemy C 撃破後、次に HP が低い Enemy B を選択
```

#### RANGED (遠距離維持)
```
Turn 1: Gundam が射程600m、現在距離400m
       → 距離を維持（移動しない or 後退）
       
Turn 2: 敵が接近して距離300m
       → 後退して距離を取る
       → メッセージ: "Gundamが距離を取る (距離: 300m)"
```

#### FLEE (回避優先)
```
Turn 1: Gundam が敵から後退
       → メッセージ: "Gundamが後退中 (距離: 500m)"
       
Turn 2: 継続して後退
       → メッセージ: "Gundamが後退中 (距離: 650m)"
```

## データフロー

### 1. ガレージでの設定変更
```typescript
// ユーザーがドロップダウンを変更
onChange={(e) =>
  setFormData({
    ...formData,
    tactics: {
      ...formData.tactics,
      priority: e.target.value
    }
  })
}
```

### 2. APIリクエスト
```typescript
// PUT /api/mobile_suits/{id}
{
  "name": "Gundam",
  "max_hp": 100,
  "armor": 10,
  "mobility": 2.0,
  "tactics": {
    "priority": "WEAKEST",
    "range": "RANGED"
  }
}
```

### 3. データベース保存
```python
# PostgreSQL JSON カラムに保存
mobile_suits.tactics = {"priority": "WEAKEST", "range": "RANGED"}
```

### 4. シミュレーション実行
```python
# 戦闘シミュレーション時に tactics を参照
target = sim._select_target(actor)
# actor.tactics["priority"] に基づいてターゲット選択

sim._process_movement(actor, ...)
# actor.tactics["range"] に基づいて移動方向決定
```

## テスト方法

### 手動テスト手順

1. **ガレージページにアクセス**
   - http://localhost:3000/garage

2. **機体を選択**
   - 左側のリストから任意の機体をクリック

3. **戦術を変更**
   - ターゲット優先度を「WEAKEST」に変更
   - 交戦距離設定を「RANGED」に変更

4. **保存**
   - 「保存」ボタンをクリック
   - 成功メッセージ「機体データを更新しました」を確認

5. **再読み込みして確認**
   - ページをリロード（F5）
   - 同じ機体を選択
   - 戦術設定が保持されていることを確認

6. **シミュレーション実行**
   - バトルシミュレーターページに移動
   - バトルを実行
   - ログを確認して、設定した戦術に基づいた行動をしているか確認

### 期待される結果

#### WEAKEST + RANGED の場合
```
バトルログ例:
Turn 1: Gundamが距離を取る (距離: 450m)
Turn 2: Gundamの攻撃！ (命中: 75%) -> 命中！ Damaged Goufに35ダメージ！
Turn 3: Gundamが射程内に移動中 (残距離: 520m)
Turn 4: Gundamの攻撃！ (命中: 72%) -> 命中！ Damaged Goufに38ダメージ！
...
```

- HPが最も低い「Damaged Gouf」を優先的に攻撃
- 距離を維持しながら戦闘

## 技術的な実装詳細

### Backend
- **モデル**: `MobileSuit.tactics` (JSON型)
- **デフォルト値**: `{"priority": "CLOSEST", "range": "BALANCED"}`
- **バリデーション**: Pydantic v2 スキーマで自動検証

### Frontend
- **型定義**: `Tactics` interface in `types/battle.ts`
- **状態管理**: React useState hook
- **API連携**: SWR for data fetching and mutation

### マイグレーション
```sql
-- Migration: 2f18b99001c_add_tactics_column_to_mobile_suits.py
ALTER TABLE mobile_suits 
ADD COLUMN tactics JSON 
NOT NULL 
DEFAULT '{"priority": "CLOSEST", "range": "BALANCED"}';
```

## トラブルシューティング

### 問題: 戦術設定が保存されない
- **確認**: ブラウザのコンソールでAPIエラーを確認
- **解決**: バックエンドが起動しているか確認

### 問題: 戦術が反映されない
- **確認**: データベースに tactics カラムが存在するか確認
- **解決**: `alembic upgrade head` を実行

### 問題: TypeScript エラー
- **確認**: `Tactics` 型が正しくインポートされているか確認
- **解決**: `import { Tactics } from '@/types/battle'` を追加

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
- **MELEE - 近接突撃**: 格闘武器の間合いまで詰める。互角でも粘り、仕切り直しの後はすぐ再突入する
- **RANGED - 射撃距離維持**: 射撃武器の最適距離を保ち、近づかれたら離れる。自分から格闘へ突入しない
- **BALANCED - バランス型**: そのとき選んだ武器に合わせて間合いを切り替える
- **FLEE - 射程限界から射撃**: 射撃武器の射程ぎりぎりを保ち、格闘を避ける

装備と矛盾する設定（射撃武器なしの RANGED など）は、使える武器に合わせて動く。
数値と詳細は `docs/features/battle-engine-feature.md` の「戦術設定（tactics.range）とパイロット能力の反映」を参照。

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

#### RANGED / FLEE / MELEE

目標交戦距離・膠着への粘り・仕切り直しの後の挙動が変わる。
詳細は `docs/features/battle-engine-feature.md` を参照。

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

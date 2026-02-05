# 定期実行バッチとマッチングロジック

## 概要

定期実行バッチシステムは、エントリーされたプレイヤーを集計し、マッチング（ルーム作成）を行い、シミュレーションを一括実行するための機能です。

## アーキテクチャ

### コンポーネント

1. **MatchingService** (`backend/app/services/matching_service.py`)
   - エントリーのグループ化
   - ルーム作成
   - NPC自動生成

2. **バッチスクリプト** (`backend/scripts/run_batch.py`)
   - マッチング処理の実行
   - シミュレーションの実行
   - 結果の保存

3. **GitHub Actions ワークフロー** (`.github/workflows/scheduled-battle.yaml`)
   - 定期実行（スケジュール）
   - 手動トリガー

## データモデルの変更

### BattleEntry

新しいフィールド:
- `is_npc`: NPCかどうかを示すブール値
- `user_id`: `nullable=True` に変更（NPCの場合は `None`）

### BattleResult

新しいフィールド:
- `room_id`: バトルルームへの外部キー参照

### BattleRoom

ステータスの更新:
- `OPEN`: エントリー受付中
- `WAITING`: マッチング完了、シミュレーション待ち
- `COMPLETED`: シミュレーション完了

## 使い方

### 手動実行

```bash
cd backend
python scripts/run_batch.py
```

### 定期実行（GitHub Actions）

1. `.github/workflows/scheduled-battle.yaml` のコメントを外す
2. スケジュール（デフォルト: JST 21:00 = UTC 12:00）に自動実行

### 手動トリガー（GitHub Actions）

1. GitHubのActionsタブを開く
2. "Scheduled Battle Batch" ワークフローを選択
3. "Run workflow" をクリック

## 処理フロー

### 1. マッチングフェーズ

1. ステータスが `OPEN` のルームを取得
2. 各ルームのエントリーを取得
3. 不足分をNPCで埋める（デフォルト: 8機まで）
4. ルームのステータスを `WAITING` に更新

### 2. シミュレーションフェーズ

1. ステータスが `WAITING` のルームを取得
2. 各ルームでシミュレーションを実行
   - エントリーのスナップショットからモビルスーツを復元
   - プレイヤーとエネミーに分ける
   - `BattleSimulator` を実行
3. 結果を保存
   - 各プレイヤーの `BattleResult` を作成
   - ルームのステータスを `COMPLETED` に更新

## NPC生成

NPCは以下のランダムな特性を持ちます:

- **名前**: Zaku II, Gouf, Dom, Gelgoog など
- **HP**: 600-900
- **装甲**: 30-70
- **機動性**: 0.8-1.5
- **武器**: 1-2種類（パワー、射程、命中率がランダム）
- **戦術**: CLOSEST/WEAKEST/RANDOM × MELEE/RANGED/BALANCED

## エラーハンドリング

- 各ルームの処理は独立しており、1つのルームでエラーが発生しても他のルームの処理は継続されます
- エラーログは標準出力に出力されます

## テスト

### ユニットテスト

```bash
cd backend
python -m pytest tests/unit/test_matching_service.py -v
```

### 統合テスト

```bash
cd backend
python tests/integration/test_batch_processing.py
```

## 環境変数

以下の環境変数が必要です:

- `NEON_DATABASE_URL`: PostgreSQLデータベースURL
- `CLERK_JWKS_URL`: Clerk JWKS URL
- `CLERK_SECRET_KEY`: Clerk秘密鍵

## トラブルシューティング

### ルームが作成されない

- エントリーが存在しない場合、ルームは作成されません
- `BattleRoom` のステータスが `OPEN` であることを確認してください

### シミュレーションが実行されない

- ルームのステータスが `WAITING` であることを確認してください
- エントリーにスナップショットが正しく保存されているか確認してください

### NPCが生成されない

- ルームサイズ（デフォルト: 8）とエントリー数を確認してください
- エントリー数がルームサイズ未満の場合、自動的にNPCが生成されます

## 今後の拡張

- チーム分け機能（プレイヤーを2チームに分ける）
- レーティングシステム（プレイヤーの強さに応じたマッチング）
- リプレイ機能（戦闘ログの再生）
- 通知機能（戦闘結果の通知）

# バトル履歴とミッション選択機能 - 実装ガイド

## 概要

このPRでは、以下の機能が実装されました：
1. **バトル結果の永続化**: バトルの結果をデータベースに保存
2. **ミッション選択**: 複数の難易度別ミッションから選択可能
3. **履歴閲覧**: 過去のバトルログを閲覧・再生可能

## 実装内容

### Backend

#### 1. 新しいモデル

**Mission** (`backend/app/models/models.py`)
- `id`: ミッションID
- `name`: ミッション名 (例: "Mission 01: ザク小隊")
- `difficulty`: 難易度 (1-5)
- `description`: ミッション説明
- `enemy_config`: 敵機の構成情報 (JSON)

**BattleResult** (`backend/app/models/models.py`)
- `id`: バトル結果ID (UUID)
- `user_id`: ユーザーID (Clerk)
- `mission_id`: ミッションID
- `win_loss`: 勝敗 ("WIN" / "LOSE" / "DRAW")
- `logs`: バトルログ (JSON)
- `created_at`: 作成日時

#### 2. データベースマイグレーション

```bash
cd backend
# マイグレーション適用
alembic upgrade head
```

#### 3. ミッションシード

```bash
cd backend
# ミッションデータを投入
python scripts/seed_missions.py
```

3つのミッションが登録されます：
- Mission 01: ザク小隊 (難易度1) - ザクII 3機
- Mission 02: 防衛線突破 (難易度2) - ザクII 4機
- Mission 03: エース部隊撃破 (難易度3) - ザクII S型 2機

#### 4. 新しいAPIエンドポイント

**GET /api/missions**
- ミッション一覧を取得
- レスポンス: `Mission[]`

**POST /api/battle/simulate?mission_id={id}**
- 指定されたミッションでシミュレーションを実行
- バトル結果をデータベースに保存
- レスポンス: `BattleResponse`

**GET /api/battles?limit={n}**
- バトル履歴を取得（最新順）
- 認証ユーザーの場合、自分のバトルのみフィルタ
- レスポンス: `BattleResult[]`

**GET /api/battles/{battle_id}**
- 特定のバトル結果の詳細を取得
- レスポンス: `BattleResult`

### Frontend

#### 1. 新しい型定義

**Mission** (`frontend/src/types/battle.ts`)
```typescript
interface Mission {
  id: number;
  name: string;
  difficulty: number;
  description: string;
  enemy_config: { enemies: Array<...> };
}
```

**BattleResult** (`frontend/src/types/battle.ts`)
```typescript
interface BattleResult {
  id: string;
  user_id: string | null;
  mission_id: number | null;
  win_loss: "WIN" | "LOSE" | "DRAW";
  logs: BattleLog[];
  created_at: string;
}
```

#### 2. APIクライアント更新

**新しいフック** (`frontend/src/services/api.ts`):
- `useMissions()`: ミッション一覧取得
- `useBattleHistory(limit)`: バトル履歴取得
- `useBattleDetail(battleId)`: バトル詳細取得

#### 3. メインページ更新 (`frontend/src/app/page.tsx`)

**ミッション選択UI**:
- グリッドレイアウトでミッション一覧を表示
- 各ミッションカードに難易度と説明を表示
- 選択したミッションでバトル開始

**リザルト表示改善**:
- "MISSION COMPLETE" (WIN) または "MISSION FAILED" (LOSE) を大きく表示
- アニメーション付きで視覚的に強調

#### 4. 履歴ページ (`frontend/src/app/history/page.tsx`)

**機能**:
- 過去のバトル記録を一覧表示
- バトル記録を選択してログを閲覧
- ミッション名、勝敗、日時を表示

#### 5. ヘッダー更新

- "History" ボタンを追加して履歴ページへのナビゲーションを追加

## セットアップ手順

### Backend

1. データベースマイグレーション実行:
```bash
cd backend
alembic upgrade head
```

2. ミッションデータのシード:
```bash
python scripts/seed_missions.py
```

3. モビルスーツデータのシード (既存):
```bash
python scripts/seed.py
```

4. バックエンド起動:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

1. 依存関係のインストール:
```bash
cd frontend
npm install
```

2. フロントエンド起動:
```bash
npm run dev
```

3. ブラウザで http://localhost:3000 を開く

## 使用方法

### ミッション選択

1. メインページでミッション一覧が表示されます
2. ミッションをクリックして選択
3. "START MISSION" ボタンをクリックしてバトル開始
4. バトル終了後、"MISSION COMPLETE" または "MISSION FAILED" が表示されます

### バトル履歴閲覧

1. ヘッダーの "History" ボタンをクリック
2. 過去のバトル記録一覧が表示されます
3. バトルをクリックして詳細ログを表示
4. 各ターンのログを確認可能

## テクニカルノート

### データベーススキーマ

```sql
-- missions テーブル
CREATE TABLE missions (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    difficulty INTEGER NOT NULL,
    description VARCHAR NOT NULL,
    enemy_config JSON
);

-- battle_results テーブル
CREATE TABLE battle_results (
    id UUID PRIMARY KEY,
    user_id VARCHAR,
    mission_id INTEGER REFERENCES missions(id),
    win_loss VARCHAR NOT NULL,
    logs JSON,
    created_at TIMESTAMP NOT NULL
);
```

### API動作フロー

1. ユーザーがミッションを選択
2. フロントエンドが `POST /api/battle/simulate?mission_id=X` を呼び出し
3. バックエンドがミッション設定を取得し、敵機を生成
4. シミュレーション実行
5. 結果をデータベースに保存 (`BattleResult`)
6. フロントエンドに結果を返却
7. フロントエンドがリザルトを表示

### セキュリティ考慮事項

- ユーザーIDは Clerk 認証から取得
- 履歴取得時、認証ユーザーは自分のバトルのみ閲覧可能
- バトル詳細は誰でも閲覧可能（UUIDを知っている場合）

## 今後の拡張案

- [ ] バトルリプレイ機能（3D表示での再生）
- [ ] ランキングシステム
- [ ] カスタムミッション作成
- [ ] マルチプレイヤー対戦
- [ ] アチーブメント/実績システム

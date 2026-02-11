# ランキングシステムと他プレイヤー視察機能の実装まとめ

## 概要
PvPvE（対人・対NPC戦）の結果を集計し、プレイヤー間の競争を可視化する「ランキング」機能と、気になるプレイヤーの構成を確認できる「視察（Inspection）」機能を実装しました。

## 実装された機能

### 1. ランキングシステム (Leaderboard)

#### バックエンド
- **データモデル** (`backend/app/models/models.py`)
  - `Season` テーブル: シーズン期間を管理（開始日・終了日、アクティブフラグ）
  - `Leaderboard` テーブル: ユーザーごとのシーズン成績（勝利数、撃墜数、獲得クレジット等）

- **ランキング集計サービス** (`backend/app/services/ranking_service.py`)
  - `get_or_create_current_season()`: 現在のアクティブシーズンを取得または作成
  - `calculate_ranking()`: BattleResult から集計を行い、Leaderboard テーブルを更新（Upsert）
  - `get_current_rankings()`: 現在のシーズンのランキングTop 100を取得

- **API エンドポイント** (`backend/app/routers/rankings.py`)
  - `GET /api/rankings/current`: 現在のシーズンのランキングTop 100を取得
  - `GET /api/rankings/pilot/{user_id}/profile`: 指定したパイロットの公開プロフィール情報を取得

- **バッチ処理統合** (`backend/scripts/run_batch.py`)
  - `update_rankings()` フェーズを追加
  - シミュレーション実行後にランキングを自動更新

#### フロントエンド
- **ランキングページ** (`frontend/src/app/rankings/page.tsx`)
  - 順位、パイロット名、勝利数、撃墜数、獲得クレジットを表示
  - 自分の順位をハイライト表示（緑色の背景）
  - トップ3の順位バッジ表示（金・銀・銅）
  - クリックでプレイヤープロフィールを表示

### 2. プレイヤー視察機能 (Inspection)

#### バックエンド
- **プロフィールAPI** (`GET /api/rankings/pilot/{user_id}/profile`)
  - パイロット名、レベル、勝敗数、撃墜数を取得
  - 現在の機体（Mobile Suit）とパラメータを取得
  - 装備している武器構成（Loadout）を取得
  - 設定している戦術（Tactics）を取得
  - **セキュリティ**: メールアドレス、所持クレジット等の非公開情報は除外

#### フロントエンド
- **プレイヤープロフィールモーダル** (`frontend/src/components/Social/PlayerProfileModal.tsx`)
  - パイロット統計（レベル、勝利数、敗北数、撃墜数）を表示
  - 勝率をプログレスバーで可視化
  - 機体スペック（HP、装甲、機動性、センサー範囲）を表示
  - 装備武器の詳細（威力、射程、命中率、種類）を表示
  - 戦術設定を日本語で表示
  - 習得スキルを一覧表示

### 3. ナビゲーション
- ヘッダーに「Rankings」リンクを追加

## 技術的な実装詳細

### パフォーマンス最適化
- ランキングはリアルタイム集計（毎回 COUNT クエリ）ではなく、**バッチ処理で Leaderboard テーブルに数値を確定させる方式**を採用
- これによりフロントエンドからのアクセス負荷を大幅に軽減

### セキュリティ
- `PlayerProfile` レスポンスモデルに以下の情報は含まれない：
  - メールアドレス
  - 所持クレジット（現在の残高）
  - Clerk ID以外のセンシティブ情報
- テストで自動検証済み（`test_profile_security`）

### データベースマイグレーション
- `c3d4e5f6g7h8_add_season_and_leaderboard_tables.py`
- `seasons` テーブルと `leaderboards` テーブルを作成
- 適切なインデックスとForeign Keyを設定

## テスト

### 自動テスト (`backend/tests/test_ranking_system.py`)
- ✅ ランキングモデルの定義確認
- ✅ ランキングサービスのメソッド確認
- ✅ API エンドポイントの登録確認
- ✅ マイグレーションファイルの存在確認
- ✅ バッチスクリプトへの統合確認
- ✅ プロフィールのセキュリティ確認

### コードレビュー
- ✅ 自動コードレビューでエラーなし

### セキュリティスキャン (CodeQL)
- ✅ Python: アラートなし
- ✅ JavaScript: アラートなし

## 使い方

### バックエンド
1. マイグレーションを実行してテーブルを作成
   ```bash
   cd backend
   alembic upgrade head
   ```

2. バッチ処理を実行してランキングを更新
   ```bash
   python scripts/run_batch.py
   ```

### フロントエンド
1. `/rankings` ページにアクセスしてランキングを確認
2. パイロット名をクリックして詳細プロフィールを表示
3. モーダル内で機体構成や戦術を視察

## 完了条件の確認

- ✅ `/rankings` ページで、勝利数順のプレイヤーリストが確認できる
- ✅ バッチ処理を実行すると、ランキングの数値が更新される
- ✅ ランキング上のプレイヤー名をクリックすると、そのプレイヤーの機体・装備・戦術が見える
- ✅ 他人のプロフィール情報APIからは、個人情報（Clerk ID以外のセンシティブ情報）が漏れていない

## 今後の拡張可能性

1. **リアルタイムランキング更新**: WebSocketを使ってバトル終了時にリアルタイムでランキングを更新
2. **複数のランキング種類**: 勝率順、撃墜数順、獲得クレジット順など
3. **シーズン切り替え機能**: 過去のシーズンのランキングを閲覧
4. **フィルタリング**: レベル帯別、機体種類別のランキング
5. **リプレイ機能**: トップランカーのバトルリプレイを視聴
6. **機体構成のコピー機能**: 気に入った機体構成を自分の機体にコピー

## ファイル一覧

### バックエンド
- `backend/app/models/models.py` - Season, Leaderboard モデル追加
- `backend/app/services/ranking_service.py` - ランキング集計サービス（新規）
- `backend/app/routers/rankings.py` - ランキングAPI（新規）
- `backend/main.py` - ランキングルーター登録
- `backend/scripts/run_batch.py` - ランキング更新フェーズ追加
- `backend/alembic/versions/c3d4e5f6g7h8_add_season_and_leaderboard_tables.py` - マイグレーション（新規）
- `backend/tests/test_ranking_system.py` - ランキングシステムテスト（新規）

### フロントエンド
- `frontend/src/app/rankings/page.tsx` - ランキングページ（新規）
- `frontend/src/components/Social/PlayerProfileModal.tsx` - プレイヤープロフィールモーダル（新規）
- `frontend/src/types/battle.ts` - LeaderboardEntry, PlayerProfile 型定義追加
- `frontend/src/services/api.ts` - useRankings, usePlayerProfile フック追加
- `frontend/src/components/Header.tsx` - ランキングリンク追加

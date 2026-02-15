# MSBS-Next (仮)

ブラウザベースの定期更新型MSバトルシミュレーションゲーム

[![Phase](https://img.shields.io/badge/Phase-2.6_UI%2FUX強化-brightgreen)](docs/roadmap.md)
[![Backend](https://img.shields.io/badge/Backend-Python%20%2F%20FastAPI-blue)](backend/)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js%2015-black)](frontend/)

## 📖 概要

MSBS-Next は、モビルスーツ（MS）をカスタマイズし、戦術を設定して自動シミュレーションバトルに参加する定期更新型タクティカルシミュレーションゲームです。MSBSのプレイ感を現代的なクラウドネイティブ技術で再現・進化させることを目的としています。

### 🎮 コアゲームループ

```
準備期間（プレイヤー操作）
  ├─ 機体カスタマイズ（装備・強化）
  ├─ 戦術設定（ターゲット優先度・交戦距離）
  └─ 次回バトルへのエントリー
         ↓
更新処理（自動実行 - 毎日JST 21:00）
  ├─ マッチング（8-16機でルーム編成）
  ├─ NPC自動生成
  └─ バトルシミュレーション実行
         ↓
結果閲覧
  ├─ 3Dリプレイ確認
  ├─ 経験値・報酬獲得
  └─ 戦績記録
```

## ✨ 主要機能

### 実装済み（Phase 2.6完了）

- ✅ **3Dバトルシミュレーション** - NumPyベースの3D空間計算
- ✅ **高度な戦闘システム** 
  - 武器属性（BEAM/PHYSICAL）と耐性
  - 地形適正（SPACE/GROUND/COLONY/UNDERWATER）
  - 索敵システム（Fog of War）
  - リソース管理（EN、弾薬、クールダウン）
- ✅ **戦術システム** - ターゲット優先度と交戦距離の事前設定
- ✅ **パイロット成長** - レベル、経験値、スキルポイント
- ✅ **4種類のスキル** - 命中率、回避率、攻撃力、クリティカル率向上
- ✅ **経済システム** - 機体強化（Engineering）、機体購入（Shop）
- ✅ **マッチングシステム** - バトルエントリー、ルーム管理、NPC自動生成
- ✅ **バッチ処理** - 定期更新自動実行（GitHub Actions対応）
- ✅ **3Dリプレイビューア** 
  - React Three Fiberによる3D表示
  - 環境別演出（星空、地面、水面エフェクト）
  - 索敵範囲可視化（アニメーションリング）
  - リアルタイムリソース表示（ENゲージ、弾薬）
  - ダメージフラッシュエフェクト
- ✅ **ダッシュボードUI** - カウントダウンタイマー、エントリー管理、結果モーダル

### 開発予定（Phase 3 - β版）

- ⏳ ランキング & 統計
- ⏳ NPC永続化 & 自律成長
- ⏳ 勢力システム
- ⏳ コンテンツ拡充（機体、武器、ミッション）
- ⏳ ソーシャル機能（フレンド、チーム戦、ギルド）

## 🛠️ 技術スタック

| 領域 | 技術 |
|------|------|
| **Frontend** | Next.js 15 (App Router), TypeScript, Tailwind CSS |
| **3D Graphics** | React Three Fiber, @react-three/drei |
| **Backend** | Python 3.11, FastAPI, Pydantic v2, SQLModel |
| **Simulation** | NumPy (ベクトル計算), Pure Python Logic |
| **Database** | Neon (PostgreSQL), Alembic |
| **Auth** | Clerk (JWT/JWKS) |
| **Infrastructure** | Vercel (Frontend), Cloud Run (Backend), Terraform (Neon) |

## 🚀 セットアップ

### 前提条件

- Python 3.11+
- Node.js 18+
- Neon PostgreSQL アカウント
- Clerk アカウント

### 1. リポジトリのクローン

```bash
git clone https://github.com/HyperGenius/msbs-next.git
cd msbs-next
```

### 2. Backend セットアップ

```bash
cd backend

# 仮想環境の作成と有効化
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 環境変数の設定
cp .env.example .env
# .envファイルを編集してNeon接続情報とClerk設定を記入

# データベースマイグレーション
alembic upgrade head

# シードデータの投入
python scripts/seed.py
```

### 3. Frontend セットアップ

```bash
cd frontend

# 依存関係のインストール
npm install

# 環境変数の設定
cp .env.example .env.local
# .env.localファイルを編集してClerk設定を記入
```

### 4. 開発サーバーの起動

**Backend (ターミナル1):**
```bash
cd backend
uvicorn main:app --reload
```
→ http://localhost:8000

**Frontend (ターミナル2):**
```bash
cd frontend
npm run dev
```
→ http://localhost:3000

### 5. 本番環境へのデプロイ

本番環境（Vercel + Cloud Run）へのデプロイ手順については、[デプロイガイド](docs/DEPLOYMENT.md)を参照してください。

## 📁 プロジェクト構造

```
msbs-next/
├── backend/                 # Python/FastAPI バックエンド
│   ├── app/
│   │   ├── core/           # 設定、スキル定義
│   │   ├── db/             # DB接続
│   │   ├── models/         # SQLModel (ORM) & Pydantic
│   │   ├── routers/        # APIエンドポイント
│   │   ├── services/       # ビジネスロジック
│   │   └── engine/         # バトルシミュレーションエンジン
│   ├── alembic/            # DBマイグレーション
│   ├── scripts/            # バッチ処理、シードデータ
│   └── tests/              # ユニット & 統合テスト
│
├── frontend/               # Next.js フロントエンド
│   └── src/
│       ├── app/           # App Router ページ
│       ├── components/    # UIコンポーネント
│       │   ├── ui/       # SciFiデザインシステム
│       │   ├── BattleViewer/  # 3Dバトルビューア
│       │   └── Dashboard/     # ダッシュボード
│       ├── services/      # API呼び出し
│       └── types/         # TypeScript型定義
│
├── docs/                  # プロジェクトドキュメント
│   ├── roadmap.md        # 開発ロードマップ ⭐
│   ├── battle_simulation_roadmap.md  # シミュレーション仕様
│   └── ...               # 各種実装ガイド
│
└── infra/                # Infrastructure as Code
    └── neon/             # Terraform (Neon DB)
```

## 📚 ドキュメント

### 主要ドキュメント

- **[開発ロードマップ](docs/roadmap.md)** - プロジェクト全体像と進捗状況
- **[Agent Guidelines](Agent.md)** - AI Agent/開発者向けガイドライン
- **[バトルシミュレーション仕様](docs/battle_simulation_roadmap.md)** - エンジンの詳細
- **[バッチシステム](docs/BATCH_SYSTEM.md)** - 定期更新処理の仕様
- **[パイロットシステム](docs/PILOT_SYSTEM.md)** - 成長・スキルシステム

### 実装ガイド

- [Clerk認証セットアップ](docs/CLERK_SETUP.md)
- [Neonマイグレーション](docs/neon_migration.md)
- [戦術システム](docs/TACTICS_IMPLEMENTATION.md)

## 🧪 テスト

### Backend テスト

```bash
cd backend

# 全テスト実行
pytest

# カバレッジ付き
pytest --cov=app --cov-report=html

# 特定のテスト
pytest tests/unit/test_simulation.py
```

### Frontend テスト

```bash
cd frontend

# E2Eテスト（準備中）
npm run test:e2e
```

## 🔧 開発コマンド

### Backend

```bash
# バッチ処理の手動実行
python scripts/run_batch.py

# マイグレーション作成
alembic revision --autogenerate -m "description"

# Linter & Formatter
ruff check .          # チェックのみ
ruff check --fix .    # 自動修正
ruff format .         # フォーマット

# 型チェック
mypy .
```

### Frontend

```bash
# 型チェック
npm run type-check

# Lint
npm run lint

# Build
npm run build
```

## 🎯 開発フロー

1. **Issue作成** - 実装する機能やバグ修正の内容を明確にする
2. **ブランチ作成** - `feature/機能名` or `fix/バグ名`
3. **実装** - Agent.mdのガイドラインに従って開発
4. **テスト** - ユニットテスト、統合テストの作成・実行
5. **PR作成** - 日本語で説明文を記述（`.github/copilot-instructions.md`参照）
6. **レビュー & マージ**

## 🤝 コントリビューション

コントリビューション歓迎です！以下を参照してください：

1. [Agent.md](Agent.md) - コーディング規約とベストプラクティス
2. [roadmap.md](docs/roadmap.md) - 開発中の機能と優先順位
3. PRは日本語で記述してください

## 📝 ライセンス

このプロジェクトは開発中のプロトタイプです。ライセンスは未定です。

## 🔗 リンク

- ドキュメント: [docs/](docs/)
- Issue トラッカー: [GitHub Issues](https://github.com/HyperGenius/msbs-next/issues)

---

**Developed with ❤️ using GitHub Copilot and modern web technologies**

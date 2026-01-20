# Agent.md - AI Agent Guidelines
このドキュメントは、本プロジェクト（MSBS-Next）の開発を担当するAI Agent（GitHub Copilot Agent等）に向けた、アーキテクチャ、コーディング規約、テスト方針、および開発プロセスを定義するものです。

## 1. プロジェクト概要

プロジェクトはPhase.0です

## 2. 技術スタック (Tech Stack)

### Backend

* **Language**: Python 3.11
* **Framework**: FastAPI
* **Lint/Format**: Ruff, Mypy
* **Testing**: Pytest

### Frontend

* **Framework**: Next.js 15+ (App Router)
* **Language**: TypeScript
* **Styling**: Tailwind CSS
* **UI Library**: shadcn/ui
* **Data Fetching**: SWR
* **Testing**: Playwright (E2E)

### Database & Infra

* **DB**: Supabase (PostgreSQL)
* **Auth**: Supabase Auth
* **Deploy**: Vercel (Frontend), Render/Cloud Run (Backend)

---

## 3. ディレクトリ構造と責務

```text
/
├── backend/
│   ├── app/
│   │   ├── api/        # 依存性注入 (Dependencies)
│   │   ├── core/       # 設定 (Config), 定数, プロンプト定義
│   │   ├── db/         # DB接続クライアント
│   │   ├── models/     # Pydanticモデル (Schema)
│   │   ├── routers/    # APIエンドポイント定義
│   │   └── services/   # ビジネスロジック
│   ├── scripts/        # バッチ処理, ユーティリティスクリプト
│   └── tests/          # 単体テスト (Unit Tests)
│
├── frontend/
│   ├── src/
│   │   ├── app/        # Next.js App Router Pages
│   │   ├── components/ # UIコンポーネント
│   │   ├── services/   # API呼び出し関数
│   │   ├── types/      # TypeScript型定義
│   │   └── utils/      # 汎用ユーティリティ
│   └── e2e/            # Playwrightテスト
│
└── supabase/
    └── migrations/     # DBマイグレーションファイル (.sql)

```

---

## 4. コーディング規約 (Coding Standards)

### Backend (Python/FastAPI)

1. **Type Hinting**: すべての関数引数と戻り値に型ヒントを記述すること。
2. **Pydantic Models**: APIのリクエスト/レスポンスは必ず `app/models` 配下のPydanticモデルで定義する。
3. **Service Layer**: ロジックは `routers` に直書きせず、`app/services` 内のクラスに切り出すこと。
4. **Error Handling**: 例外は適切にキャッチし、`HTTPException` を送出する。ログ出力を忘れないこと。

### Frontend (Next.js/TypeScript)

1. **Server/Client Components**: デフォルトは Server Component。`useState` や `useEffect` が必要な場合のみ `'use client'` を付与する。
2. **SWR Usage**: データ取得は `useSWR` を使用し、`src/utils/fetcher.ts` を経由する。
3. **Type Safety**: `any` 型の使用は原則禁止。`src/types` に定義された型を使用する。

### Database (Supabase)

1. **RLS (Row Level Security)**: すべてのテーブルでRLSを有効化する。`user_id` による分離を徹底する。
2. **Migrations**: スキーマ変更は必ず `supabase/migrations` にSQLファイルを追加して行う。

---

## 5. テスト方針 (Testing Strategy)

### Backend: Unit Testing

**「ロジックの正確性」と「外部依存の分離」を重視する。**

* **Tool**: `pytest`
* **Location**: `backend/tests/unit/`
* **Rules**:
* DB接続や外部API（Supabase）は **必ずMock化 (`unittest.mock`)** する。
* 正常系だけでなく、異常系（APIエラー等）のテストケースも網羅する。



### Frontend: E2E Testing

**「ユーザー体験（UX）の担保」を重視する。**

* **Tool**: `Playwright`
* **Location**: `frontend/e2e/`
* **Rules**:
* 実際のブラウザ操作をシミュレーションする（ログイン → 操作 → 確認）。
* テスト用アカウント（環境変数 `TEST_EMAIL` 等）を使用する。
* APIのレスポンス待ちには `page.waitForResponse` 等を使用し、 `setTimeout` のような固定待機は避ける。



---

## 6. 開発フロー (Development Process)

AI AgentがIssueに取り組む際は、以下の手順を遵守してください。

1. **Design**: `app/models` (Backend) や `src/types` (Frontend) の定義から始める。データ構造を先に確定させる。
2. **Backend Impl**: `Service` クラスの実装 → `Router` の実装 → `Unit Test` の作成・パス。
3. **Frontend Impl**: `Service` (API Client) の実装 → UIコンポーネントの実装 → ページへの組み込み。
4. **Integration**: `E2E Test` を実行し、一連のフローが動作することを確認する。

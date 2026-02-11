# Agent.md - AI Agent Guidelines
このドキュメントは、本プロジェクト（MSBS-Next）の開発を担当するAI Agent（GitHub Copilot Agent等）に向けた、アーキテクチャ、コーディング規約、テスト方針、および開発プロセスを定義するものです。

## 1. プロジェクト概要

**プロジェクト名:** MSBS-Next (仮)  
**ジャンル:** 定期更新型タクティカルバトルシミュレーション (PvPvE)  
**プラットフォーム:** Webブラウザ (PC/Mobile対応予定)  
**現在のフェーズ:** Phase 2.6 (UI/UX強化) 完了、Phase 3 (β版) 準備中

### 実装済み主要機能

- ✅ 3D空間でのリアルタイムバトルシミュレーション
- ✅ ユーザー認証 (Clerk)
- ✅ 機体カスタマイズ & 戦術設定
- ✅ 高度な戦闘システム (武器属性、地形適正、索敵、リソース管理)
- ✅ パイロット成長 & スキルシステム
- ✅ 機体強化 (Engineering) & ショップ
- ✅ バトルエントリー & マッチング
- ✅ バッチ処理システム (定期更新対応)
- ✅ 3Dバトルビューア (環境別演出、索敵範囲可視化、リソース表示)
- ✅ ダッシュボード (エントリー管理、カウントダウン、結果モーダル)

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
* **UI Library**: カスタムSciFiデザインシステム (`src/components/ui/`)
* **3D Rendering**: React Three Fiber (@react-three/fiber, @react-three/drei)
* **Data Fetching**: SWR
* **Testing**: Playwright (E2E, 準備中)

### Database & Infra

* **DB**: Neon (PostgreSQL)
* **Auth**: Clerk
* **Deploy**: Vercel (Frontend), Render/Cloud Run (Backend)

---

## 3. ディレクトリ構造と責務

```text
/
├── backend/
│   ├── app/
│   │   ├── core/       # 設定 (Config), スキル定義, 定数
│   │   ├── db/         # DB接続 (db.py)
│   │   ├── models/     # SQLModel (ORM) & Pydanticモデル
│   │   ├── routers/    # APIエンドポイント定義
│   │   ├── services/   # ビジネスロジック (マッチング、パイロット、整備等)
│   │   └── engine/     # バトルシミュレーションエンジン
│   ├── alembic/        # DBマイグレーション
│   ├── scripts/        # バッチ処理 (run_batch.py), シードデータ
│   └── tests/          # 単体テスト & 統合テスト
│       ├── unit/       # ユニットテスト
│       └── integration/# 統合テスト
│
├── frontend/
│   ├── src/
│   │   ├── app/        # Next.js App Router Pages
│   │   ├── components/ # UIコンポーネント
│   │   │   ├── ui/     # カスタムSciFiコンポーネント (SciFiButton等)
│   │   │   ├── Dashboard/ # ダッシュボード関連コンポーネント
│   │   │   └── BattleViewer/ # 3Dバトルビューア (R3F)
│   │   ├── services/   # API呼び出し (api.ts)
│   │   ├── types/      # TypeScript型定義
│   │   └── utils/      # 汎用ユーティリティ
│   └── e2e/            # Playwrightテスト (準備中)
│
├── docs/               # プロジェクトドキュメント
│   ├── roadmap.md      # 開発ロードマップ (メインドキュメント)
│   └── ...             # 各種実装ガイド & レポート
│
└── infra/              # Terraform HCL
    └── neon/           # Neon DB作成
```

---

## 4. コーディング規約 (Coding Standards)

### Backend (Python/FastAPI)

1.  **完全な型ヒントの付与 (Type Hints)**
    * すべての関数・メソッドの**引数**および**戻り値**に型ヒントを明記すること。
    * 戻り値がない場合は `-> None` を記述すること。

2. **Ruff準拠**
    * 提案するコードは Ruff のLinterおよびFormatterルールに適合していること。

3.  **`Any` 型の回避**
    * `typing.Any` の使用は原則禁止とする。
    * 型が動的に変わる場合や外部ライブラリの制約など、やむを得ない場合のみ使用し、その際は**理由をコメントで明記**すること（例: `# library X returns untyped dict`）。

4.  **Mypy エラーの解消**
    * 実装コードは `mypy` (Strict mode) のチェックをパスしなければならない。
    * `disallow_untyped_defs = true` 準拠とし、すべての関数引数と戻り値に型ヒントを記述すること。Any型は極力避け、Pydanticモデルや具体的な型を使用すること
    * Import整理: 標準ライブラリ、サードパーティ、ローカルモジュールの順序を守ること（Ruffが自動処理するが、AIも意識して出力すること）。
    * `# type: ignore` の使用は最終手段とし、使用する場合は理由を併記すること。

5.  **Pydantic / SQLModel の活用**
    * 辞書 (`dict`) をそのまま受け渡しするのではなく、可能な限り Pydantic モデルや SQLModel クラスを使用して構造化データを扱うこと。

6.  **検証**
    * コード修正後は必ずローカルで `pre-commit run --all-files` (または `mypy .`) を実行し、静的解析エラーがないことを確認してから提案すること。

### Frontend (Next.js/TypeScript)

1. **Server/Client Components**: デフォルトは Server Component。`useState` や `useEffect` が必要な場合のみ `'use client'` を付与する。
2. **SWR Usage**: データ取得は `useSWR` を使用し、`src/utils/fetcher.ts` を経由する。
3. **Type Safety**: `any` 型の使用は原則禁止。`src/types` に定義された型を使用する。
4. **Component Complexity (Logic Extraction)**:
   - データの整形、フィルタリング、複雑な状態計算ロジックはコンポーネント内に記述せず、必ず **Custom Hooks** (`useLogicName`) に切り出す。
   - コンポーネントは「描画」に専念し、ロジックを持たないようにする (View vs Logic の分離)。
   - 実装例: `BattleViewer` → `useBattleSnapshot`, `useBattleEvents` に状態計算を分離
5. **React Three Fiber (R3F) Separation**:
   - 3Dシーン (`Canvas` 内部) と 2D UI (HTML オーバーレイ) は、同じファイルに混在させず、それぞれ別のコンポーネントファイルに分割する。
   - `Canvas` を含む親コンポーネントは、レイアウトとデータの受け渡しのみを行う構成（Container Component）にする。
   - 実装例: `BattleViewer/index.tsx` (Container) → `scene/BattleScene.tsx` (3D) + `ui/BattleOverlay.tsx` (2D UI)
6. **Constants & Utils**:
   - 複数の場所で使用される定数や、3行以上の計算ロジック（色計算など）は `utils/` や `constants.ts` に移動し、純粋関数として定義する。
   - 実装例: `BattleViewer/utils.ts` - HPバー色計算、環境色取得
7. **SciFi Design System**:
   - UIコンポーネントは `src/components/ui/` のカスタムコンポーネントを使用する。
   - 利用可能: `SciFiButton`, `SciFiPanel`, `SciFiHeading`, `SciFiSelect`, `SciFiInput` 等
   - 統一感のあるサイバーパンク風デザインを維持する。

### Database (Neon/PostgreSQL)

1. **Alembic Migrations**: スキーマ変更は必ず `alembic` を使用してマイグレーションファイルを生成・適用する。
2. **SQLModel ORM**: データアクセスには SQLModel を使用し、型安全性を確保する。

#### マイグレーション作成時の注意事項

複数ブランチで並行してマイグレーションを作成すると、**複数のheadリビジョン**が発生し、`alembic upgrade head` がエラーになります。

**コンフリクト回避のベストプラクティス:**

1. **マイグレーション作成前に履歴を確認する**
   ```bash
   cd backend
   alembic heads  # 複数のheadがないか確認（1つであるべき）
   alembic history  # マイグレーション履歴と依存関係を確認
   ```

2. **mainブランチを最新化してから作業する**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature
   cd backend
   alembic upgrade head  # 最新の状態に更新
   ```

3. **複数headが発生した場合の解決方法**
   ```bash
   # 現在のheadを確認
   alembic heads
   
   # 2つのheadをマージするマイグレーションを作成
   alembic merge -m "merge_heads" <revision1> <revision2>
   
   # マージマイグレーションを適用
   alembic upgrade head
   ```

4. **Dry Run（マイグレーションの事前確認）**
   ```bash
   # 実行されるSQLを確認（実際には適用されない）
   alembic upgrade head --sql
   
   # 特定のリビジョンまでのSQLを確認
   alembic upgrade <revision_id> --sql
   
   # 現在のDBバージョンを確認
   alembic current
   
   # 次に実行されるマイグレーションを確認
   alembic show head
   ```

---

## 5. テスト方針 (Testing Strategy)

### Backend: Unit Testing

**「ロジックの正確性」と「外部依存の分離」を重視する。**

* **Tool**: `pytest`
* **Location**: `backend/tests/unit/`
* **Rules**:
* DB接続や外部APIは **必ずMock化 (`unittest.mock`)** する。
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
4. **Integration**: `E2E Test` を実行し、一連のフローが動作することを確認する（現在準備中）。

---

## 7. プロジェクト固有の重要事項

### バトルシミュレーションエンジン

* **Location**: `backend/app/engine/simulation.py`
* **Class**: `BattleSimulator`
* **Key Features**:
  - 3D空間でのベクトル計算（NumPy使用）
  - 武器属性（BEAM/PHYSICAL）と耐性システム
  - 地形適正による移動速度補正
  - 索敵システム（Fog of War）
  - リソース管理（EN、弾薬、クールダウン）
  - 戦術（Tactics）に基づくAI行動

### バッチ処理システム

* **Location**: `backend/scripts/run_batch.py`
* **Purpose**: 定期更新型ゲームの自動マッチング＆シミュレーション実行
* **Flow**:
  1. `MatchingService` でエントリーをルーム分け
  2. NPC自動生成（不足分を補う）
  3. 各ルームでバトルシミュレーション実行
  4. 結果をDBに保存
* **Schedule**: GitHub Actions (毎日JST 21:00 / UTC 12:00) - 手動トリガーも可能

### 3Dビジュアライゼーション

* **Location**: `frontend/src/components/BattleViewer/`
* **Structure**:
  - `index.tsx` - Container Component
  - `scene/BattleScene.tsx` - 3Dシーン（Canvas内部）
  - `ui/BattleOverlay.tsx` - 2D UIオーバーレイ
  - `hooks/` - カスタムフック（状態計算、イベント取得）
  - `utils.ts` - ユーティリティ関数
* **Features**:
  - 環境別演出（SPACE/GROUND/COLONY/UNDERWATER）
  - 索敵範囲可視化（アニメーションリング）
  - リアルタイムリソース表示
  - ダメージフラッシュエフェクト

### 主要ドキュメント

開発時に参照すべき主要ドキュメント：

* **`docs/roadmap.md`** - プロジェクトの全体像、実装済み機能、今後の計画
* **`docs/battle_simulation_roadmap.md`** - シミュレーションエンジンの詳細仕様
* **`docs/BATCH_SYSTEM.md`** - バッチ処理システムの仕様
* **`docs/PILOT_SYSTEM.md`** - パイロット成長・スキルシステム
* **実装レポート** (ルートディレクトリの `*_REPORT.md`, `*_SUMMARY.md`) - 各機能の実装詳細

### 環境設定

* **Backend起動**: `cd backend && uvicorn main:app --reload`
* **Frontend起動**: `cd frontend && npm run dev`
* **バッチ実行**: `cd backend && python scripts/run_batch.py`
* **マイグレーション**: `cd backend && alembic upgrade head`
* **テスト実行**: `cd backend && pytest`

---

## 8. Pull Request作成時の注意

PRを作成する際は、以下を必ず含めてください：

1. **変更内容の要約** - 何を実装したか
2. **関連Issue** - `Closes #123` 形式でリンク
3. **テスト結果** - 実行したテストとその結果
4. **スクリーンショット** - UI変更の場合は必須
5. **ドキュメント更新** - 必要に応じてREADMEやdocs/を更新

**PR説明文は日本語で記述すること。**（`.github/copilot-instructions.md`に規定）

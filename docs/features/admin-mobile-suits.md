# マスター機体データ管理画面 — 管理者専用エディタ

## 概要

`data/master/mobile_suits.json` のマスター機体データを Web UI 上で直接編集・追加・削除できる管理者専用画面。

---

## Backend API

### エンドポイント一覧

すべてのエンドポイントは `X-API-Key` ヘッダーによる認証が必要。

| メソッド | パス | 説明 |
|---|---|---|
| `GET` | `/api/admin/mobile-suits` | 全マスター機体一覧取得 |
| `POST` | `/api/admin/mobile-suits` | 新規機体追加 |
| `PUT` | `/api/admin/mobile-suits/{ms_id}` | 既存機体の更新 |
| `DELETE` | `/api/admin/mobile-suits/{ms_id}` | 機体削除 |

### 認証

リクエストヘッダーに以下を付与する：

```
X-API-Key: <ADMIN_API_KEY>
```

`ADMIN_API_KEY` は環境変数で設定する。未設定の場合は `500` を返す。

### ステータスコード

| コード | 意味 |
|---|---|
| `200` | 成功 (GET / PUT) |
| `201` | 作成成功 (POST) |
| `204` | 削除成功 (DELETE) |
| `401` | APIキー不正 |
| `404` | 対象機体が見つからない |
| `409` | ID重複 / ショップ在庫参照 |
| `422` | バリデーションエラー（ID形式不正 / weapons 空など） |

### バリデーションルール

- 機体 `id`: スネークケース英数字のみ（例: `rx_78_2`）。正規表現 `^[a-z0-9_]+$`
- `specs.weapons`: 最低1件必須
- DELETE 時: 同名機体がプレイヤー所有の mobile_suits テーブルに存在する場合は `409`

### リクエスト例

#### POST — 新規機体追加

```json
POST /api/admin/mobile-suits
X-API-Key: <key>
Content-Type: application/json

{
  "id": "rx_78_2",
  "name": "RX-78-2 Gundam",
  "price": 1500,
  "faction": "FEDERATION",
  "description": "宇宙世紀を代表する機体。",
  "specs": {
    "max_hp": 1000,
    "armor": 80,
    "mobility": 1.2,
    "sensor_range": 600,
    "beam_resistance": 0.1,
    "physical_resistance": 0.2,
    "melee_aptitude": 1.2,
    "shooting_aptitude": 1.3,
    "accuracy_bonus": 5.0,
    "evasion_bonus": 0.0,
    "acceleration_bonus": 1.0,
    "turning_bonus": 1.0,
    "weapons": [
      {
        "id": "beam_rifle",
        "name": "Beam Rifle",
        "power": 150,
        "range": 500,
        "accuracy": 75,
        "type": "BEAM",
        "optimal_range": 320,
        "decay_rate": 0.09,
        "is_melee": false
      }
    ]
  }
}
```

#### PUT — 既存機体の部分更新

```json
PUT /api/admin/mobile-suits/rx_78_2
X-API-Key: <key>
Content-Type: application/json

{
  "price": 1800,
  "description": "改良型仕様。"
}
```

---

## Frontend

### ルーティング

`/admin/mobile-suits`

### アクセス制御

`src/middleware.ts` で Clerk の `publicMetadata.role === "admin"` をチェック。
非管理者はトップページ (`/`) にリダイレクト。

### 環境変数

| 変数名 | 説明 |
|---|---|
| `NEXT_PUBLIC_API_URL` | バックエンド API の URL（デフォルト: `http://127.0.0.1:8000`） |
| `NEXT_PUBLIC_ADMIN_API_KEY` | 管理者 API キー（フロントエンドからバックエンドへの X-API-Key） |

#### `NEXT_PUBLIC_ADMIN_API_KEY` の設定方法

フロントエンドが `X-API-Key` ヘッダーに付与する値は、バックエンドの `ADMIN_API_KEY` 環境変数と一致させる必要がある。

**ローカル開発**

`frontend/.env.local` に記載する（`.gitignore` 対象なのでコミットしない）：

```env
NEXT_PUBLIC_ADMIN_API_KEY=your_secret_key_here
```

バックエンド側にも同じ値を設定する：

```env
# backend/.env
ADMIN_API_KEY=your_secret_key_here
```

`your_secret_key_here` は任意の安全なランダム文字列を使用する（例: `openssl rand -hex 32` で生成）。

**本番環境（Vercel）**

Vercel ダッシュボードの **Settings → Environment Variables** から `NEXT_PUBLIC_ADMIN_API_KEY` を追加する。
値はバックエンド（Cloud Run）のシークレットマネージャーに設定した `ADMIN_API_KEY` と同一にする。

> [!WARNING]
> `NEXT_PUBLIC_` プレフィックスの変数はブラウザバンドルに含まれる。本番では IP 制限・Clerk ロールチェック等のアクセス制御と併用し、管理者画面 URL を公開しないこと。

### コンポーネント構成

```
src/
├── app/
│   └── admin/
│       └── mobile-suits/
│           └── page.tsx           # 管理画面エントリーポイント
├── components/
│   └── admin/
│       ├── MobileSuitTable.tsx    # 機体一覧テーブル（ソート・フィルタ付き）
│       ├── MobileSuitEditForm.tsx # 全パラメータ編集フォーム（Zod バリデーション）
│       ├── MobileSuitRadarChart.tsx # バランス比較レーダーチャート（recharts）
│       └── CloneDialog.tsx        # Clone & Edit ダイアログ
└── hooks/
    └── useAdminMobileSuits.ts     # SWR を用いた CRUD フック
```

### 機能詳細

#### 機体一覧テーブル (`MobileSuitTable`)

- 名前・勢力・価格・HP・装甲・機動性を表示
- 各列ヘッダークリックでソート（昇順/降順）
- テキストフィルタ（name / id / faction で絞り込み）
- 編集中の機体は行がハイライト表示

#### 詳細編集フォーム (`MobileSuitEditForm`)

- `react-hook-form` + `zod` によるバリデーション
- 全スペック・武装パラメータを編集可能
- フィールド横にインラインエラーメッセージ表示
- 武装リストの動的追加・削除

#### バランス比較チャート (`MobileSuitRadarChart`)

- `recharts` の `RadarChart` を使用
- 5軸: HP・装甲・機動性・射撃適性・格闘適性
- 各軸は全機体最大値を 100 として正規化
- 選択機体（橙）と全機体平均（シアン点線）の2系列表示

#### Clone & Edit (`CloneDialog`)

- 選択中の機体をコピーして新しい ID を付けて新規追加
- ID バリデーション（スネークケース英数字のみ）

#### 楽観的更新とロールバック

`useAdminMobileSuits` フックで SWR の `mutate` を使用し、API 呼び出し前にキャッシュを先行更新。
エラー時は自動ロールバック（`rollbackOnError: true`）。

---

## テスト

### Backend

```bash
cd backend
NEON_DATABASE_URL="sqlite:///test.db" ADMIN_API_KEY="test_key" python -m pytest tests/unit/test_admin_mobile_suits.py -v
```

テスト内容:
- 認証チェック（キーなし / 不正キー）
- GET 一覧取得
- POST 新規追加（正常 / ID 重複 409 / ID 不正 422 / weapons 空 422）
- PUT 更新（正常 / 404 / weapons 空 422）
- DELETE 削除（正常 / 404 / 在庫参照 409）
- JSON ファイル永続化確認

### Frontend

```bash
cd frontend
npx vitest run --project unit
```

テスト内容 (`tests/unit/mobileSuitEditFormValidation.test.ts`):
- `weaponSchema`: id 形式 / 必須フィールド / accuracy 範囲 / type enum など
- `masterMobileSuitSchema`: id 形式 / 価格 / スペック値範囲 / weapons 必須 1 件以上

---

## 関連ファイル

- `backend/app/routers/admin.py` — CRUD API ルーター
- `backend/app/services/mobile_suit_service.py` — CRUD ロジック
- `backend/app/core/gamedata.py` — JSON 読み書き・キャッシュ
- `backend/app/core/auth.py` — `verify_admin_api_key` 依存関数
- `backend/app/models/models.py` — `MasterMobileSuitEntry` / `MasterMobileSuitCreate` / `MasterMobileSuitUpdate`
- `backend/data/master/mobile_suits.json` — マスターデータ
- `frontend/src/app/admin/mobile-suits/page.tsx` — 管理画面
- `frontend/src/middleware.ts` — 管理者ロールガード

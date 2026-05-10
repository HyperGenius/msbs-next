# マスター武器データ管理画面 — 管理者専用エディタ

## 概要

`data/master/weapons.json` のマスター武器データを Web UI 上で直接編集・追加・削除できる管理者専用画面。

---

## Backend API

### エンドポイント一覧

すべてのエンドポイントは `X-API-Key` ヘッダーによる認証が必要。

| メソッド | パス | 説明 |
|---|---|---|
| `GET` | `/api/admin/weapons` | 全マスター武器一覧取得 |
| `POST` | `/api/admin/weapons` | 新規武器追加 |
| `PUT` | `/api/admin/weapons/{weapon_id}` | 既存武器の更新 |
| `DELETE` | `/api/admin/weapons/{weapon_id}` | 武器削除 |

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
| `404` | 対象武器が見つからない |
| `409` | ID重複 / パイロットインベントリ参照 |
| `422` | バリデーションエラー（ID形式不正など） |

### バリデーションルール

- 武器 `id`: スネークケース英数字のみ（例: `beam_rifle`）。正規表現 `^[a-z0-9_]+$`
- DELETE 時: パイロットのインベントリ（`Pilot.inventory`）に当該 ID が存在する場合は `409`

### リクエスト例

#### POST — 新規武器追加

```json
POST /api/admin/weapons
X-API-Key: <key>
Content-Type: application/json

{
  "id": "beam_rifle",
  "name": "Beam Rifle",
  "price": 800,
  "description": "ガンダム用ビームライフル。高威力・高精度のビーム兵器。",
  "weapon": {
    "id": "beam_rifle",
    "name": "Beam Rifle",
    "power": 150,
    "range": 500,
    "accuracy": 75,
    "type": "BEAM",
    "weapon_type": "RANGED",
    "optimal_range": 320.0,
    "decay_rate": 0.09,
    "is_melee": false,
    "max_ammo": null,
    "en_cost": 10,
    "cooldown_sec": 1.0,
    "fire_arc_deg": 30.0
  }
}
```

#### PUT — 既存武器の部分更新

```json
PUT /api/admin/weapons/beam_rifle
X-API-Key: <key>
Content-Type: application/json

{
  "price": 900,
  "description": "改良型仕様。"
}
```

#### PUT — 武器パラメータの更新

```json
PUT /api/admin/weapons/beam_rifle
X-API-Key: <key>
Content-Type: application/json

{
  "weapon": {
    "id": "beam_rifle",
    "name": "Beam Rifle",
    "power": 160,
    "range": 520,
    "accuracy": 78,
    "type": "BEAM",
    "optimal_range": 340.0,
    "decay_rate": 0.08,
    "is_melee": false
  }
}
```

---

## Frontend

### ルーティング

`/admin/weapons`

### アクセス制御

`src/middleware.ts` で Clerk の `publicMetadata.role === "admin"` をチェック。
非管理者はトップページ (`/`) にリダイレクト。

### 環境変数

| 変数名 | 説明 |
|---|---|
| `NEXT_PUBLIC_API_URL` | バックエンド API の URL（デフォルト: `http://127.0.0.1:8000`） |
| `NEXT_PUBLIC_ADMIN_API_KEY` | 管理者 API キー（フロントエンドからバックエンドへの X-API-Key） |

### コンポーネント構成

```
src/
├── app/
│   └── admin/
│       └── weapons/
│           └── page.tsx              # 管理画面エントリーポイント
├── components/
│   └── admin/
│       ├── WeaponTable.tsx           # 武器一覧テーブル（ソート・フィルタ付き）
│       ├── WeaponEditForm.tsx        # 全パラメータ編集フォーム（Zod バリデーション）
│       ├── WeaponRadarChart.tsx      # バランス比較レーダーチャート（recharts）
│       └── WeaponCloneDialog.tsx     # Clone & Edit ダイアログ
└── hooks/
    └── useAdminWeapons.ts            # SWR を用いた CRUD フック
```

### 機能詳細

#### 武器一覧テーブル (`WeaponTable`)

- 名前・価格・武器属性（BEAM/PHYSICAL）・近接フラグ・威力・射程・命中率を表示
- 各列ヘッダークリックでソート（昇順/降順）
- テキストフィルタ（name / id / type で絞り込み）
- 編集中の武器は行がハイライト表示

#### 詳細編集フォーム (`WeaponEditForm`)

- `react-hook-form` + `zod` によるバリデーション
- 全パラメータ（`power`, `range`, `accuracy`, `type`, `weapon_type`, `optimal_range`, `decay_rate`, `is_melee`, `max_ammo`, `en_cost`, `cooldown_sec`, `fire_arc_deg`）を編集可能
- フィールド横にインラインエラーメッセージ表示

#### バランス比較チャート (`WeaponRadarChart`)

- `recharts` の `RadarChart` を使用
- 5軸: 威力・射程・命中率・最適射程・減衰率
- 各軸は全武器の最大値を 100 として正規化（動的スケール）
- 減衰率軸は小さいほど高性能なため表示上反転（`1 - 正規化値`）
- 選択武器（橙）と全武器平均（シアン点線）の2系列表示

#### Clone & Edit (`WeaponCloneDialog`)

- 選択中の武器をコピーして新しい ID を付けて新規追加
- ID バリデーション（スネークケース英数字のみ）

#### 楽観的更新とロールバック

`useAdminWeapons` フックで SWR の `mutate` を使用し、API 呼び出し前にキャッシュを先行更新。
エラー時は自動ロールバック（`rollbackOnError: true`）。

---

## テスト

### Backend

```bash
cd backend
NEON_DATABASE_URL="sqlite:///test.db" ADMIN_API_KEY="test_key" python -m pytest tests/unit/test_admin_weapons.py -v
```

テスト内容:
- 認証チェック（キーなし / 不正キー）
- GET 一覧取得
- POST 新規追加（正常 / ID 重複 409 / ID 不正 422）
- PUT 更新（正常 / 武器パラメータ更新 / 404）
- DELETE 削除（正常 / 404 / インベントリ参照 409）
- JSON ファイル永続化確認

### Frontend

```bash
cd frontend
npx vitest run --project unit
```

テスト内容 (`tests/unit/weaponEditFormValidation.test.ts`):
- `masterWeaponSchema`: id 形式 / 必須フィールド / accuracy 範囲 / type enum / weapon_type enum など

---

## 関連ファイル

- `backend/app/routers/admin.py` — CRUD API ルーター（`weapon_router` を追加）
- `backend/app/services/weapon_service.py` — CRUD ロジック
- `backend/app/core/gamedata.py` — JSON 読み書き・キャッシュ（`get_master_weapons` / `save_master_weapons`）
- `backend/app/core/auth.py` — `verify_admin_api_key` 依存関数
- `backend/app/models/models.py` — `MasterWeaponEntry` / `MasterWeaponCreate` / `MasterWeaponUpdate`
- `backend/data/master/weapons.json` — マスターデータ
- `frontend/src/app/admin/weapons/page.tsx` — 管理画面
- `frontend/src/middleware.ts` — 管理者ロールガード

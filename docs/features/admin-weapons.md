# マスター武器データ管理画面 — 管理者専用エディタ

## 概要

開発者・運営が `data/master/weapons.json` のマスター武器データを **Web UI 上で直接編集・追加・削除** できる管理者専用画面。

---

## API エンドポイント

全エンドポイントは `X-API-Key` ヘッダー（環境変数 `ADMIN_API_KEY`）による認証が必要。

### GET /api/admin/weapons

全マスター武器一覧を返す。

**レスポンス例:**
```json
[
  {
    "id": "beam_rifle",
    "name": "Beam Rifle",
    "price": 800,
    "description": "ガンダム用ビームライフル。高威力・高精度のビーム兵器。",
    "weapon": {
      "id": "beam_rifle",
      "name": "Beam Rifle",
      "power": 300,
      "range": 600,
      "accuracy": 80,
      "type": "BEAM",
      "weapon_type": "RANGED",
      "optimal_range": 400.0,
      "decay_rate": 0.05,
      "is_melee": false,
      "max_ammo": null,
      "en_cost": 0,
      "cooldown_sec": 1.0,
      "fire_arc_deg": 30.0
    }
  }
]
```

### POST /api/admin/weapons

新規マスター武器を追加する。

**リクエスト:** `MasterWeaponCreate` オブジェクト（`id`, `name`, `price`, `description`, `weapon` を含む）

**バリデーション:**
- `id` はスネークケース英数字のみ許可（`^[a-z0-9_]+$`）
- `id` が重複する場合は `409 Conflict` を返す

**レスポンス:** `201 Created` + 作成された `MasterWeaponEntry`

### PUT /api/admin/weapons/{weapon_id}

既存マスター武器を更新する。

**リクエスト:** `MasterWeaponUpdate` オブジェクト（全フィールド Optional）
- `name`, `price`, `description`, `weapon` を部分的に更新可能

**レスポンス:**
- `200 OK` + 更新された `MasterWeaponEntry`
- `404 Not Found`: 対象 `weapon_id` が存在しない場合

### DELETE /api/admin/weapons/{weapon_id}

マスター武器を削除する。

**バリデーション:**
- `player_weapons` テーブルで `master_weapon_id` として参照されている場合は `409 Conflict` を返す

**レスポンス:**
- `204 No Content`: 削除成功
- `404 Not Found`: 対象が存在しない
- `409 Conflict`: `player_weapons` テーブルに参照がある場合

---

## 認証エラー

| ステータス | 条件 |
|-----------|------|
| `401 Unauthorized` | `X-API-Key` ヘッダーが不正または不一致 |
| `422 Unprocessable Content` | `X-API-Key` ヘッダーが存在しない |
| `500 Internal Server Error` | サーバー側で `ADMIN_API_KEY` が未設定 |

---

## フロントエンド

### ルーティング

`/admin/weapons` — 管理者専用ページ（`middleware.ts` の Clerk `publicMetadata.role === "admin"` チェックにより保護）

### 機能一覧

| 機能 | 説明 |
|------|------|
| **武器一覧テーブル** | 名前・価格・武器種別（BEAM/PHYSICAL）・近接フラグ・威力・射程・命中率を表示。ソート・フィルタ対応 |
| **詳細編集フォーム** | 全パラメータ（`power`, `range`, `accuracy`, `type`, `weapon_type`, `optimal_range`, `decay_rate`, `is_melee`, `max_ammo`, `en_cost`, `cooldown_sec`, `fire_arc_deg`）を編集 |
| **新規追加フォーム** | 新規武器の追加。ID は自動で weapon.id にも同期 |
| **Clone & Edit** | 選択中の武器をベースに新しい ID でコピーを作成 |
| **バランス比較チャート** | 選択中の武器と全武器平均を **レーダーチャート（威力・射程・命中率・最適射程・減衰率の5軸）** で表示。全武器最大値で正規化し、減衰率は反転表示 |
| **トースト通知** | 保存成功・失敗をトーストで通知 |
| **削除確認ダイアログ** | 削除操作の確認ダイアログ |

### コンポーネント構成

```
src/
├── app/admin/weapons/page.tsx          # ページコンポーネント
├── hooks/useAdminWeapons.ts            # SWR フック（CRUD + 楽観的更新）
└── components/admin/
    ├── WeaponTable.tsx                 # 武器一覧テーブル
    ├── WeaponEditForm.tsx              # 全パラメータ編集フォーム（react-hook-form + zod）
    ├── WeaponRadarChart.tsx            # バランス比較レーダーチャート（recharts）
    └── WeaponCloneDialog.tsx           # Clone & Edit ダイアログ
```

### 環境変数

| 変数名 | 説明 |
|--------|------|
| `NEXT_PUBLIC_API_URL` | バックエンド API のベース URL（デフォルト: `http://127.0.0.1:8000`） |
| `NEXT_PUBLIC_ADMIN_API_KEY` | 管理者 API キー |

---

## 関連ファイル

- `backend/app/routers/admin.py` — CRUD API ルーター（`weapon_router`）
- `backend/app/services/weapon_service.py` — CRUD ロジック
- `backend/app/core/gamedata.py` — JSON 読み書き・キャッシュ（`get_master_weapons` / `save_master_weapons`）
- `backend/app/core/auth.py` — `verify_admin_api_key` 依存関数
- `backend/app/models/models.py` — `MasterWeaponEntry` / `MasterWeaponCreate` / `MasterWeaponUpdate`
- `backend/data/master/weapons.json` — マスターデータ
- `frontend/src/app/admin/weapons/page.tsx` — 管理画面
- `frontend/src/middleware.ts` — 管理者ロールガード

---

## テスト

### バックエンド

```bash
cd backend && NEON_DATABASE_URL="sqlite:///test.db" ADMIN_API_KEY="test_key" \
  python -m pytest tests/unit/test_admin_weapons.py -v
```

テスト項目:
- 認証テスト（不正キー → 401、キーなし → 422）
- `GET /api/admin/weapons` 全件取得
- `POST` 新規追加・重複 409・不正 ID 422
- `PUT` 更新・スペック更新・存在しない ID 404
- `DELETE` 削除・存在しない ID 404・参照あり 409
- JSON ファイル永続化確認

### フロントエンド

```bash
cd frontend && npx vitest run tests/unit/weaponEditFormValidation.test.ts
```

テスト項目:
- エントリー ID・名前・価格のバリデーション
- weapon スペック（power・range・accuracy・type・weapon_type・is_melee など）のバリデーション

# マスター機体データ管理画面 — 管理者専用エディタ

## 概要

マスター機体データを Web UI 上で直接編集・追加・削除できる管理者専用画面。
データは `master_mobile_suits` PostgreSQL テーブルに永続化されるため、デプロイ後も変更が失われない。

> [!NOTE]
> Issue #383 で `name_ja`（日本語表示名）を追加したが、ゲーム側フロントエンド（`frontend/`）に
> 言語切替UI・国際化（i18n）フレームワークは未導入のため、現状は管理画面での編集・保存までがスコープ。
> 言語選択に応じた表示切替は別途対応が必要。

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
| `POST` | `/api/admin/simulate-combat` | 1対1 攻撃シミュレーション（ダメージ・命中率）（Issue #381） |

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
- `weapon_slot_count`: 1以上の整数。`specs.weapons` の件数が `weapon_slot_count` を超える場合は `422`（Issue #383）
- `beam_generator_lv`: 0以上の整数。`specs.weapons` 内に `type == "BEAM"` かつ `required_beam_generator_lv` が `beam_generator_lv` を超える武器が含まれる場合は `422`（Issue #383）
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
  "name_ja": "ガンダム",
  "model_number": "RX-78-2",
  "price": 1500,
  "faction": "FEDERATION",
  "description": "宇宙世紀を代表する機体。",
  "weapon_slot_count": 2,
  "beam_generator_lv": 1,
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
        "is_melee": false,
        "required_beam_generator_lv": 1
      }
    ]
  }
}
```

> `name_ja` / `model_number` / `weapon_slot_count` / `beam_generator_lv` を省略した場合、それぞれ既定値
> (`""` / `""` / `1` / `0`) が使われる（Issue #383）。

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

## ダメージ・命中率シミュレーション API（Issue #381）

`POST /api/admin/simulate-combat` は、機体スペック・武器・パイロットステータスを入力として、
実戦（`backend/app/engine/combat.py`）と同一の計算式で命中率・クリティカル率・ダメージを算出する。

### 計算の実装

`backend/app/engine/combat_preview.py` に `BattleSimulator` インスタンス状態に依存しない純粋関数として実装。
シグモイドダメージ式（[`docs/features/sigmoid-damage-calculation.md`](./sigmoid-damage-calculation.md)）や
`calculator.py` のパイロットステータス補正関数をそのまま再利用しており、実戦の挙動と乖離しない。

### 乱数を含む計算への対応

命中判定・クリティカル判定・ダメージ分散は本来 `random` モジュールに依存するため、同一入力でも結果が毎回変わる。
これに対応するため、本APIは2種類の値を返す:

- **決定論値**（常に返す）: 乱数を振らず、命中率(%)・クリティカル率(%)・理論ダメージ値を返す
- **モンテカルロ試行**（`trials` 指定時のみ）: サーバー側で実際に乱数判定をN回（最大5000回）試行し、
  実測命中率・平均/最小/最大ダメージ・クリティカル発生率・完全回避発生率（LUKステータス由来）を集計して返す

### リクエスト例

```json
POST /api/admin/simulate-combat
X-API-Key: <key>
Content-Type: application/json

{
  "attacker_spec": { "...": "MasterMobileSuitSpec と同形" },
  "attacker_weapon_id": "beam_rifle",
  "attacker_pilot": { "sht": 50, "mel": 0, "intel": 0, "ref": 0, "tou": 0, "luk": 0 },
  "defender_spec": { "...": "MasterMobileSuitSpec と同形" },
  "defender_pilot": { "sht": 0, "mel": 0, "intel": 0, "ref": 0, "tou": 20, "luk": 0 },
  "distance": 320,
  "attack_sector": "FRONT_SIDE",
  "trials": 1000
}
```

### レスポンス例

```json
{
  "hit_chance": 65.0,
  "crit_chance": 5.0,
  "base_damage": 116,
  "crit_damage": 180,
  "resistance_applied_damage": 116,
  "monte_carlo": {
    "trials": 1000,
    "actual_hit_rate": 66.2,
    "actual_crit_rate": 5.4,
    "avg_damage": 119.1,
    "min_damage": 104,
    "max_damage": 197,
    "perfect_evade_rate": 0.0
  }
}
```

`trials` を省略した場合は `monte_carlo` が `null` になり、決定論値のみが返る。

### バリデーション

| ケース | ステータスコード |
|---|---|
| `attacker_weapon_id` が `attacker_spec.weapons` に存在しない | `422` |
| `attack_sector` が `FRONT`/`FRONT_SIDE`/`REAR_SIDE`/`REAR` 以外 | `422` |
| `trials` が範囲外（1〜5000）| `422` |

### 管理画面UI

マスター機体編集画面の「ダメージ・命中率シミュレーション」パネル（`CombatSimulationPanel`）から利用できる。
攻撃側は選択中の機体、防御側はマスター機体一覧から選択する。距離・攻撃セクタ・双方のパイロットステータスを
調整しながら「理論値を計算」（決定論値のみ）・「N回試行」（モンテカルロ統計付き）を実行できる。

---

## データ永続化

### DB スキーマ (`master_mobile_suits`)

```sql
CREATE TABLE master_mobile_suits (
    id                 TEXT PRIMARY KEY,       -- スネークケース (例: rx_78_2)
    name               TEXT NOT NULL,
    name_ja            TEXT NOT NULL DEFAULT '',  -- 日本語表示名（Issue #383）
    model_number       TEXT NOT NULL DEFAULT '',  -- 型番 例: RGM-79（Issue #383）
    price              INTEGER NOT NULL,
    faction            TEXT NOT NULL DEFAULT '',
    description        TEXT NOT NULL,
    weapon_slot_count  INTEGER NOT NULL DEFAULT 1,  -- 武器スロット数、1以上（Issue #383）
    beam_generator_lv  INTEGER NOT NULL DEFAULT 0,  -- ビームジェネレータLv、0以上（Issue #383）
    specs              JSONB NOT NULL,         -- MasterMobileSuitSpec の全フィールド
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`Weapon`（`specs.weapons` 内の各要素）には `required_beam_generator_lv`（装備に必要なビームジェネレータLv、`type == "BEAM"` の武器のみ有効、既定値0）が追加されている（Issue #383）。

### マイグレーション

```bash
cd backend
alembic upgrade head
```

### シードデータ投入

初回デプロイ後、`data/master/mobile_suits.json` のデータを DB へ投入する:

```bash
# 既存レコードは上書きしない（管理画面変更を保護）
python scripts/seed/seed_master_data.py

# --force で既存レコードも上書き（開発環境リセット用）
python scripts/seed/seed_master_data.py --force
```

### キャッシュ

- マスターデータは `MASTER_DATA_CACHE_TTL_SEC` 秒（デフォルト: 60秒）の TTL キャッシュで保持される
- `GET /api/admin/reload-master` でキャッシュをクリアして最新 DB データを返す
- テスト環境では `MASTER_DATA_CACHE_TTL_SEC=0` でキャッシュを無効化できる

---

## Frontend（`admin-tool/` — 独立アプリ）

マスタデータ管理UIは `frontend/` から分離され、リポジトリ直下の独立した Next.js アプリ `admin-tool/`（ポート3100）として提供される。
ゲームバランス調整用のローカル専用ツールであり、アプリ本体のユーザー向け認証（Clerk）とは無関係。

### ルーティング

`/mobile-suits`（`admin-tool/` は全体が管理画面のため `/admin` プレフィックスなし）

### アクセス制御

`admin-tool/` に認証機構は無い（localhost 専用ツールとして運用）。データ保護は下記の `X-API-Key` のみに依存する。

### 環境変数

| 変数名 | 説明 |
|---|---|
| `NEXT_PUBLIC_API_URL` | バックエンド API の URL（デフォルト: `http://127.0.0.1:8000`） |
| `NEXT_PUBLIC_ADMIN_API_KEY` | 管理者 API キー（admin-tool からバックエンドへの X-API-Key） |

#### `NEXT_PUBLIC_ADMIN_API_KEY` の設定方法

`admin-tool` が `X-API-Key` ヘッダーに付与する値は、バックエンドの `ADMIN_API_KEY` 環境変数と一致させる必要がある。

`admin-tool/.env.local` に記載する（`.gitignore` 対象なのでコミットしない）：

```env
NEXT_PUBLIC_ADMIN_API_KEY=your_secret_key_here
```

バックエンド側にも同じ値を設定する：

```env
# backend/.env
ADMIN_API_KEY=your_secret_key_here
```

`your_secret_key_here` は任意の安全なランダム文字列を使用する（例: `openssl rand -hex 32` で生成）。

> [!NOTE]
> 現状は「まずローカル開発環境で完結するツール」として構築されている。本番公開する場合はアクセス制御方式を別途検討すること。

### 起動方法

```bash
cd admin-tool && npm run dev   # http://localhost:3100
# もしくはリポジトリルートから ./scripts/dev.sh で frontend/backend と同時起動
```

### コンポーネント構成

```
admin-tool/src/
├── app/
│   ├── mobile-suits/
│   │   └── page.tsx               # 管理画面エントリーポイント
│   └── weapons/
│       └── page.tsx
├── components/
│   ├── admin/
│   │   ├── MobileSuitTable.tsx    # 機体一覧テーブル（ソート・フィルタ付き）
│   │   ├── MobileSuitEditForm.tsx # 全パラメータ編集フォーム（Zod バリデーション）
│   │   ├── MobileSuitRadarChart.tsx # バランス比較レーダーチャート（recharts）
│   │   ├── CombatSimulationPanel.tsx # ダメージ・命中率シミュレーションパネル（Issue #381）
│   │   └── CloneDialog.tsx        # Clone & Edit ダイアログ
│   └── ui/                        # SciFiPanel / SciFiButton / SciFiHeading（frontendから移植）
└── hooks/
    ├── useAdminMobileSuits.ts     # SWR を用いた CRUD フック
    └── useCombatSimulation.ts     # シミュレーションAPI呼び出しフック（Issue #381）
```

### 機能詳細

#### 機体一覧テーブル (`MobileSuitTable`)

- ID・型番・名前・勢力・価格・HP・装甲・機動性を表示（型番列は Issue #383 で追加）
- 各列ヘッダークリックでソート（昇順/降順）
- テキストフィルタ（name / name_ja / model_number / id / faction で絞り込み、Issue #383 で name_ja / model_number を追加）
- 編集中の機体は行がハイライト表示

#### 詳細編集フォーム (`MobileSuitEditForm`)

- `react-hook-form` + `zod` によるバリデーション
- 全スペック・武装パラメータを編集可能（型番・日本語名・武器スロット数・ビームジェネレータLvを含む、Issue #383）
- フィールド横にインラインエラーメッセージ表示
- 武装リストの動的追加・削除
- 武器数が武器スロット数を超える場合、およびBEAM武器の要求ビームジェネレータLvが機体のビームジェネレータLvを超える場合はクライアント側 (`zod.superRefine`) でもエラー表示（Issue #383）

#### バランス比較チャート (`MobileSuitRadarChart`)

- `recharts` の `RadarChart` を使用
- 5軸: HP・装甲・機動性・射撃適性・格闘適性
- 各軸は全機体最大値を 100 として正規化
- 選択機体（橙）と全機体平均（シアン点線）の2系列表示

#### Clone & Edit (`CloneDialog`)

- 選択中の機体をコピーして新しい ID を付けて新規追加
- ID バリデーション（スネークケース英数字のみ）

#### ダメージ・命中率シミュレーション (`CombatSimulationPanel`, Issue #381)

- 攻撃側（選択中の機体・武装・パイロットステータス）と防御側（機体一覧から選択・パイロットステータス）を入力
- 距離スライダー・攻撃セクタ選択で条件を調整可能
- 「理論値を計算」で決定論値（命中率・クリティカル率・非クリ/クリダメージ）を表示
- 「N回試行」でモンテカルロ試行を実行し、実測統計値を理論値と並べて表示
- バックエンドAPI: `POST /api/admin/simulate-combat`（詳細は本ドキュメント上部「ダメージ・命中率シミュレーション API」セクション参照）

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
- DB 永続化確認
- `name_ja` / `model_number` / `weapon_slot_count` / `beam_generator_lv` の保存・既定値（Issue #383）
- 武器数が `weapon_slot_count` を超える場合の 422（新規追加・更新の両方）（Issue #383）
- BEAM武器の `required_beam_generator_lv` が `beam_generator_lv` を超える場合の 422（Issue #383）

```bash
cd backend
NEON_DATABASE_URL="sqlite:///test.db" ADMIN_API_KEY="test_key" python -m pytest tests/unit/test_admin_combat_simulation.py -v
```

テスト内容 (`tests/unit/test_admin_combat_simulation.py`, Issue #381):
- 認証チェック（キーなし / 不正キー）
- 決定論値の計算式検証（命中率・クリティカル率・クリダメージ倍率）
- パイロットステータス（SHT/INT/TOU）が命中率・クリティカル率に反映されること
- 格闘武器は耐性計算をスキップする現行仕様との整合性
- モンテカルロ試行の実測値が理論値に近似すること（大数の法則）
- 武器ID不正・攻撃セクタ不正・試行回数範囲外の 422 エラー

### admin-tool

```bash
cd admin-tool
npx vitest run tests/unit/
```

テスト内容 (`tests/unit/mobileSuitEditFormValidation.test.ts`):
- `weaponSchema`: id 形式 / 必須フィールド / accuracy 範囲 / type enum など
- `masterMobileSuitSchema`: id 形式 / 価格 / スペック値範囲 / weapons 必須 1 件以上

---

## 関連ファイル

- `backend/app/routers/admin.py` — CRUD API ルーター
- `backend/app/services/mobile_suit_service.py` — CRUD ロジック
- `backend/app/core/gamedata.py` — DB 読み書き・TTL キャッシュ
- `backend/app/core/auth.py` — `verify_admin_api_key` 依存関数
- `backend/app/models/models.py` — `MasterMobileSuit` (テーブルモデル) / `MasterMobileSuitEntry` / `MasterMobileSuitCreate` / `MasterMobileSuitUpdate`
- `backend/data/master/mobile_suits.json` — シードデータ（Git 管理継続）
- `backend/scripts/seed/seed_master_data.py` — シードスクリプト
- `backend/alembic/versions/r1s2t3u4v5w6_add_master_mobile_suits_and_weapons_tables.py` — マイグレーション
- `backend/alembic/versions/u4v5w6x7y8z9_add_model_number_name_ja_slots_beam_lv.py` — 型番/日本語名/武器スロット数/ビームジェネレータLv追加マイグレーション（Issue #383）
- `admin-tool/src/app/mobile-suits/page.tsx` — 管理画面（独立アプリ、ポート3100）
- `admin-tool/src/hooks/useAdminMobileSuits.ts` — CRUD フック
- `backend/app/engine/combat_preview.py` — 1対1 攻撃シミュレーション計算ロジック（決定論値・モンテカルロ）（Issue #381）
- `backend/app/services/combat_simulation_service.py` — シミュレーションサービス（Issue #381）
- `backend/tests/unit/test_admin_combat_simulation.py` — シミュレーションAPIテスト（Issue #381）
- `admin-tool/src/components/admin/CombatSimulationPanel.tsx` — シミュレーションパネルUI（Issue #381）
- `admin-tool/src/hooks/useCombatSimulation.ts` — シミュレーションAPI呼び出しフック（Issue #381）
- `scripts/dev-admin.sh` — admin-tool 起動スクリプト


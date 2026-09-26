# エースパイロット マスターデータ管理 — DBテーブル化と管理者専用エディタ（Issue #442）

## 概要

エースパイロット（赤い彗星・青き巨星・紫豚・白い悪魔・ハマーンの影）の雛形定義を、
`backend/app/core/npc_data.py` のハードコード（`ACE_PILOTS`）から `ace_pilots` テーブルへ移行した。
`master_mobile_suits` / `master_weapons` と同様に admin-tool から一覧・編集・追加・削除でき、
バランス調整や新規エースの追加がコード修正・デプロイなしで完結する。

> [!NOTE]
> 本機能はエースの**雛形（マスター）**を扱う。マッチング時にこの雛形から `is_ace=True` の `MobileSuit` が
> 都度生成される。永続化された NPC 個体（`pilots` / `mobile_suits` の `is_npc=True` レコード）の管理は
> [admin-npcs.md](./admin-npcs.md)（Issue #441）を参照。

`PERSONALITY_TYPES` / `BATTLE_CHATTER` / `NPC_PILOT_*_NAMES` は単純な定数のため `npc_data.py` に残している。

---

## データ永続化

### DB スキーマ (`ace_pilots`)

| カラム | 型 | 説明 |
|---|---|---|
| `id` | String (PK) | スネークケースID（例: `ace_char_aznable`） |
| `name` | String | 二つ名（例: `赤い彗星`） |
| `pilot_name` | String | パイロット名（例: `Char Aznable`）。NPC管理画面のエース判定にも使用 |
| `description` | String | 説明文 |
| `personality` | String | `AGGRESSIVE` / `CAUTIOUS` / `SNIPER` |
| `mobile_suit` | JSONB | 搭乗機体スペック（`AcePilotMobileSuitSpec`） |
| `bounty_exp` | Integer | 撃破時のボーナス経験値 |
| `bounty_credits` | Integer | 撃破時のボーナスクレジット |
| `stats` | JSONB | パイロットステータス（`sht` / `mel` / `intel` / `ref` / `tou` / `luk`） |
| `skills` | JSONB | スキルID→レベル（例: `{"flanking": 3}`） |
| `created_at` / `updated_at` | TIMESTAMP | 作成・更新日時 |

`mobile_suit` JSON の構造（`AcePilotMobileSuitSpec`）:

| キー | 説明 |
|---|---|
| `name` | 機体名 |
| `max_hp` / `armor` / `mobility` / `sensor_range` | 基本スペック |
| `beam_resistance` / `physical_resistance` | 耐性（0〜1） |
| `max_en` / `en_recovery` | EN 最大値・回復量 |
| `weapons` | 武装リスト（`Weapon`、最低1件） |
| `tactics` | 戦術設定（`priority` / `range`） |
| `missing_parts` | 欠損部位（任意。部位 HP/装甲 `parts` は `max_hp`/`armor` から自動生成） |

`MasterMobileSuitSpec` にある適性・ボーナス系（`melee_aptitude` 等）はエース機体では持たない。

### マイグレーション

`backend/alembic/versions/e9f0a1b2c3d4_add_ace_pilots_table.py` でテーブルを作成し、移行時点の
`ACE_PILOTS` 5件を data migration として投入する。

- データはマイグレーション内にリテラルで複製しており、アプリコードを import しない
  （将来アプリ側が変わっても過去のマイグレーションの再現性を保つため）
- `weapons` は `Weapon` の既定値と異なる項目のみ保存している。読み出し時に `Weapon(**w)` で既定値が補完されるため、
  移行前（`Weapon(...)` をコードで直書きしていた頃）と挙動は同一
- 管理 API（作成・更新）で保存する武器も同じ形式（`Weapon.model_dump(exclude_defaults=True)`）に揃えており、
  移行データと管理画面で保存したデータの形式が混在しない

```bash
cd backend
alembic upgrade head
```

### シードデータ投入

開発環境向けに `backend/data/master/ace_pilots.json` を用意し、`seed_master_data.py` の投入対象に追加した
（テストの `conftest.py` もこのファイルからシードする）。

```bash
# 既存レコードは上書きしない（管理画面変更を保護）
python scripts/seed/seed_master_data.py

# --force で既存レコードも上書き（開発環境リセット用）
python scripts/seed/seed_master_data.py --force
```

### キャッシュ

エースはエンジン層（`simulation.py`、セッションを持たない）からユニットごとに参照されるため、機体・武器マスターと同じ
TTL キャッシュ方式で `gamedata.py` から提供する。

| 関数 | 説明 |
|---|---|
| `gamedata.get_ace_pilots()` | 全件を TTL キャッシュ経由で返す（`mobile_suit.weapons` は `Weapon` インスタンス） |
| `gamedata.get_ace_pilot_by_id(ace_id)` | ID で1件取得。見つからない場合は `None` |
| `gamedata.invalidate_ace_pilots_cache()` | キャッシュ無効化。管理 API の作成・更新・削除時に呼ばれる |

- TTL は機体・武器と同じ `MASTER_DATA_CACHE_TTL_SEC`（デフォルト60秒）だが、有効期限は独立して管理する
- `POST /api/admin/reload-master` でもエースのキャッシュがクリアされ、レスポンスに `ace_pilots` 件数が含まれる
- 管理画面での変更は次回マッチング（エース出現判定）から反映される

---

## ゲームロジックの参照元

| 箇所 | 用途 |
|---|---|
| `MatchingService._create_ace_pilot()` | `get_ace_pilots()` からランダムに1体選び `MobileSuit` を生成。マスターが空なら `None` を返し、エースは出現しない |
| `main.py::_resolve_npc_pilot_stats()` | `is_ace` 機体の `ace_id` から `stats` を解決 |
| `simulation.py::_resolve_flanking_skill_level()` | `is_ace` 機体の `ace_id` から `skills.flanking` を解決 |
| `PilotService.get_ace_pilot_names()` / `is_ace_pilot()` | NPC 管理画面のエース判定（`pilot_name` の名前一致）。import 時ではなく呼び出し毎にキャッシュから取得する |

生成済みのエース機体は `ace_id` 文字列で参照するのみ（FK なし）。マスターから削除・ID変更された場合、
`get_ace_pilot_by_id()` が `None` を返し、以下のフォールバックで動作する:

- パイロットステータス: `personality` から自動解決（`simulation.py::_personality_pilot_stats()`）
- フランキング: `AGGRESSIVE` は Lv.1、それ以外は Lv.0

`skills` には `SKILL_MASTER_DATA` の任意のスキルを保存できるが、NPC 戦闘で現在参照されるのは `flanking` のみ。

---

## API エンドポイント

すべてのエンドポイントは `X-API-Key` ヘッダー（環境変数 `ADMIN_API_KEY`）による認証が必要。

| メソッド | パス | 説明 |
|---|---|---|
| `GET` | `/api/admin/ace-pilots` | 全エース一覧 |
| `POST` | `/api/admin/ace-pilots` | 新規追加 |
| `PUT` | `/api/admin/ace-pilots/{ace_id}` | 部分更新（指定したフィールドのみ） |
| `DELETE` | `/api/admin/ace-pilots/{ace_id}` | 削除 |

### バリデーション

| 条件 | ステータス |
|---|---|
| `id` がスネークケース英数字（`[a-z0-9_]+`）でない | 422 |
| `personality` が `PERSONALITY_TYPES` 以外 | 422 |
| `mobile_suit.weapons` が0件 | 422 |
| `mobile_suit.missing_parts` に未知の部位名 | 422 |
| `skills` に未知のスキルID、またはレベルが 0〜`max_level` の範囲外 | 422 |
| `id` が重複（POST） | 409 |
| 対象が存在しない（PUT / DELETE） | 404 |

### リクエスト例（POST）

```json
{
  "id": "ace_test_pilot",
  "name": "テストの鬼",
  "pilot_name": "Test Pilot",
  "description": "テスト用エース",
  "personality": "SNIPER",
  "mobile_suit": {
    "name": "Test Gelgoog",
    "max_hp": 1250, "armor": 85, "mobility": 2.1, "sensor_range": 750.0,
    "beam_resistance": 0.2, "physical_resistance": 0.1,
    "max_en": 1800, "en_recovery": 180,
    "weapons": [
      { "id": "ace_test_beam_rifle", "name": "Test Beam Rifle", "power": 300, "range": 650,
        "accuracy": 88, "type": "BEAM", "optimal_range": 420.0, "decay_rate": 0.05, "en_cost": 90 }
    ],
    "tactics": { "priority": "STRONGEST", "range": "RANGED" }
  },
  "bounty_exp": 600,
  "bounty_credits": 1500,
  "stats": { "sht": 14, "mel": 7, "intel": 12, "ref": 11, "tou": 8, "luk": 9 },
  "skills": { "flanking": 1 }
}
```

---

## フロントエンド（`admin-tool/`）

### ルーティング

`/ace-pilots`（トップページに「エースパイロット管理」リンクを追加）

### 機能一覧

- エース一覧テーブル: ID・二つ名・パイロット名（機体名）・性格・HP・機動性・賞金を表示。列ヘッダーでソート、テキストフィルタ
- 編集フォーム: 入力項目が多いため「基本情報 / 機体 / 武装 / パイロット」のタブに分割
  - バリデーションエラーを含むタブには `!` を表示し、保存時にエラーのある最初のタブへ自動で切り替える
  - 武装フォームで扱わない項目（`weapon_type` / `cooldown_sec` / `fire_arc_deg` / `aim_distribution` 等）は、
    同じ武器IDの既存値を引き継いで送信する（編集で既定値に巻き戻らないようにするため）
  - スキルは `SKILL_MASTER_DATA` と同じ選択肢から追加する（重複・レベル上限をクライアント側でも検証）
- 新規追加・削除（確認ダイアログ付き）。SWR による楽観的更新

### コンポーネント構成

```
admin-tool/src/
├── app/
│   └── ace-pilots/
│       └── page.tsx               # エース管理画面エントリーポイント
├── components/
│   └── admin/
│       ├── AcePilotTable.tsx      # 一覧テーブル（ソート・フィルタ付き）
│       └── AcePilotEditForm.tsx   # タブ分割の編集フォーム・zod スキーマ・送信値変換
├── hooks/
│   └── useAdminAcePilots.ts       # 一覧取得・作成・更新・削除フック（SWR + 楽観的更新）
└── types/
    └── admin.ts                   # AcePilot / AcePilotMobileSuitSpec / AcePilotCreate / AcePilotUpdate
```

`AcePilotEditForm` は `MobileSuitEditForm` と同じく `"use no memo"` を付与している（Issue #388 と同じ理由）。
武器の zod スキーマは `MobileSuitEditForm` の `weaponSchema` を再利用している。

環境変数・起動方法は [admin-mobile-suits.md](./admin-mobile-suits.md) の「Frontend」セクションと共通。

---

## 関連ファイル

- `backend/app/models/models.py` — `AcePilot`（テーブル）/ `AcePilotMobileSuitSpec` / `AcePilotEntry` / `AcePilotCreate` / `AcePilotUpdate`
- `backend/app/core/gamedata.py` — `get_ace_pilots()` / `get_ace_pilot_by_id()` / `invalidate_ace_pilots_cache()`
- `backend/app/services/ace_pilot_service.py` — CRUD・バリデーション
- `backend/app/routers/admin.py` — `ace_pilot_router`
- `backend/app/services/matching_service.py` — エース機体の生成
- `backend/app/services/pilot_service.py` — `get_ace_pilot_names()` / `is_ace_pilot()`
- `backend/main.py` — `_resolve_npc_pilot_stats()`・ルーター登録
- `backend/app/engine/simulation.py` — `_resolve_flanking_skill_level()`
- `backend/alembic/versions/e9f0a1b2c3d4_add_ace_pilots_table.py` — テーブル作成・既存5体の移行
- `backend/data/master/ace_pilots.json` — 開発用シードデータ
- `backend/scripts/seed/seed_master_data.py` — シードスクリプト
- `backend/scripts/verify/verify_ace_pilots.py` — エースデータ検証スクリプト（インメモリDBにシードして検証）
- `admin-tool/src/app/ace-pilots/page.tsx` ほか上記フロントエンドファイル

---

## テスト

### バックエンド

```bash
cd backend
python -m pytest tests/unit/test_admin_ace_pilots.py --tb=short
```

`tests/unit/test_admin_ace_pilots.py`:
- 認証チェック
- 一覧: 移行済み5体が返ること、JSON 列で省略した武器の既定値がレスポンスで補完されること
- 作成・更新・削除: 正常系、409 / 404 / 422（ID形式・性格・スキル・武器0件・欠損部位）
- 管理 API での変更がゲームロジック側のキャッシュ（`get_ace_pilot_by_id()`）に即時反映されること
- 削除済みエースの生成済み機体が personality ベースのフォールバックで動作すること
- マスターが空の場合 `_create_ace_pilot()` が `None` を返すこと
- NPC 一覧の `is_ace` 判定がマスターの `pilot_name` に追従すること

既存の `test_npc_personality_and_ace.py` / `test_phase_e35_flanking.py` は、`ACE_PILOTS` の代わりに
`get_ace_pilots()`（`conftest.py` が `ace_pilots.json` からシード）を参照するよう変更した。

### admin-tool

```bash
cd admin-tool
npx vitest run tests/unit/acePilotEditFormValidation.test.ts
```

`acePilotSchema` のバリデーション（ID形式・武器0件・耐性範囲・スキル上限/重複）と、
`toAcePilotPayload()` の変換（skills 配列→辞書、フォーム外の武器項目の引き継ぎ）を検証する。

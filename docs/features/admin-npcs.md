# NPCデータ管理画面 — 管理者専用エディタ（Issue #441）

## パイロット名について（Issue #444）

通常NPC（非エース）の `Pilot.name` は `backend/app/core/npc_data.py` の `generate_npc_pilot_name()`
（`NPC_PILOT_FIRST_NAMES` × `NPC_PILOT_LAST_NAMES` からランダムに1件ずつ選び `"名 姓"` を生成、400通り）
で採番される。`MatchingService._create_npc_mobile_suit()` が生成する `MobileSuit.pilot_name` にこの値を
設定しており、NPCパイロット作成時（`create_room_matches()` 内の
`pilot_name = npc_suit.pilot_name or npc_suit.name`）にそのまま使われる。

以前は `MobileSuit.pilot_name` が未設定のままだったため、上記フォールバックにより機体名
（例: `"Zaku II (NPC)"`）がパイロット名として保存されてしまっていた。既存データはマイグレーション
`backend/alembic/versions/x7y8z9a0b1c2_backfill_npc_pilot_human_names.py` で一括バックフィル済み
（対象は `pilots.name` が `"... (NPC)"` 形式の機体名パターンに一致する行のみ。エース由来NPCや、
既に手動で人名へ修正済みの行を誤って上書きしないための絞り込み）。バックフィルは `pilots.name` だけでなく、
同じ `user_id` を持つ `mobile_suits.pilot_name` にも同一の人名を書き込む。`mobile_suits.pilot_name` は
バトルログ表示（`battle_utils.py` の `f"[{pilot_name}]の{actor.name}"`）やNPC再利用時のログ
（`MatchingService.select_npcs_for_room` 経由の再利用）でも参照されるため、`pilots.name` のみ更新すると
これらの表示が機体名のまま残ってしまう。

エースNPCのパイロット名は引き続き `npc_data.py` の `ACE_PILOTS[*]["pilot_name"]`（例: `"Char Aznable"`）
由来で、本セクションの対象外。

## 概要

NPC（`Pilot.is_npc=True`）を、通常ユーザと同じ `pilots`/`mobile_suits` テーブルを共用したまま、
admin-tool から一覧・閲覧・編集できる管理画面。#171（NPC自律成長AIロジック）が実装されるまでの
間の暫定運用、および実装後の挙動確認・チューニング用途を想定している。

> [!NOTE]
> `npc_data.py` の `ACE_PILOTS`（エースパイロットの静的マスタデータ）自体の編集は本Issueのスコープ外。
> エースパイロットの `MobileSuit` は戦闘マッチング時に `user_id=None` の使い捨てレコードとして都度生成され
> `Pilot` テーブルには永続化されないため、`ACE_PILOTS` 由来かどうかは `Pilot.name` と
> `ACE_PILOTS[*].pilot_name` の一致による best-effort 判定（`PilotService.is_ace_pilot`）で識別している。
> 恒久的な紐付け（例: `Pilot` にエースIDを持たせる等）が必要になった場合は別Issueで対応する。

---

## Backend API

すべてのエンドポイントは `X-API-Key` ヘッダー（環境変数 `ADMIN_API_KEY`）による認証が必要。

### エンドポイント一覧

| メソッド | パス | 説明 |
|---|---|---|
| `GET` | `/api/admin/npcs` | NPCパイロット一覧取得（性格/レベル範囲/エースで絞り込み可） |
| `GET` | `/api/admin/npcs/{pilot_id}` | NPCパイロット詳細取得（所有機体一覧付き） |
| `PUT` | `/api/admin/npcs/{pilot_id}` | NPCパイロットのステータス更新 |
| `PUT` | `/api/admin/npcs/{pilot_id}/mobile-suits/{ms_id}` | NPC所有機体のステータス更新 |

### GET /api/admin/npcs

クエリパラメータ（すべて省略可、AND条件で絞り込み）:

| パラメータ | 型 | 説明 |
|---|---|---|
| `personality` | string | `AGGRESSIVE` / `CAUTIOUS` / `SNIPER` |
| `min_level` | int | レベル下限（この値以上） |
| `max_level` | int | レベル上限（この値以下） |
| `ace_only` | bool | `true` でエース由来NPCのみ、`false` で通常NPCのみ |

レスポンスは `NpcPilotEntry` の配列。`mobile_suit_count` は `MobileSuit.user_id == Pilot.user_id` で
紐づく所有機体数。

### GET /api/admin/npcs/{pilot_id}

`NpcPilotDetail`（`NpcPilotEntry` に `mobile_suits: NpcMobileSuitEntry[]` を追加したもの）を返す。
`is_npc=False` のパイロット、または存在しない `pilot_id` を指定した場合は `404`。

### PUT /api/admin/npcs/{pilot_id}

`NpcPilotUpdate`（`npc_personality` / `level` / `exp` / `credits` / `skill_points` / `status_points` /
`sht` / `mel` / `intel` / `ref` / `tou` / `luk` / `awq`、すべて省略可）を受け取り、指定フィールドのみ更新する。
更新後の `NpcPilotDetail` を返す。存在しない場合は `404`。

### PUT /api/admin/npcs/{pilot_id}/mobile-suits/{ms_id}

指定したNPCが所有する機体（`MobileSuit`）のステータスを更新する。リクエストボディは既存の
`MobileSuitUpdate`（`app/models/models.py`）をそのまま流用しており、`name` / `max_hp` / `armor` /
`mobility` / `tactics` / 各種適性・補正値などを部分更新できる。

- `ms_id` が `pilot_id` の所有機体でない場合は `404` を返す（他NPCの機体を誤って編集できないようにするため）
- 更新ロジックは `MobileSuitService.update_mobile_suit()`（プレイヤー機体編集用の既存メソッド）をそのまま再利用

### ステータスコード

| コード | 意味 |
|---|---|
| `200` | 成功 |
| `401` | APIキー不正 |
| `404` | 対象NPC / 所有機体が見つからない |
| `422` | バリデーションエラー |

---

## データモデル

### `Pilot`（既存テーブル、新規テーブル追加なし）

NPCは `is_npc=True` の `Pilot` レコードとして永続化される。`user_id` は `npc-{uuid}` 形式の合成ID。
本Issueで新たに管理画面から編集可能になったフィールド: `npc_personality` / `level` / `exp` / `credits` /
`skill_points` / `status_points` / `sht` / `mel` / `intel` / `ref` / `tou` / `luk` / `awq`。

### `MobileSuit`（既存テーブル）

NPCの所有機体は `MobileSuit.user_id == Pilot.user_id` で紐づく。エース機体は `is_ace=True` /
`ace_id` / `pilot_name` / `bounty_exp` / `bounty_credits` を持つが、前述の通りエース機体は
`user_id=None` の使い捨てレコードとして生成されるため、通常は管理画面のNPC一覧・詳細には現れない
（`select_npcs_for_room()` で永続化NPCとして再利用されたエース以外）。

### `app/services/pilot_service.py` に追加した管理者用メソッド

- `PilotService.list_npc_pilots(session, personality, min_level, max_level, ace_only)` — 一覧取得（フィルタ対応）
- `PilotService.get_npc_pilot_by_id(session, pilot_id)` — idによる単体取得（`is_npc=True` のみ）
- `PilotService.get_npc_owned_mobile_suits(session, user_id)` — 所有機体一覧取得
- `PilotService.is_ace_pilot(pilot)` — `ACE_PILOTS` 由来かどうかの best-effort 判定（名前一致）
- `PilotService.update_npc_pilot(session, pilot_id, update_data)` — ステータス更新

既存の `PilotService` はインスタンスメソッド中心（`__init__(self, session)`）だが、上記の管理者用メソッドは
`MobileSuitService` の管理者用CRUDメソッドと同じ `@staticmethod` パターンに揃えている。

---

## Frontend（`admin-tool/`）

### ルーティング

`/npcs`

### コンポーネント構成

```
admin-tool/src/
├── app/
│   └── npcs/
│       └── page.tsx               # NPC管理画面エントリーポイント
├── components/
│   └── admin/
│       ├── NpcTable.tsx           # NPC一覧テーブル（ソート・フィルタ付き）
│       └── NpcEditForm.tsx        # ステータス編集フォーム + 所有機体インライン編集
└── hooks/
    └── useAdminNpcs.ts            # 一覧/詳細取得・更新フック（SWR）
```

### NPC一覧テーブル（`NpcTable`）

- 名前・性格・レベル・EXP・クレジット・所属機体数を表示
- 各列ヘッダークリックでソート（昇順/降順）
- 名前によるテキストフィルタ、性格タイプ・レベル範囲・エース/通常NPCによる絞り込み（サーバー側フィルタではなく
  クライアント側で `npcs` 全件から絞り込む。既存の `MobileSuitTable` と同じ設計）
- エース由来NPC（`is_ace=true`）は行内に `ACE` バッジを表示

### 詳細編集フォーム（`NpcEditForm`）

- `react-hook-form` + `zod` によるバリデーション（性格・レベル・EXP・クレジット・各種ポイント・SHT/MEL/INT/REF/TOU/LUK/AWQ）
- 所有機体一覧を下部に表示し、機体ごとに最大HP・装甲・機動性をインライン編集して個別に保存可能
  （`PUT /api/admin/npcs/{pilot_id}/mobile-suits/{ms_id}` を機体単位で呼び出す）

> [!NOTE]
> `NpcEditForm` は `MobileSuitEditForm` と同様、React Compiler の自動メモ化が `react-hook-form` の
> 非制御 `<input>` への `reset()` を阻害する問題（Issue #388）を避けるため、コンポーネント関数内に
> `"use no memo"` ディレクティブを付与している。

### env vars / 起動方法

`admin-mobile-suits.md` の「Frontend」セクションと共通（`NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_ADMIN_API_KEY`）。

---

## テスト

### Backend

```bash
cd backend
NEON_DATABASE_URL="sqlite:///test.db" ADMIN_API_KEY="test_admin_key_12345" python -m pytest tests/unit/test_admin_npcs.py -v
```

テスト内容 (`tests/unit/test_admin_npcs.py`):
- 認証チェック（キーなし / 不正キー）
- 一覧取得: `is_npc=False` のパイロットが含まれないこと、所有機体数の反映、性格/レベル範囲/`ace_only` フィルタ
- 詳細取得: 所有機体一覧の反映、404（存在しないid / `is_npc=False`）
- 更新: ステータス更新の反映、404（存在しないid）
- 所有機体更新: ステータス反映、他NPC所有機体を編集しようとした場合の404

---

## 関連ファイル

- `backend/app/routers/admin.py` — `npc_router`（NPC CRUD API）
- `backend/app/services/pilot_service.py` — NPC管理者用メソッド・`ACE_PILOT_NAMES`
- `backend/app/models/models.py` — `NpcPilotEntry` / `NpcPilotDetail` / `NpcPilotUpdate` / `NpcMobileSuitEntry`
- `backend/app/core/npc_data.py` — `ACE_PILOTS`（エース識別の名前一致元データ）
- `backend/main.py` — `app.include_router(admin.npc_router)`
- `backend/tests/unit/test_admin_npcs.py` — NPC管理APIテスト
- `admin-tool/src/app/npcs/page.tsx` — 管理画面
- `admin-tool/src/hooks/useAdminNpcs.ts` — 一覧/詳細取得・更新フック
- `admin-tool/src/components/admin/NpcTable.tsx` — NPC一覧テーブル
- `admin-tool/src/components/admin/NpcEditForm.tsx` — ステータス編集フォーム
- `admin-tool/src/types/admin.ts` — `NpcPilot` / `NpcPilotDetail` / `NpcPilotUpdate` / `NpcMobileSuit` 型定義
- `admin-tool/src/app/page.tsx` — トップナビへのリンク追加

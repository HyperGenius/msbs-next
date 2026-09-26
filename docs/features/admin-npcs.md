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

エースNPCのパイロット名は `ace_pilots` テーブルの `pilot_name`（例: `"Char Aznable"`）由来で、
本セクションの対象外（Issue #442 で `npc_data.py` の `ACE_PILOTS` から DB へ移行。[admin-ace-pilots.md](./admin-ace-pilots.md) 参照）。

## 概要

NPC（`Pilot.is_npc=True`）を、通常ユーザと同じ `pilots`/`mobile_suits` テーブルを共用したまま、
admin-tool から一覧・閲覧・編集できる管理画面。#171（NPC自律成長AIロジック）が実装されるまでの
間の暫定運用、および実装後の挙動確認・チューニング用途を想定している。

> [!NOTE]
> エースパイロットのマスターデータ自体の編集は本Issueのスコープ外で、`/ace-pilots` 画面で行う
> （Issue #442、[admin-ace-pilots.md](./admin-ace-pilots.md)）。
> エースパイロットの `MobileSuit` は戦闘マッチング時に `user_id=None` の使い捨てレコードとして都度生成され
> `Pilot` テーブルには永続化されないため、エース由来かどうかは `Pilot.name` と
> `ace_pilots.pilot_name` の一致による best-effort 判定（`PilotService.is_ace_pilot`）で識別している。
> 判定元の名前集合は `PilotService.get_ace_pilot_names()` が呼び出し毎に TTL キャッシュ経由で取得するため、
> マスターの `pilot_name` を変更・追加すると判定結果も追従する。
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
| `POST` | `/api/admin/npcs/{pilot_id}/mobile-suits` | 機体マスターから NPC に機体を追加（Issue #540） |
| `PUT` | `/api/admin/npcs/{pilot_id}/mobile-suits/{ms_id}` | NPC所有機体のスペック（武装含む）更新 |

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
`sht` / `mel` / `intel` / `ref` / `tou` / `luk` / `awq` / `active_mobile_suit_id`、すべて省略可）を受け取り、
指定フィールドのみ更新する。更新後の `NpcPilotDetail` を返す。存在しない場合は `404`。

`active_mobile_suit_id`（Issue #542）はそのパイロットの所有機（`user_id` が一致し `side='ENEMY'`）でなければ `422`。
所有機の判定条件はマッチングで出撃させる機体の条件と揃えている。

### POST /api/admin/npcs/{pilot_id}/mobile-suits（Issue #540）

リクエストボディ `NpcMobileSuitCreate`（`master_mobile_suit_id`）で指定した機体マスター（`master_mobile_suits`）の
`specs` をコピーし、NPC の所有機体として `mobile_suits` に作成する。作成した機体を `NpcMobileSuitEntry` で返す（`201`）。

| 項目 | 設定値 |
|---|---|
| `max_hp` / `armor` / `mobility` / `sensor_range` / 耐性 / 適性・補正 / `missing_parts` | 機体マスターの `specs` からコピー |
| `weapons` | 機体マスターの `specs.weapons`（既定値との差分で保存されていても `Weapon` として補完する） |
| `weapon_slot_count` | 機体マスターの `weapon_slot_count`（Issue #543） |
| `name` | `"{機体マスター名} (NPC)"`（マッチングで生成される NPC 機体の命名に合わせる） |
| `current_hp` | `max_hp` と同じ |
| `user_id` / `side` | NPC パイロットの `user_id` / `"ENEMY"` |
| `personality` / `pilot_name` | NPC パイロットの `npc_personality`（未設定なら `AGGRESSIVE`）/ `name` |
| `tactics` | `build_npc_tactics(personality)`（`npc_data.py`。マッチング時の NPC 機体生成と共通） |

NPC パイロットまたは機体マスターが存在しない場合は `404`。

NPC の出撃機体（`active_mobile_suit_id`）が未設定の場合は、作成した機体を出撃機体に設定する（Issue #542）。
設定済みの場合は変更しない。

### PUT /api/admin/npcs/{pilot_id}/mobile-suits/{ms_id}

指定したNPCが所有する機体（`MobileSuit`）を部分更新する。リクエストボディは NPC 専用の
`NpcMobileSuitUpdate`（`app/models/models.py`）で、以下を更新できる。

- 基本: `name` / `max_hp` / `armor` / `mobility` / `sensor_range` / `beam_resistance` / `physical_resistance` / `max_en` / `en_recovery`
- 適性・補正: `melee_aptitude` / `shooting_aptitude` / `accuracy_bonus` / `evasion_bonus` / `acceleration_bonus` / `turning_bonus`
- `tactics` / `missing_parts` / `weapons` / `weapon_slot_count`（Issue #543）

プレイヤー向けの `MobileSuitUpdate` は流用しない。`MobileSuitUpdate` に武装などを足すと、プレイヤーが
`PUT /api/mobile_suits/{ms_id}` で自機の武装を任意に書き換えられるようになるため。

- `ms_id` が `pilot_id` の所有機体でない場合は `404` を返す（他NPC・プレイヤーの機体を誤って編集できないようにするため）
- `weapons` を空にした場合、`missing_parts` に不正な部位名を含めた場合は `422`
- `tactics` の `priority` / `range` / `weapon_switch_policy` が許容値に無い場合は `422`（Issue #544。`validate_tactics()`）。
  許容値は `app/engine/constants.py` の `TACTICS_PRIORITIES` / `TACTICS_RANGES` / `WEAPON_SWITCH_POLICIES`。
  未設定のキーはエンジンの既定値で動くため検証しない。それ以外のキーも検証せず、そのまま保存する
- 武器の `aim_distribution` の部位名が `ALL_PART_NAMES` に無い、負の値がある、合計が 1.0 ±0.01 でない場合は `422`
  （Issue #544。Garage と共通の `validate_aim_distribution()`（`weapon_service.py`））。欠損部位に配分が残っていてもエラーにしない
- 武装の本数が武器スロット数を超える場合、同じ武器 ID の武装が2本以上ある場合は `422`（Issue #543）。
  `weapon_slot_count` だけを送った場合も、既存の武装の本数と比べる。
  バトル中の弾数・クールダウン（`weapon_states`）は武器 ID をキーに持つため、同じ ID の武器は状態を共有してしまう。
  ビームジェネレータLv の条件は NPC 機には適用しない。検証は `validate_npc_weapons()`（`mobile_suit_service.py`）
- `max_hp` を変更すると `current_hp` も新しい `max_hp` に揃える（バトル投入時に全快されるため実害はないが、表示の不整合を避ける）
- `max_hp` / `armor` / `missing_parts` のいずれかを変更すると `parts` を空にする（`normalize_parts()` が次回参照時に再生成する）
- 更新ロジックは `MobileSuitService.update_npc_mobile_suit()`

レスポンスの `NpcMobileSuitEntry` は、上記の編集対象項目すべてと `current_hp` / `personality` / `is_ace` /
`ace_id` / `pilot_name` / `bounty_exp` / `bounty_credits` を返す。
`weapon_slot_count` は `resolve_weapon_slot_count()` で解決した値を返す（未設定の機体は装備数と `MAX_WEAPON_SLOTS` の大きい方）。

### ステータスコード

| コード | 意味 |
|---|---|
| `200` | 成功 |
| `201` | 機体追加成功 |
| `401` | APIキー不正 |
| `404` | 対象NPC / 所有機体が見つからない |
| `422` | バリデーションエラー |

---

## データモデル

### `Pilot`（既存テーブル、新規テーブル追加なし）

NPCは `is_npc=True` の `Pilot` レコードとして永続化される。`user_id` は `npc-{uuid}` 形式の合成ID。
本Issueで新たに管理画面から編集可能になったフィールド: `npc_personality` / `level` / `exp` / `credits` /
`skill_points` / `status_points` / `sht` / `mel` / `intel` / `ref` / `tou` / `luk` / `awq`。

#### 出撃機体 `active_mobile_suit_id`（Issue #542）

NPC がマッチングでどの所有機に乗って出撃するかを保持する（nullable、`mobile_suits.id` への FK、`ON DELETE SET NULL`）。
プレイヤーは `battle_entries.mobile_suit_id` で出撃機体を指定するため NULL のまま。

以前の `MatchingService.select_npcs_for_room()` は所有機を `ORDER BY` なしで取得して先頭の1機を出撃させていたため、
複数機所有の NPC では出撃機体が不定だった（`mobile_suits` に作成日時カラムがなく、並び順で決定的に選ぶ手段もない）。
現在の選択ルールは以下の通り（所有機の一括取得による N+1 回避は維持）:

1. `active_mobile_suit_id` が所有機（`side='ENEMY'`）を指していれば、その機体で出撃する
2. NULL、または所有機を指していない場合は所有機から1機を選び、`active_mobile_suit_id` に保存してから出撃する（以降は同じ機体で出撃）
3. 所有機が0機の NPC は再利用対象にしない

マッチングで新規生成される NPC は、生成した機体がそのまま出撃機体に設定される。`pilots` → `mobile_suits` の FK は
`relationship()` を定義しておらず flush 時の INSERT 順序が保証されないため、機体・パイロットを flush した後に設定している
（`_fill_with_new_npcs()`。`battle_entries` の FK 違反を防いだ Issue #461 と同じ理由）。

マイグレーション `f0a1b2c3d4e5` で、所有機がちょうど1機の既存 NPC パイロットにその機体 ID をバックフィルしている。

### `MobileSuit`（既存テーブル）

NPCの所有機体は `MobileSuit.user_id == Pilot.user_id` で紐づく。エース機体は `is_ace=True` /
`ace_id` / `pilot_name` / `bounty_exp` / `bounty_credits` を持つが、前述の通りエース機体は
`user_id=None` の使い捨てレコードとして生成されるため、通常は管理画面のNPC一覧・詳細には現れない
（`select_npcs_for_room()` で永続化NPCとして再利用されたエース以外）。

#### 武器スロット数 `weapon_slot_count`（Issue #543）

`mobile_suits.weapon_slot_count`（nullable int）で機体ごとに武器スロット数を持つ。
NPC 機は機体名が `"{機体マスター名} (NPC)"` のため、プレイヤー機と同じ「機体名で機体マスターを引く」方法では解決できないため。

スロット数は `resolve_weapon_slot_count()`（`models.py`）で次の順に解決する。
`MobileSuitResponse.from_mobile_suit()` と `WeaponService` の装備時チェックもこの関数を使う。

1. `mobile_suits.weapon_slot_count`
2. 機体名で引いた機体マスターの `weapon_slot_count`
3. `max(装備数, MAX_WEAPON_SLOTS)`

| 機体 | `weapon_slot_count` |
|---|---|
| プレイヤー機 | NULL のまま（機体マスターから解決する。従来どおり） |
| 既存の NPC 機（`side = 'ENEMY'`） | マイグレーション `g1b2c3d4e5f6` で `max(装備数, 2)` をバックフィル |
| マッチングで新規生成する NPC 機 | `MAX_WEAPON_SLOTS`（武装は1〜2本） |
| 機体マスターから追加した NPC 機 | 機体マスターの値 |
| エース機 | 雛形（`ace_pilots.mobile_suit.weapon_slot_count`）の値。未設定なら `max(装備数, MAX_WEAPON_SLOTS)` |

### `app/services/pilot_service.py` に追加した管理者用メソッド

- `PilotService.list_npc_pilots(session, personality, min_level, max_level, ace_only)` — 一覧取得（フィルタ対応）
- `PilotService.get_npc_pilot_by_id(session, pilot_id)` — idによる単体取得（`is_npc=True` のみ）
- `PilotService.get_npc_owned_mobile_suits(session, user_id)` — 所有機体一覧取得
- `PilotService.is_ace_pilot(pilot)` — `ace_pilots` 由来かどうかの best-effort 判定（名前一致）
- `PilotService.update_npc_pilot(session, pilot_id, update_data)` — ステータス・出撃機体の更新（所有機でない出撃機体は `ValueError`）

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
│       ├── NpcTable.tsx               # NPC一覧テーブル（ソート・フィルタ付き）
│       ├── NpcEditForm.tsx            # ステータス編集フォーム + 所有機体一覧・機体追加
│       ├── NpcMobileSuitEditForm.tsx  # NPC機体の編集フォーム（機体 / 武装タブ）
│       ├── MobileSuitSpecFields.tsx   # エース機・NPC機で共通の機体スペック / 武装入力欄
│       ├── MasterMobileSuitSelect.tsx # 機体マスター選択プルダウン
│       └── MasterWeaponSelect.tsx     # 武器マスター選択プルダウン（Issue #543）
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
- 所有機体一覧を下部に表示する。機体ごとの「編集」で `NpcMobileSuitEditForm` を開き、個別に保存する
  （`PUT /api/admin/npcs/{pilot_id}/mobile-suits/{ms_id}` を機体単位で呼び出す）
- 一覧の下の「機体を追加」で機体マスターをプルダウンから選ぶと、`POST /api/admin/npcs/{pilot_id}/mobile-suits` で追加する
- 出撃機体には「出撃中」バッジを表示する。他の機体の「出撃機体にする」を押すと、確認なしで即時に
  `PUT /api/admin/npcs/{pilot_id}`（`active_mobile_suit_id`）を呼び出して切り替える（元に戻すのも同じ操作でできるため）。
  次回マッチングから反映される

### NPC機体編集フォーム（`NpcMobileSuitEditForm`、Issue #540）

- 「機体 / 武装」のタブに分割。バリデーションエラーを含むタブには `!` を表示し、保存時にエラーのある最初のタブへ切り替える
- 機体タブ: スペック・武器スロット数・戦術・欠損部位（エース用フォームと共通の `MobileSuitSpecSection`）と、NPC 機だけが持つ適性・補正
  - 戦術には武装持ち替えポリシー（`weapon_switch_policy`）を含む（Issue #544）。選択肢と表示ラベルは Garage の `TacticsSelector` と同じ。
    未設定の機体は `BALANCED`（`DEFAULT_WEAPON_SWITCH_POLICY`）として表示する
  - `tactics` のうちフォームで扱わないキーは、保存時に既存値とマージして残す（`mergeTactics()`）
- 武装タブ: 武器の追加・削除・編集（エース用フォームと共通の `WeaponListSection`）
  - 各武器の見出しは Garage と同じスロット名（右腕 / 左腕 / ラックN）で表示する（`weaponSlotLabel()`。Issue #543）
  - 武器マスターをプルダウンで選んで「追加」すると、武器マスターの `id` / `name` / スペックをコピーして末尾に追加する。
    同じ武器IDがすでにある場合は `{id}_2`、`{id}_3` … と接尾辞を付ける（`masterWeaponToWeapon()`。Issue #543）
  - 武装の本数がスロット数に達すると「+ 追加」と武器マスターからの追加を無効にする
  - 武装の本数がスロット数を超える場合（スロット数の欄）、武器IDが重複する場合（2本目以降の ID 欄）はフォームでエラーにする
    （`refineWeaponSlots()`）
  - 各武器の「狙う部位配分」で、部位ごと（頭部・胴体・右腕・左腕・右脚・左脚）の配分を % で編集する（Issue #544）。
    武器ごとに折りたたみ、既定では閉じておく。見出しに合計を表示し、100% ±1% を外れると赤くする。
    初期表示は武器の `aim_distribution`（未設定・空なら既定値）。「既定値に戻す」で `DEFAULT_AIM_DISTRIBUTION` に戻す。
    負値・合計のずれはフォームでエラーにする（`aimDistributionSchema`）。送信時は割合（0〜1）に直す
- 武装フォームで扱わない項目（`weapon_type` / `cooldown_sec` / `fire_arc_deg` 等）は、
  同じ武器IDの既存値・武器マスターから追加した武器の値を引き継いで送信する（`mergeWeaponSources()`）

`MobileSuitSpecSection` / `WeaponListSection` は `useFormContext()` で親フォームを参照するため、
`FormProvider` 配下に置き、機体スペックを `mobile_suit` キーの下に持つフォームで使う。

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
- 所有機体更新（Issue #540）: 武装・耐性・戦術・欠損部位を含む全項目の反映、`max_hp` 変更時の `current_hp`/`parts` 再計算、
  武装0件・不正な欠損部位の422、プレイヤー所有機の404
- 持ち替えポリシー・狙う部位配分（Issue #544）: 持ち替えポリシー・配分の保存、`tactics` の未知のキーが残ること、
  欠損部位に配分が残っていても保存できること、不正な戦術値・配分（部位名・負値・合計）の422
- 機体追加（Issue #540）: 機体マスターのスペック・武装のコピー、NPC パイロットの性格・名前の反映、404（機体マスター / NPC が存在しない）
- 武器スロット数（Issue #543）: 未設定機のフォールバック値、スロット数の更新、本数超過・スロット数だけの引き下げ・武器ID重複の422、
  ビームジェネレータLv 条件を適用しないこと、機体マスターからの追加時のスロット数コピー
- 出撃機体（Issue #542）: 所有機への切り替え、他パイロットの機体・存在しない機体の422、
  機体追加時に未設定なら追加機体が出撃機体になること・設定済みなら変わらないこと

マッチング時の出撃機体選択は `tests/unit/test_npc_persistence.py` でテストしている
（`active_mobile_suit_id` の機体で出撃すること、NULL / 他パイロットの機体 / `side='PLAYER'` の機体を指す場合に所有機が選ばれて保存されること、
所有機0機の NPC が選ばれないこと、新規生成 NPC の出撃機体設定）。

### admin-tool

```bash
cd admin-tool
npx vitest run tests/unit/npcMobileSuitEditFormValidation.test.ts
```

`npcMobileSuitSchema` のバリデーション、`toNpcMobileSuitFormValues()`（戦術未設定の補完）、
`toNpcMobileSuitPayload()`（フォーム外の武器項目の引き継ぎ）、`masterToSpecValues()`、`masterMobileSuitLabel()` を検証する。
Issue #543 で、武器スロット数・武器ID重複のバリデーション、`uniqueWeaponId()`、`weaponSlotLabel()`、
武器マスターから追加した武器のフォーム外項目の引き継ぎを追加した。
Issue #544 で、持ち替えポリシーの読み込み・送信、`tactics` のフォーム外キーの保持、配分の %⇔割合の変換、
配分のバリデーション（合計・許容誤差・負値・欠損部位）を追加した。

---

## 関連ファイル

- `backend/app/routers/admin.py` — `npc_router`（NPC CRUD API）
- `backend/app/services/pilot_service.py` — NPC管理者用メソッド・`get_ace_pilot_names()`
- `backend/app/services/mobile_suit_service.py` — `update_npc_mobile_suit()` / `create_npc_mobile_suit_from_master()` / `validate_npc_weapons()` / `validate_tactics()` / `validate_weapon_aim_distributions()`
- `backend/app/services/weapon_service.py` — `validate_aim_distribution()`（Garage の `update_aim_distribution()` と共通の配分検証）
- `backend/app/core/npc_data.py` — `build_npc_tactics()`（性格に応じた戦術設定）
- `backend/alembic/versions/g1b2c3d4e5f6_add_weapon_slot_count_to_mobile_suits.py` — `mobile_suits.weapon_slot_count` の追加と NPC 機のバックフィル
- `backend/app/models/models.py` — `resolve_weapon_slot_count()` / `NpcPilotEntry` / `NpcPilotDetail` / `NpcPilotUpdate` / `NpcMobileSuitEntry` / `NpcMobileSuitUpdate` / `NpcMobileSuitCreate`
- `backend/app/core/gamedata.py` — `get_ace_pilots()`（エース識別の名前一致元データ。`ace_pilots` テーブル）
- `backend/main.py` — `app.include_router(admin.npc_router)`
- `backend/tests/unit/test_admin_npcs.py` — NPC管理APIテスト
- `admin-tool/src/app/npcs/page.tsx` — 管理画面
- `admin-tool/src/hooks/useAdminNpcs.ts` — 一覧/詳細取得・更新フック
- `admin-tool/src/components/admin/NpcTable.tsx` — NPC一覧テーブル
- `admin-tool/src/components/admin/NpcEditForm.tsx` — ステータス編集フォーム・所有機体一覧・機体追加
- `admin-tool/src/components/admin/NpcMobileSuitEditForm.tsx` — NPC機体編集フォーム
- `admin-tool/src/components/admin/MobileSuitSpecFields.tsx` — 機体スペック / 武装の共通入力欄・変換ヘルパー
- `admin-tool/src/components/admin/MasterMobileSuitSelect.tsx` — 機体マスター選択プルダウン
- `admin-tool/src/components/admin/MasterWeaponSelect.tsx` — 武器マスター選択プルダウン
- `admin-tool/src/types/admin.ts` — `NpcPilot` / `NpcPilotDetail` / `NpcPilotUpdate` / `NpcMobileSuit` / `NpcMobileSuitUpdate` / `NpcMobileSuitCreate` 型定義
- `admin-tool/src/app/page.tsx` — トップナビへのリンク追加

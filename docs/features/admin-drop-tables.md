# ドロップテーブル管理画面 — 管理者専用エディタ

## 概要

定期バトル（バトルロイヤル）のドロップテーブルを、admin-tool から確認・編集する画面（Issue #562、Epic #550 Sub-Issue 5）。
シードスクリプトを本番DBで直接実行せずに、ドロップ率とエントリーを調整できるようにする。

* 編集対象は定期バトルのテーブル1つ（`scope_type = BATCH`、`scope_key = default`）
* ソロミッション単位・戦域単位のテーブル、複数テーブルの一覧・作成・削除、変更履歴は対象外
* ドロップテーブルと抽選の仕様は `blueprint-system.md` の「ドロップテーブルと抽選（Issue #560）」を参照

---

## API エンドポイント

全エンドポイントは `X-API-Key` ヘッダー（環境変数 `ADMIN_API_KEY`）による認証が必要（`verify_admin_api_key`）。
ルーターは `backend/app/routers/admin.py` の `drop_table_router`、処理は `backend/app/services/drop_table_service.py` の `DropTableService`。

### GET /api/admin/drop-tables/batch

定期バトルのテーブルを返す。テーブルが無ければ（シード未実行）、`id = null`・`drop_rate = 0`・`win_rate_multiplier = 1`・エントリー無しの既定値を返す。

```json
{
  "id": 1,
  "name": "定期バトル",
  "drop_rate": 0.3,
  "win_rate_multiplier": 1.5,
  "entries": [
    {
      "blueprint_id": "mobile_suit:gelgoog",
      "target_type": "MOBILE_SUIT",
      "target_id": "gelgoog",
      "target_name": "ゲルググ",
      "faction": "ZEON",
      "is_standard_issue": false,
      "weight": 1,
      "requires_win": true
    }
  ],
  "unobtainable_blueprints": [
    {
      "blueprint_id": "weapon:beam_rifle",
      "target_type": "WEAPON",
      "target_id": "beam_rifle",
      "target_name": "Beam Rifle",
      "faction": "",
      "is_standard_issue": false
    }
  ]
}
```

| 項目 | 内容 |
|---|---|
| `entries` | 追加した順（`drop_table_entries.id` 順） |
| `target_name` | 機体は `name_ja`（空なら `name`）、武器は `name`。対象のマスターが無ければ `target_id` |
| `faction` | 機体マスターの勢力。武器と共通機体は空文字 |
| `unobtainable_blueprints` | 要設計図（`is_standard_issue = false`）なのに、このテーブルに入っていない設計図。設計図ID順 |

* テーブル・エントリー・全設計図（機体・武器マスターを外部結合）をそれぞれ1回のクエリで取得する。エントリー数によらずクエリは3回

### PUT /api/admin/drop-tables/batch

定期バトルのテーブルを保存し、保存後の内容を GET と同じ形で返す。

```json
{
  "name": "定期バトル",
  "drop_rate": 0.3,
  "win_rate_multiplier": 1.5,
  "entries": [
    { "blueprint_id": "mobile_suit:gelgoog", "weight": 1, "requires_win": true }
  ]
}
```

* テーブルが無ければ作成する。エントリーは `entries` の内容で置き換える。1回のコミットで保存する
* エントリーが0件のテーブルも保存できる。ドロップを止める運用に使う
* ミッションのテーブルは変更しない

**バリデーション（いずれも `422`、何も保存しない）:**

| 条件 | 判定する場所 |
|---|---|
| `drop_rate` が 0〜1 の範囲外 | スキーマ（`DropTableUpdate`） |
| `win_rate_multiplier` が 1 未満 | スキーマ |
| `weight` が 1 未満、または整数でない | スキーマ（`DropTableEntryInput`） |
| `name` が空 | スキーマ |
| 同じ設計図が2つ以上のエントリーにある | `DropTableService.save()`。`detail` は `Duplicate blueprints: ...` |
| 設計図マスターに無い設計図がある | `DropTableService.save()`。`detail` は `Blueprints not found: ...` |

---

## フロントエンド（`admin-tool/`）

### ルーティング

`/drop-tables`。トップページ（`src/app/page.tsx`）の「ドロップテーブル管理」からリンクする。

### 画面構成

| セクション | 内容 |
|---|---|
| テーブルの設定 | `name`・`drop_rate`（0〜1）・`win_rate_multiplier`（1以上）。入力値から、1回のバトルで何かがドロップする確率を勝利時・敗北時で表示する |
| エントリー | 設計図（種別・名前・標準配備か要設計図か）、重み、勝利時のみ、勝敗別・勢力別の出現率、削除ボタン。機体・武器マスターのプルダウンから追加する |
| 入手手段の無い要設計図 | 要設計図なのにテーブルに入っていない機体・武器の一覧。「テーブルに追加」でエントリーに加えられる |

* テーブルの設定とエントリーは「保存」でまとめて1回で送る。「変更を破棄」で保存済みの内容に戻す
* 未保存の変更があれば「未保存の変更がある」、テーブルが未作成なら「保存すると作成される」と表示する
* 標準配備の設計図のエントリーには「標準配備のため設計図なしで購入できる。ドロップしても換金されるだけになる」と注意を表示する
* すでにテーブルにある設計図を追加しようとすると、追加せずにメッセージを表示する

### 出現率の計算（`src/lib/dropTable.ts`）

`dropChances()` が、エントリーごとに1回のバトルでその設計図が出る確率を返す。backend の `DropService.roll()` と同じ計算にする。

* ドロップ率: 敗北時は `drop_rate`、勝利時は `min(drop_rate × win_rate_multiplier, 1)`（`effectiveDropRate()`）
* 設計図の確率: ドロップ率 × そのエントリーの重み ÷ 抽選対象の重みの合計
* 抽選対象外（敗北時の勝利時のみエントリー、パイロットの勢力で扱えない機体）は `null` を返し、「—」と表示する。勢力の判定は backend の `is_available_to_faction()` と同じ（`isAvailableToFaction()`）
* 勢力は連邦（`FEDERATION`）・ジオン（`ZEON`）の2通りを表示する。対象外のエントリーがあると、同じ勢力の残りのエントリーの確率が上がる
* 保存前の入力値（`useWatch`）で再計算する。入力途中の不正な重みは 0 として扱う

入手手段の無い要設計図の一覧も、保存前の入力を反映する（`unobtainableBlueprints()`）。
保存済みの `unobtainable_blueprints` に保存済みエントリーのうち要設計図のものを足し、編集中のエントリーを除く。

### コンポーネント・フック

| ファイル | 役割 |
|---|---|
| `src/app/drop-tables/page.tsx` | 画面。保存結果をトーストで表示する |
| `src/components/admin/DropTableForm.tsx` | テーブルの設定・エントリー・入手手段の無い要設計図の編集。`react-hook-form` + `zod`（`"use no memo"` 付き） |
| `src/components/admin/DropTableEntryRow.tsx` | エントリー1行。重み・勝利時のみの入力と、勝敗別・勢力別の出現率 |
| `src/hooks/useAdminDropTable.ts` | `GET` / `PUT /api/admin/drop-tables/batch`。保存後は SWR のキャッシュをレスポンスで置き換える |
| `src/lib/dropTable.ts` | フォームのスキーマ（`dropTableFormSchema`）、出現率の計算、設計図IDの組み立て（`blueprintIdFor()`、backend の `BlueprintService.blueprint_id_for()` と同じ規則） |
| `src/types/admin.ts` | `DropTableDetail` / `DropTableEntryDetail` / `BlueprintTargetSummary` / `DropTableUpdate` / `DropTableEntryInput` |

* 機体・武器の追加には、既存の `MasterMobileSuitSelect` / `MasterWeaponSelect` を使う
* フォームのスキーマでも範囲・重複を検証する。backend の 422 は保存前に防げるが、backend 側の検証が正とする

---

## テスト

### バックエンド

`backend/tests/test_admin_drop_tables.py`

* 認証（APIキー違いで 401、テーブルを作成しない）
* 取得: テーブルが無いときの既定値、エントリーの表示情報、入手手段の無い要設計図、ミッションのテーブルを返さないこと、クエリ回数が3回で一定
* 保存: テーブルの作成、既存エントリーの置き換え、0件での保存、ミッションのテーブルを変更しないこと、ショップの入手ヒントと抽選への反映
* バリデーション: 重複・存在しない設計図・範囲外の値が 422 になり、保存されないこと

```bash
cd backend && python -m pytest tests/test_admin_drop_tables.py --tb=short
```

### admin-tool

`admin-tool/tests/unit/dropTable.test.ts`

* ドロップ率・勢力判定・勝敗別・勢力別の出現率、不正な重みの扱い、表示の書式
* フォームのスキーマ（範囲外の値・重複）、保存リクエストへの変換、設計図IDの組み立て、入手手段の無い要設計図の再計算

```bash
cd admin-tool && npx vitest run && npx tsc --noEmit && npm run lint
```

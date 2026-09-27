# 技術マスター管理画面 — 管理者専用エディタ

## 概要

技術断片・技術Lv（Issue #569、Epic #550 Sub-Issue 8）の技術マスターを、admin-tool から一覧・追加・編集・削除する画面。
技術はコードで固定せずマスターデータとして持つため、コードを変えずに新しい技術断片を運用に追加できる。

* 技術断片・技術Lv・購入条件の仕様は `blueprint-system.md` の「技術断片と技術Lv（Issue #569）」を参照
* 機体・武器に必要な技術Lvは、機体・武器の編集フォームの「設計図」欄で設定する（`admin-mobile-suits.md`・`admin-weapons.md`）
* 技術断片をドロップさせるには、ドロップテーブル（`admin-drop-tables.md`）に技術断片のエントリーを追加する

> 技術Lvは、機体の `beam_generator_lv`（装備できるビーム武器のLv）とは別物。技術IDは `*_tech` のように、機体の項目と重ならない名前にする。

---

## API エンドポイント

全エンドポイントは `X-API-Key` ヘッダー（環境変数 `ADMIN_API_KEY`）による認証が必要。
ルーターは `backend/app/routers/admin.py` の `technology_router`、処理は `backend/app/services/technology_service.py` の `TechnologyService`。

| メソッド | パス | 内容 |
|---|---|---|
| `GET` | `/api/admin/technologies` | 全技術を技術ID順に返す |
| `POST` | `/api/admin/technologies` | 技術を追加する。`201` |
| `PUT` | `/api/admin/technologies/{tech_id}` | 技術を更新する。省略した項目は変更しない |
| `DELETE` | `/api/admin/technologies/{tech_id}` | 技術を削除する。`204` |

```json
{
  "id": "psycommu_tech",
  "name": "サイコミュ技術",
  "description": "サイコミュ武器、サイコミュ搭載機体の開発に必要な技術",
  "level_thresholds": [3, 8, 15],
  "overflow_credit_value": 500
}
```

| 項目 | 内容 |
|---|---|
| `id` | スネークケース英数字（`^[a-z0-9_]+$`）。変更できない |
| `level_thresholds` | Lvごとに必要な累計断片数。要素数が最大Lv。1要素以上で、正の整数の狭義単調増加 |
| `overflow_credit_value` | 最大Lvに達した後に断片を入手したときに付与するクレジット。0以上 |

**エラー:**

| 条件 | ステータス |
|---|---|
| `id` の形式が不正、閾値が不正、名前が空、換金額が負 | `422` |
| `id` が重複している | `409` |
| 閾値を減らして最大Lvが下がり、それを超える必要Lvを設定した設計図がある | `422`（`detail` に該当する設計図ID） |
| 設計図の購入条件（`blueprint_tech_requirements`）かドロップテーブルから参照されている技術の削除 | `409` |
| 技術が無い | `404` |

* 削除すると、全プレイヤーのその技術の累計断片数（`player_technologies`）も削除する
* 閾値を引き上げると、既存プレイヤーの技術Lvが下がることがある。購入済みの機体・武器は残るため許容する

---

## フロントエンド（`admin-tool/`）

### ルーティング

`/technologies`。トップページ（`src/app/page.tsx`）の「技術マスタ管理」からリンクする。

### 画面構成

| セクション | 内容 |
|---|---|
| 技術一覧 | 技術名・ID・閾値（最大Lv）・最大Lv後の換金額・削除ボタン。行を押すと編集する |
| 編集フォーム | ID（新規作成のみ入力可）・表示名・説明・Lvごとの累計断片数（カンマ区切り）・最大Lv後の換金額。入力中の閾値から「最大Lv3: Lv1=3個 / Lv2=8個 / Lv3=15個」を表示する |

* 新規作成の初期値は閾値 `3, 8, 15`・換金額 500 C（`technologies.json` の初期データと同じ）
* 削除は確認ダイアログを挟む。参照されている技術の削除は backend の `409` のメッセージをトーストで表示する
* 閾値の検証（`thresholdsError()`）は backend の `validate_level_thresholds()` と同じ規則。backend 側の検証が正とする

### コンポーネント・フック

| ファイル | 役割 |
|---|---|
| `src/app/technologies/page.tsx` | 画面。保存・削除の結果をトーストで表示する |
| `src/components/admin/TechnologyTable.tsx` | 技術一覧 |
| `src/components/admin/TechnologyEditForm.tsx` | 追加・編集フォーム。`react-hook-form` + `zod`（`"use no memo"` 付き） |
| `src/components/admin/MasterTechnologySelect.tsx` | 技術マスターのプルダウン（ドロップテーブルの「技術断片を追加」で使う） |
| `src/components/admin/BlueprintSettingsFields.tsx` | 設計図設定の「必要な技術Lv」の行（技術の選択 ＋ Lv）。機体・武器の編集フォームで共用 |
| `src/hooks/useAdminTechnologies.ts` | 技術マスターの取得・追加・更新・削除。保存後は SWR のキャッシュをレスポンスで置き換える |
| `src/lib/technology.ts` | フォームのスキーマ、閾値の解析・検証、必要な技術Lvのスキーマ（`techRequirementsSchema`、同じ技術の重複を禁止） |

---

## テスト

### バックエンド

`backend/tests/test_technologies.py`

* 初期データ、Lvの計算、断片の付与（Lvアップ・最大Lv到達・最大Lv後の換金）、閾値の変更でLvが下がること
* 購入の判定（設計図と技術Lvの組み合わせ・標準配備）、ショップ一覧の `missing_tech_requirements`、購入APIの `403`、クエリ回数
* 設計図設定の `tech_requirements` の保存・置換・バリデーション、機体・武器マスター削除時の後始末
* 技術マスターの CRUD とバリデーション（閾値・ID・重複・最大Lvの引き下げ・参照中の削除）
* ドロップ（技術断片の付与・換金・勢力で外れないこと・勝利時のみ・候補の順序）、ドロップテーブルの保存
* 戦利品の名前、図鑑の必要な技術Lv、`GET /api/technologies/me`

```bash
cd backend && python -m pytest tests/test_technologies.py --tb=short
```

### admin-tool

`admin-tool/tests/unit/technology.test.ts`（閾値の解析・検証、フォームの変換、行追加の初期値）、`blueprintSettings.test.ts`（必要な技術Lvのスキーマ）、`dropTable.test.ts`（技術断片のエントリー）

```bash
cd admin-tool && npx vitest run && npx tsc --noEmit && npm run lint
```

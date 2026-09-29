# 戦域・環境タイプ管理画面 — 管理者専用エディタ

## 概要

戦域ローテーション（Epic #573）の環境タイプと戦域を、admin-tool から一覧・追加・編集・削除する画面（Issue #579、Sub-Issue 6）。
コードを変えずに、戦域（一年戦争の地名・作戦名）と環境タイプを運用で追加し、効果パラメータやミノフスキー濃度をプレイの様子を見ながら調整できる。

* データモデル・ローテーションの決め方・戦闘への適用は [theater-rotation.md](theater-rotation.md) を参照
* 環境タイプの効果（索敵・射撃ペナルティ・地形適正）の計算は [battle-engine-feature.md 30章](battle-engine-feature.md#30-環境タイプの効果と地形適正) を参照
* 機体の地形適正は、機体マスターの編集フォームの「地形適正」欄で設定する（[admin-mobile-suits.md](admin-mobile-suits.md)）

---

## 変更がいつ反映されるか

| 変更 | 反映 |
|---|---|
| 戦域の追加・削除、`rotation_order`・`is_active`・濃度（`base_minovsky`・`minovsky_variance`） | 次に作成されるルームから。作成済みの OPEN ルーム（今回）の戦域と濃度はルームに保存済みなので変わらない |
| 戦域の `environment_id`・`obstacle_density` | 次の戦闘から。今回のルームにも反映する（戦闘時に戦域マスターから読むため） |
| 環境タイプの効果パラメータ・既定値 | 次の戦闘から。今回のルームにも反映する（戦闘時に環境タイプマスターから読むため） |

* ローテーションの位置は `(開催日 − THEATER_ROTATION_EPOCH) mod 有効な戦域数` で決まる。戦域を追加・無効化すると、以降の開催日の戦域がずれる
* 濃度のシードは開催日と戦域IDで決まる。基準値・揺らぎ幅を変えると、次回以降の濃度が変わる

---

## API エンドポイント

全エンドポイントは `X-API-Key` ヘッダー（環境変数 `ADMIN_API_KEY`）による認証が必要。
ルーターは `backend/app/routers/admin.py` の `environment_router`・`theater_router`、処理は `backend/app/services/theater_service.py` の `TheaterService`。
リクエスト・レスポンスのモデルは `backend/app/models/models.py` の `MasterEnvironment*`・`MasterTheater*`。

### 環境タイプ

| メソッド | パス | 内容 |
|---|---|---|
| `GET` | `/api/admin/environments` | 全環境タイプを環境ID順に返す |
| `POST` | `/api/admin/environments` | 環境タイプを追加する。`201` |
| `PUT` | `/api/admin/environments/{environment_id}` | 環境タイプを更新する。省略した項目は変更しない。`id` は変更できない |
| `DELETE` | `/api/admin/environments/{environment_id}` | 環境タイプを削除する。`204` |

```json
{
  "id": "DESERT",
  "name": "砂漠",
  "description": "砂嵐が視界を遮る。",
  "sensor_range_multiplier": 0.9,
  "ranged_accuracy_penalty": 0.1,
  "ranged_penalty_ref_distance": 500.0,
  "default_obstacle_density": "SPARSE",
  "default_terrain_grade": "B",
  "viewer_preset": "GROUND"
}
```

| 項目 | 規則 |
|---|---|
| `id` | 大文字スネークケース英数字（`^[A-Z0-9_]+$`）。機体の `terrain_adaptability` のキーになるため変更できない |
| `name` | 空は不可 |
| `sensor_range_multiplier` | 0 より大きく 1 以下 |
| `ranged_accuracy_penalty` | 0〜1 |
| `ranged_penalty_ref_distance` | 0 より大きい |
| `default_obstacle_density` | `NONE`/`SPARSE`/`MEDIUM`/`DENSE` |
| `default_terrain_grade` | `S`〜`D` |
| `viewer_preset` | `SPACE`/`GROUND`/`COLONY`/`UNDERWATER`/`FOREST` |

| 条件 | ステータス |
|---|---|
| 上の規則に反する | `422` |
| `id` が重複している | `409` |
| 戦域から参照されている環境タイプの削除 | `409`（`detail` に参照している戦域ID） |
| 環境タイプが無い | `404` |

* 削除しても、機体の `terrain_adaptability` に残ったそのキーは消さない。同じIDで作り直すと再び使われる
* パラメータで表せるのは、索敵範囲・射撃の命中率・障害物密度・地形適正の既定ランク・描画プリセットだけ。水中でのビーム減衰のような新しい仕組みが必要な環境は、戦闘エンジンの実装が要る（画面にも注記する）
* BattleViewer が描画を用意していないプリセットは宇宙として描画する（[theater-rotation.md](theater-rotation.md#バトル結果の表示)）

### 戦域

| メソッド | パス | 内容 |
|---|---|---|
| `GET` | `/api/admin/theaters` | 全戦域を巡回順（`rotation_order`、`id`）に返す。無効な戦域も含める |
| `GET` | `/api/admin/theaters/rotation?days=14` | 今回と、その後 `days − 1` 回分の開催の戦域・濃度を返す。`days` は 1〜28（既定 14） |
| `POST` | `/api/admin/theaters` | 戦域を追加する。`201` |
| `PUT` | `/api/admin/theaters/{theater_id}` | 戦域を更新する。省略した項目は変更しない。`id` は変更できない |
| `DELETE` | `/api/admin/theaters/{theater_id}` | 戦域を削除する。`204` |

```json
{
  "id": "odessa",
  "name": "オデッサ",
  "environment_id": "SPACE",
  "base_minovsky": 0.5,
  "minovsky_variance": 0.1,
  "obstacle_density": null,
  "hint": "ヒント",
  "description": "説明",
  "rotation_order": 30,
  "is_active": true
}
```

| 項目 | 規則 |
|---|---|
| `id` | スネークケース英数字（`^[a-z0-9_]+$`）。変更できない |
| `name` | 空は不可 |
| `environment_id` | 環境タイプのマスターにあること |
| `base_minovsky` | 0〜1 |
| `minovsky_variance` | 0〜0.5 |
| `obstacle_density` | `NONE`/`SPARSE`/`MEDIUM`/`DENSE` または null（環境タイプの既定値）。PUT で null を送ると既定値に戻す |

| 条件 | ステータス |
|---|---|
| 上の規則に反する（環境タイプが無いことを含む） | `422` |
| `id` が重複している | `409` |
| 最後の有効な戦域を無効にする、または削除する | `409` |
| 終了していない（`COMPLETED` 以外の）ルームに割り当てられている戦域の削除 | `409` |
| 戦域が無い | `404` |

* 削除しても、終了したルーム（`battle_rooms`）とバトル結果（`battle_results`）の `theater_id` は残す。
  そのため両テーブルの `theater_id` には外部キーを張っていない（マイグレーション `m7a8b9c0d1e2_drop_theater_foreign_keys.py`）
* マスターに無い戦域のバトル結果は、戦域名の代わりに戦域IDを表示する（`TheaterService.labels_for()`）
* 戦域別ドロップテーブル（Sub-Issue 7、Issue #580）を追加するときは、戦域の削除でそのドロップテーブルも削除する
* ローテーション API は公開の予報 API（`GET /api/theaters/forecast`）と同じ `TheaterForecastService.forecast()` を使う。今回（`is_current`）は OPEN ルームに保存した値を返す

---

## フロントエンド（`admin-tool/`）

### ルーティング

`/theaters`（戦域）・`/environments`（環境タイプ）。トップページ（`src/app/page.tsx`）の「戦域管理」「環境タイプ管理」からリンクする。2つの画面は互いにリンクする。

### 戦域の画面

| セクション | 内容 |
|---|---|
| 注記 | 変更の反映時期（上の表）、最後の有効な戦域、削除後の過去の結果 |
| 戦域一覧 | 順番（入力欄）・有効（チェックボックス）・戦域名とID・環境（障害物密度を指定していれば併記）・濃度の範囲（例: 20%〜50%）・削除ボタン。行を押すと編集する |
| 今後14日のローテーション | 開催日（JST）・戦域・環境・濃度（％と低・中・高）。今回は「今回（確定）」と表示する。戦域を保存・削除するたびに取り直す |
| 編集フォーム | ID（新規作成のみ）・表示名・環境タイプ・障害物密度（「環境タイプの既定値」を含む）・濃度の基準値と揺らぎ幅（入力中の値から濃度の範囲を表示）・ヒント・説明。新規作成のときだけ順番と有効化も入力する |

* 順番は入力欄を確定したとき（フォーカスを外す・Enter）、有効化はチェックを変えたときに保存する
* 最後の有効な戦域は、チェックボックスと削除ボタンを押せない（backend の `409` と同じ規則）
* 編集フォームは順番と有効化を送らない。一覧で変えた値を、フォームを開いた時点の値で戻さないため
* 編集フォームは編集対象を替えたときだけ作り直す（`key`）。一覧で順番・有効化を変えても入力中の値は消えない
* 新規作成の順番の初期値は、既存の最大値 + 10

### 環境タイプの画面

| セクション | 内容 |
|---|---|
| 注記 | パラメータで表せない環境があること、変更は作成済みのルームにも反映すること |
| 環境タイプ一覧 | 名前とID・索敵倍率・射撃ペナルティ（基準距離）・障害物密度・既定ランク・描画プリセット・削除ボタン |
| 編集フォーム | ID（新規作成のみ）・表示名・説明・各パラメータ。選択肢の項目はプルダウン |

* 新規作成の初期値は効果なし（索敵 ×1.0、ペナルティ 0、基準距離 400m、障害物 `MEDIUM`、既定ランク `A`、描画 `SPACE`）
* 削除は確認ダイアログを挟む。参照されている環境タイプの削除は backend の `409` のメッセージをトーストで表示する

### コンポーネント・フック

| ファイル | 役割 |
|---|---|
| `src/app/theaters/page.tsx` | 戦域の画面 |
| `src/app/environments/page.tsx` | 環境タイプの画面 |
| `src/components/admin/TheaterTable.tsx` | 戦域一覧。順番と有効化の入力 |
| `src/components/admin/TheaterEditForm.tsx` | 戦域の追加・編集フォーム。`react-hook-form` + `zod`（`"use no memo"` 付き） |
| `src/components/admin/TheaterRotationPanel.tsx` | 今後のローテーション |
| `src/components/admin/EnvironmentTable.tsx` | 環境タイプ一覧 |
| `src/components/admin/EnvironmentEditForm.tsx` | 環境タイプの追加・編集フォーム |
| `src/components/admin/TerrainAdaptabilityFields.tsx` | 機体の地形適正の入力欄（機体マスターの編集フォームで使う） |
| `src/hooks/useAdminTheaters.ts` | 戦域とローテーションの取得、戦域の追加・更新・削除。保存後にローテーションを取り直す |
| `src/hooks/useAdminEnvironments.ts` | 環境タイプの取得・追加・更新・削除 |
| `src/lib/theater.ts` | フォームのスキーマと変換、選択肢、濃度の範囲・開催日の表示、地形適正の設定（`setTerrainGrade()`・`unmanagedTerrainKeys()`） |
| `src/lib/adminApi.ts` | 管理APIの fetcher とリクエスト（APIキーの付与、エラーの `detail` の変換） |

---

## テスト

### バックエンド

`backend/tests/test_admin_theaters.py`

* 環境タイプの一覧・追加・更新（部分更新、IDを変えられないこと）・削除、入力チェック（IDの形式・数値の範囲・選択肢）、重複・参照中の削除・無い場合
* 戦域の一覧（無効な戦域を含む巡回順）・追加・更新（障害物密度を null で既定値に戻す）、入力チェック、重複・無い環境タイプ
* 最後の有効な戦域の無効化・削除、終了していないルームの戦域の削除を拒否する
* 戦域を削除しても、終了したルームとバトル結果の戦域IDが残り、名前の代わりにIDを表示する
* ローテーションの日数（既定14、範囲外は 422）、戦域の変更が次回以降だけに反映されること
* 機体マスターの地形適正の保存・省略時に変えないこと・不正なランク

`backend/tests/test_theater_battle.py`: マスターに無い戦域のバトル結果は戦域IDを名前にする

```bash
cd backend && python -m pytest tests/test_admin_theaters.py tests/test_theater_battle.py --tb=short
```

### admin-tool

`admin-tool/tests/unit/theater.test.ts`（フォームの検証と変換、並び順、濃度の範囲、開催日、地形適正の設定・マスターに無いキー・機体フォームでの検証）

```bash
cd admin-tool && npx vitest run && npx tsc --noEmit && npm run lint
```

---

## 本番への反映

* マイグレーション `m7a8b9c0d1e2`（`battle_rooms`・`battle_results` の `theater_id` の外部キーを外す）を本番DBに適用する必要がある。適用前でも画面は使えるが、過去の結果がある戦域の削除は DB の外部キー違反で失敗する
* 本番DB（Neon）への適用は書き込みになるため、実行前に確認を取る

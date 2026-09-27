# 戦域ローテーション — 戦域・環境タイプのデータ基盤

## 概要

定期バトル（デイリーバトルロイヤル）のルームに、開催日ごとの「戦域」と「ミノフスキー濃度」を割り当てる仕組み。
Epic #573「戦域ローテーションと環境効果」の土台で、本ドキュメントは Sub-Issue 1（Issue #574）の範囲を記述する。

* 戦域は一年戦争の地名・作戦名（例: ソロモン宙域、東南アジア密林）。環境タイプ（宇宙・森林など）を1つ持つ
* 戦域・環境タイプはコードに書かず、マスターデータ（DB）として持つ
* 開催日から戦域と濃度を決定的に計算する。スケジュール表は持たない

> 現時点では戦闘の挙動は変わらない。初期データで有効な戦域は「ソロモン宙域（宇宙・濃度0）」だけで、シミュレーターにはまだ渡していない。

### 今後の予定（Epic #573）

| Sub-Issue | 内容 |
|---|---|
| 3 | 環境タイプの効果パラメータ（索敵・射撃ペナルティ）を戦闘に使う。`FOREST` の初期値を確定する |
| 4 | ルームの戦域・濃度を戦闘に適用し、`BattleResult` に記録する。森林を有効化し、濃度を実際の値にする |
| 5 | 予報 API（`TheaterService.forecast()` を使う） |
| 6 | admin-tool の戦域・環境タイプ編集画面 |
| 7 | ドロップテーブルの適用範囲に `THEATER` を追加する |

---

## データモデル

定義は `backend/app/models/models.py`。

### 環境タイプ（`master_environments` / `MasterEnvironment`）

| 項目 | 型 | 説明 |
|---|---|---|
| `id` | str (PK) | 大文字スネークケース。機体の `terrain_adaptability` のキーと同じ（例: `SPACE`、`FOREST`） |
| `name` | str | 表示名（例: 宇宙、森林） |
| `description` | str | 説明 |
| `sensor_range_multiplier` | float | 索敵範囲の倍率。0 より大きく 1 以下。既定 1.0 |
| `ranged_accuracy_penalty` | float | 射撃命中ペナルティの係数 α。0〜1。既定 0 |
| `ranged_penalty_ref_distance` | float | ペナルティが最大になる距離 D（m）。0 より大きい。既定 400 |
| `default_obstacle_density` | str | 障害物密度の既定値（`NONE`/`SPARSE`/`MEDIUM`/`DENSE`） |
| `default_terrain_grade` | str | 機体に地形適正の設定が無いときのランク（`S`〜`D`）。既定 `A` |
| `viewer_preset` | str | BattleViewer の描画プリセット（`SPACE`/`GROUND`/`COLONY`/`UNDERWATER`/`FOREST`） |
| `created_at` / `updated_at` | datetime | |

* 数値の範囲は DB の CHECK 制約で守る
* 文字列の選択肢は `ObstacleDensity`・`TerrainGrade`・`ViewerPreset`（StrEnum）で定義する。シードスクリプトは投入前にこの値を検証する
* 既存エンジンが使う `SPACE`/`GROUND`/`COLONY`/`UNDERWATER` はそのまま環境IDとして使える（ソロミッションの `Mission.environment` と互換）

### 戦域（`master_theaters` / `MasterTheater`）

| 項目 | 型 | 説明 |
|---|---|---|
| `id` | str (PK) | スネークケース（例: `solomon`） |
| `name` | str | 表示名 |
| `environment_id` | str (FK → `master_environments.id`) | 環境タイプ |
| `base_minovsky` | float | ミノフスキー濃度の基準値。0〜1 |
| `minovsky_variance` | float | 揺らぎ幅。0〜0.5 |
| `obstacle_density` | str \| null | 障害物密度。null なら環境タイプの既定値 |
| `hint` | str | 予報に出す有利・不利のヒント |
| `description` | str | フレーバーテキスト |
| `rotation_order` | int | ローテーション順（昇順） |
| `is_active` | bool | ローテーションに含めるか |
| `created_at` / `updated_at` | datetime | |

### ルームと結果

| テーブル | 追加カラム | 説明 |
|---|---|---|
| `battle_rooms` | `theater_id`（FK、nullable）、`minovsky_density`（float、nullable） | ルーム作成時に保存する |
| `battle_results` | `theater_id`（FK、nullable）、`minovsky_density`（float、nullable） | 値を入れるのは Sub-Issue 4。現時点では常に null |

* 導入前に作成されたルーム・結果は null のまま（バックフィルしない）。Sub-Issue 4 では宇宙・濃度0として扱う
* 有効な戦域が無いときに作成したルームは `theater_id = null`、`minovsky_density = 0.0`

マイグレーション: `backend/alembic/versions/l6f7a8b9c0d1_add_theaters.py`

---

## 戦域とミノフスキー濃度の決め方

処理は `backend/app/services/theater_service.py` の `TheaterService`。

### 開催日

開催予定時刻（`BattleRoom.scheduled_at`）の JST の日付。タイムゾーン無しの時刻（SQLite が返す値）は UTC とみなす。
定期バトルは 21:00 JST（12:00 UTC）開催なので、開催日は UTC の日付と一致する。

### 戦域

1. `is_active = true` の戦域を `(rotation_order, id)` の順に並べる
2. `index = (開催日 − THEATER_ROTATION_EPOCH).days mod 戦域数` の戦域を選ぶ

* `THEATER_ROTATION_EPOCH = date(2026, 1, 1)`。変えると全開催日の戦域がずれる
* 管理者が戦域の有効化や順番を変えると、以降の開催日の戦域もずれる。作成済みの OPEN ルームの戦域は変えない
* 有効な戦域が1つも無い場合は「戦域なし」（`theater_id = null`、濃度 0）を返す。ルーム作成は止めない

### ミノフスキー濃度

1. `random.Random(f"{開催日}:{theater_id}")` で `基準値 ± 揺らぎ幅` の一様乱数を引く
2. [0, 1] にクランプする
3. 小数第2位に丸める

シードが開催日と戦域IDだけで決まるため、予報で出した値と実際の開催時の値が一致する（戦域の設定を変えない限り）。
`random.Random` に文字列を渡したときのシードはハッシュのランダム化の影響を受けないため、プロセスをまたいでも同じ値になる。

### 主な関数

| 関数 | 説明 |
|---|---|
| `TheaterService.battle_date_of(scheduled_at)` | 開催予定時刻から開催日（JST）を返す |
| `TheaterService.resolve_for_date(session, date)` | 開催日の `TheaterAssignment`（`theater_id`・`environment_id`・`minovsky_density`）を返す。将来ストーリーイベントで期間限定の戦域を固定する場合はここを差し替える |
| `TheaterService.forecast(session, from_date, days)` | `from_date` から `days` 日分の `TheaterAssignment` を返す（Sub-Issue 5 の予報 API で使う） |

---

## ルームの作成と延期

処理は `backend/app/services/battle_room_service.py` の `BattleRoomService`。

| 関数 | 説明 |
|---|---|
| `get_or_create_open_room(session, now=None)` | OPEN ルームを返す。無ければ次の 12:00 UTC を開催予定時刻として作成し、戦域と濃度を割り当てる。戻り値は `(ルーム, 新規作成したか)` |
| `assign_theater(session, room)` | `room.scheduled_at` の開催日で戦域と濃度を割り当てる。コミットは呼び出し側で行う |
| `next_scheduled_at(now)` | 次の開催予定時刻（12:00 UTC）を返す。12:00 UTC ちょうどは翌日 |

ルームを作成する経路はすべて `get_or_create_open_room()` を通る。

* `POST /api/entries`・`GET /api/entries/status`（`backend/app/routers/entries.py`）
* 定期バッチのフェーズ4 `create_next_open_room()`（`backend/scripts/run_batch.py`）

エントリーが無く開催予定時刻を過ぎたルームは、`MatchingService.create_rooms()` が翌日に延期する。
このとき `assign_theater()` を呼び、延期後の開催日で戦域と濃度を決め直す（エントリーが無いのでプレイヤーへの影響はない）。

---

## 初期データ

`backend/data/master/environments.json`・`backend/data/master/theaters.json` を
`backend/scripts/seed/seed_master_data.py` で投入する（既存レコードはスキップ。`--force` で上書き）。
戦域は環境タイプを外部キーで参照するため、環境タイプを先に投入する。

### 環境タイプ

| id | name | 障害物密度の既定値 | 描画プリセット | 効果パラメータ |
|---|---|---|---|---|
| `SPACE` | 宇宙 | `MEDIUM` | `SPACE` | 既定値（効果なし） |
| `FOREST` | 森林 | `DENSE` | `FOREST` | 既定値（効果なし）。Sub-Issue 3 で確定する |

### 戦域

| id | name | 環境 | 基準濃度 | 揺らぎ | 順番 | 有効 |
|---|---|---|---|---|---|---|
| `solomon` | ソロモン宙域 | SPACE | 0.0 | 0.0 | 10 | ✅ |
| `southeast_asia_jungle` | 東南アジア密林 | FOREST | 0.0 | 0.0 | 20 | ❌ |

`rotation_order` は間に戦域を追加できるように10刻みにしている。

> 本番DB（Neon）への投入・マイグレーションは書き込みになるため、実行前に確認を取る。

---

## テスト

`backend/tests/test_theaters.py`

* 開催日の計算（JST、タイムゾーン無しの扱い）
* 濃度が決定的で、基準値 ± 揺らぎ幅と [0, 1] に収まる
* 同じ開催日なら何度計算しても同じ戦域・濃度になる
* 有効な戦域が複数あると開催日ごとに交互に切り替わり、`rotation_order` に従う
* 有効な戦域が無ければ戦域なし・濃度 0
* ルーム作成時に戦域と濃度が保存され、作成済みの OPEN ルームは設定を変えても変わらない
* 延期したルームは延期後の日付で戦域を決め直す

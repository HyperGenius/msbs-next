# 戦域ローテーション — 戦域・環境タイプのデータ基盤

## 概要

定期バトル（デイリーバトルロイヤル）のルームに、開催日ごとの「戦域」と「ミノフスキー濃度」を割り当てる仕組み。
Epic #573「戦域ローテーションと環境効果」の土台で、本ドキュメントは Sub-Issue 1（Issue #574）、Sub-Issue 4（Issue #577）、Sub-Issue 5（Issue #578）の範囲を記述する。

* 戦域は一年戦争の地名・作戦名（例: ソロモン宙域、東南アジア密林）。環境タイプ（宇宙・森林など）を1つ持つ
* 戦域・環境タイプはコードに書かず、マスターデータ（DB）として持つ
* 開催日から戦域と濃度を決定的に計算する。スケジュール表は持たない

> 定期バトルは、ルームに割り当てた戦域の環境タイプ・ミノフスキー濃度・障害物密度で戦う（Issue #577）。
> 初期データでは「ソロモン宙域（宇宙）」と「東南アジア密林（森林）」を日替わりで交互に開催する。

### 今後の予定（Epic #573）

| Sub-Issue | 内容 |
|---|---|
| 2 | ミノフスキー濃度を連続値にし、索敵と射撃の命中率に反映する（Issue #575、実装済み。[battle-engine-feature.md 29章](battle-engine-feature.md#29-ミノフスキー濃度の連続値化)） |
| 3 | 環境タイプの効果パラメータ（索敵・射撃ペナルティ）を戦闘に使う。`FOREST` の初期値を確定する（Issue #576、実装済み。[battle-engine-feature.md 30章](battle-engine-feature.md#30-環境タイプの効果と地形適正)） |
| 4 | ルームの戦域・濃度を戦闘に適用し、`BattleResult` に記録する。森林を有効化し、濃度を実際の値にする（Issue #577、実装済み。本ドキュメントの「[定期バトルへの適用](#定期バトルへの適用)」） |
| 5 | 予報 API とダッシュボードの予報カード（Issue #578、実装済み。本ドキュメントの「[戦域予報](#戦域予報)」） |
| 6 | admin-tool の戦域・環境タイプ編集画面（Issue #579、実装済み。[admin-theaters.md](admin-theaters.md)） |
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
| `battle_rooms` | `theater_id`（nullable）、`minovsky_density`（float、nullable） | ルーム作成時に保存する |
| `battle_results` | `theater_id`（nullable）、`minovsky_density`（float、nullable） | 定期バトルで戦闘に適用した値を入れる。ソロミッションは null |

* 導入前に作成されたルーム・結果は null のまま（バックフィルしない）。`theater_id` が null のルームは宇宙・濃度0で戦う
* 有効な戦域が無いときに作成したルームは `theater_id = null`、`minovsky_density = 0.0`

* `theater_id` には外部キーを張らない。戦域マスターを削除しても、過去のルームと結果の戦域IDを残すため（Issue #579）

マイグレーション: `backend/alembic/versions/l6f7a8b9c0d1_add_theaters.py`、`m7a8b9c0d1e2_drop_theater_foreign_keys.py`（外部キーを外す）

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
| `TheaterService.resolve_environment_profile(session, environment_id)` | 環境タイプの `EnvironmentProfile` を返す（戦闘エンジンに渡す）。見つからなければ `None` |
| `TheaterService.environment_profile(environment)` | `MasterEnvironment` から `EnvironmentProfile` を作る |
| `TheaterService.battlefield_for(theater)` | 戦域の障害物密度を反映した `BattleField` を返す。戦域が密度を指定しなければ、エンジンが環境タイプの既定値を使う |
| `TheaterService.battle_conditions(session, theater_id, minovsky_density)` | 戦闘に適用する条件（`BattleConditions`）を返す。次章を参照 |
| `TheaterService.labels_for(session, battles)` | バトル結果ごとに戦域名・環境タイプ名・描画プリセット（`TheaterLabel`）を返す |

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

## 定期バトルへの適用

### 戦闘の条件

`scripts/run_batch.py` の `_process_room()` が、ルームの `theater_id`・`minovsky_density` から
`TheaterService.battle_conditions()` で `BattleConditions` を作り、`_run_simulation()` と `_save_battle_results()` に渡す。

| 項目 | `BattleSimulator` の引数 | 値 |
|---|---|---|
| `environment` | `environment` | 環境タイプID |
| `environment_profile` | `environment_profile` | 環境タイプの効果（`TheaterService.environment_profile()`） |
| `minovsky_density` | `minovsky_density` | `BattleRoom.minovsky_density` |
| `battlefield` | `battlefield` | `TheaterService.battlefield_for(theater)`。戦域が密度を指定しなければ環境タイプの既定値 |

`BattleConditions.simulator_kwargs()` が上の4つを返す。
ソロミッションなど他の経路でも、戦域IDと濃度があれば同じ関数で条件を作れる（ソロミッションへの適用は未対応）。

### 既定の条件（戦域を導入する前と同じ）

次のときは `BattleConditions()`（宇宙・効果なし・濃度0・障害物 `MEDIUM`）で戦う。

| ケース | 警告 |
|---|---|
| ルームの `theater_id` が null（導入前のルーム、有効な戦域が無いときに作ったルーム） | 出さない |
| 戦域のマスターが無い | 出す（`logging` の WARNING） |
| 戦域の環境タイプのマスターが無い | 出す |

マスターが無いときは `theater_id` も null として記録する（実際に戦った条件と記録を一致させるため）。

### バトル結果への記録

`_save_battle_results()` が `BattleResult` に次を保存する。

| カラム | 値 |
|---|---|
| `environment` | 環境タイプID（既定の条件では `SPACE`） |
| `theater_id` | 戦域ID（既定の条件では null） |
| `minovsky_density` | 戦闘時の濃度（既定の条件では 0.0） |

### バトル結果の表示

バトル結果・履歴の API（`GET /api/battles`・`/api/battles/unread`・`/api/battles/{id}`）の `BattleResultSummary` に次を含める。
名前は保存せず、`LootService.summaries()` が `TheaterService.labels_for()` でマスターから引く（クエリは件数によらず最大2回）。

| 項目 | 説明 |
|---|---|
| `theater_id` / `minovsky_density` | `BattleResult` の値 |
| `theater_name` | 戦域名。戦域が無ければ null。マスターに無い（削除した）戦域は戦域ID |
| `environment_name` | 環境タイプ名。マスターに無い環境（ソロミッションの `GROUND` など）は null |
| `viewer_preset` | 環境タイプの描画プリセット。マスターに無い環境は null |

フロントエンド:

* `formatTheaterLabel()`（`frontend/src/utils/theater.ts`）で「ソロモン宙域（宇宙）／ミノフスキー濃度 42%」の形式にする。戦域が無ければ null で、表示しない
* 表示する場所: バトル結果モーダル（`BattleResultModal` の「戦域」欄）、バトル履歴の一覧（`BattleList`）、リプレイのヘッダー（`ModalHeader`）
* リプレイの BattleViewer には `getViewerEnvironment()` で `viewer_preset`（無ければ `environment`）を渡す
* BattleViewer は描画を用意していない環境（現時点では `FOREST`）を `SPACE` として描画する（`toSupportedEnvironment()`）。森林の描画は Sub-Issue 8 で追加する

---

## 戦域予報

エントリー前に、今回と次回以降の戦域・環境・ミノフスキー濃度を知らせる。
予報は確定値で、実際の戦闘は予報どおりになる（戦域の設定を変えない限り）。

### API: `GET /api/theaters/forecast?days=3`

ログイン不要。`backend/app/routers/theaters.py`、処理は `backend/app/services/theater_forecast_service.py` の `TheaterForecastService.forecast()`。

* `days` は 1〜7（既定 3）。範囲外は 422
* 今回（OPEN ルームの開催）と、その後 `days − 1` 回分の開催を、開催予定時刻の昇順で返す
* 今回はルームに保存した `theater_id`・`minovsky_density` を返す。次回以降は `TheaterService.forecast()` で開催日から計算する
* OPEN ルームが無いときは、ルーム作成時と同じ計算（`next_scheduled_at()` と `resolve_for_date()`）で今回の値を返す。GET ではルームを作らない
* 戦域の無い開催（有効な戦域が無い、戦域のマスターが無い）は含めない。有効な戦域が無ければ空の配列になる
  * 作成済みの OPEN ルームに戦域があれば、その後すべての戦域を無効にしても今回の分は返す（そのルームは保存した戦域で戦うため）

レスポンス（`TheaterForecast`、`backend/app/models/models.py`）:

```json
[
  {
    "scheduled_at": "2026-10-01T12:00:00Z",
    "is_current": true,
    "theater_id": "southeast_asia_jungle",
    "theater_name": "東南アジア密林",
    "environment_id": "FOREST",
    "environment_name": "森林",
    "default_terrain_grade": "A",
    "minovsky_density": 0.62,
    "minovsky_level": "MEDIUM",
    "hint": "格闘・索敵に強い機体が有利。長距離射撃は不利",
    "description": "..."
  }
]
```

| 項目 | 説明 |
|---|---|
| `is_current` | OPEN ルームの開催なら true |
| `environment_name` | 環境タイプ名。マスターに無ければ環境タイプID |
| `default_terrain_grade` | 環境タイプの地形適正の既定ランク。フロントエンドが機体に設定の無い環境のランクを出すのに使う |
| `minovsky_level` | `LOW`（0.33 未満）、`MEDIUM`（0.66 未満）、`HIGH`（それ以上）。しきい値は `MINOVSKY_LEVEL_LOW_MAX`・`MINOVSKY_LEVEL_MEDIUM_MAX` |

管理者が戦域の有効化や順番を変えると、次回以降の予報も変わる。今回の分はルームに保存した値なので変わらない。

### ダッシュボードの予報カード

`frontend/src/components/Dashboard/TheaterForecastCard.tsx`。`EntryDashboard` の先頭に表示する（エントリー前・エントリー後の両方）。
予報は `useTheaterForecast()`（`frontend/src/services/theaters.ts`）で取得し、ホーム画面（`app/page.tsx`）から渡す。

* 今回の戦域: 戦域名、環境、ミノフスキー濃度（％と低・中・高）、ヒント
* エントリー中の機体の、その環境の地形適正（例: 「あなたの機体: 森林適正 B」）。C 以下は「この戦域には不向き」と注意を出す
  * 機体の `terrain_adaptability` にその環境が無ければ `default_terrain_grade` を使う（戦闘時と同じ）
* カードの下に次回以降を「次回 10/2(金) 🌌 ソロモン宙域（宇宙・ミノフスキー 低）」の形で並べる。日付は JST
* 環境ごとのアイコンと色（`getEnvironmentVisual()`、`frontend/src/utils/theater.ts`）: 宇宙は 🌌 とシアン、森林は 🌲 と緑。未知の環境タイプは 🛰️ と既定の色
* 予報が空なら「現在、戦域の予報はありません」を出す

Storybook: `Dashboard/TheaterForecastCard`（宇宙・森林・不向きな機体・予報なし・未知の環境タイプ）

---

## 初期データ

`backend/data/master/environments.json`・`backend/data/master/theaters.json` を
`backend/scripts/seed/seed_master_data.py` で投入する（既存レコードはスキップ。`--force` で上書き）。
戦域は環境タイプを外部キーで参照するため、環境タイプを先に投入する。

### 環境タイプ

| id | name | 索敵範囲の倍率 | 射撃ペナルティ α | 基準距離 D | 障害物密度の既定値 | 地形適正の既定ランク | 描画プリセット |
|---|---|---|---|---|---|---|---|
| `SPACE` | 宇宙 | 1.0 | 0.0 | 400m | `SPARSE` | `A` | `SPACE` |
| `FOREST` | 森林 | 0.8 | 0.2 | 400m | `DENSE` | `A` | `FOREST` |

効果パラメータの使い方は [battle-engine-feature.md 30章](battle-engine-feature.md#30-環境タイプの効果と地形適正) を参照。
Issue #576 で `SPACE` の障害物密度の既定値を `MEDIUM` から `SPARSE` に変えた。
既存の本番DBのレコードは `seed_master_data.py --force` で更新する。

### 戦域

| id | name | 環境 | 基準濃度 | 揺らぎ | 障害物 | 順番 | 有効 | ヒント |
|---|---|---|---|---|---|---|---|---|
| `solomon` | ソロモン宙域 | SPACE | 0.35 | 0.15 | 環境の既定値 | 10 | ✅ | ビーム・高機動・長距離に強い機体が有利 |
| `southeast_asia_jungle` | 東南アジア密林 | FOREST | 0.6 | 0.15 | 環境の既定値 | 20 | ✅ | 格闘・索敵に強い機体が有利。長距離射撃は不利 |

`rotation_order` は間に戦域を追加できるように10刻みにしている。
値は運用しながら調整する（Issue #577 で初期値を設定し、森林を有効にした）。
作成済みの OPEN ルームの戦域は変わらず、次に作るルームから切り替わる。

> 本番DB（Neon）への投入・マイグレーションは書き込みになるため、実行前に確認を取る。
>
> 運用中の追加・調整は admin-tool の戦域・環境タイプの画面で行う（[admin-theaters.md](admin-theaters.md)）。

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

`backend/tests/test_theater_battle.py`

* 戦域なしのルームは宇宙・濃度0・障害物 `MEDIUM` で戦う
* 森林の戦域は環境タイプの効果・濃度・障害物密度の既定値（`DENSE`）で戦う。戦域が密度を指定すればそちらを使う
* 戦域・環境タイプのマスターが無ければ既定の条件で戦い、警告を出す
* 定期バトルのシミュレーターに条件を渡し、`BattleResult` に環境タイプ・戦域・濃度を記録する
* バトル結果の一覧・未読・詳細の API に戦域名・環境タイプ名・描画プリセットを含める

`backend/tests/test_theater_forecast.py`

* 濃度の段階のしきい値
* 今回はルームに保存した値、次回以降は開催日から計算した値を返す。`days` の既定値と範囲
* OPEN ルームが無ければ計算した値を返し、ルームを作らない
* 有効な戦域が無ければ空の配列
* 戦域の設定を変えると次回以降の予報だけが変わる
* 今回と次回の予報の戦域・濃度が、実際に開催した定期バトルの `BattleResult` の値と一致する

`frontend/tests/unit/theater.test.ts`: 戦域の表示名、BattleViewer に渡す環境、予報カードの表示（環境のアイコン、濃度の段階、地形適正、開催日）

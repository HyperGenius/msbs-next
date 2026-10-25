# 作戦ルーム — 作戦マスターの拡張と定期バッチでの実行

## 概要

作戦（`Mission`）を、デイリーバトルロイヤルと同じ「エントリー → 定期バッチ → 結果確認」の流れで遊べるようにする。
Epic #682「作戦（ミッション）と敵小隊のロール」の Sub-Issue 3（Issue #685）の範囲を記述する。

* 作戦マスターに作戦目標・友軍・配置・有効フラグを持たせる
* エントリー時に作戦を選ぶと、その開催・その作戦の専用ルーム（作戦ルーム）を作る
* 作戦ルームは NPC で埋めない。定期バッチが作戦マスターから敵・友軍・撤退ポイント・作戦目標を組み立てて実行する
* 作戦はその日の戦域（環境・ミノフスキー濃度・障害物密度）で戦う

即時実行の経路（`POST /api/battle/simulate`、開発環境の `DevSimulationPanel` 用）は変えない。
敵機の組み立てを共通の関数に移しただけで、作る機体は同じ。

### 今後の予定（Epic #682）

| Sub-Issue | 内容 |
|---|---|
| 1 | 作戦目標の基盤（Issue #683、実装済み。[battle-engine-feature.md 36章](battle-engine-feature.md#36-作戦目標epic-682-sub-issue-1)） |
| 2 | ユニット単位のロールと小隊の基盤（Issue #684、実装済み。[battle-engine-feature.md 37章](battle-engine-feature.md#37-ユニットのロールと小隊epic-682-sub-issue-2)） |
| 3 | 作戦マスターの拡張と作戦ルームのバッチ実行（Issue #685、本ドキュメント） |
| 4 | 撤退支援ミッション。撤退支援の作戦目標と作戦マスターのデータ（Issue #686、実装済み。[retreat-support-mission.md](retreat-support-mission.md)） |
| 5 | 作戦の選択と結果表示（フロントエンド、Issue #687、実装済み。[mission-frontend.md](mission-frontend.md)） |
| 6 | 小隊の陣形（Issue #688、実装済み。[battle-engine-feature.md 38章](battle-engine-feature.md#38-小隊の陣形epic-682-sub-issue-6)） |
| 7 | 支援ターゲット選択と戦術 SUPPORT / PROTECT（Issue #689） |

---

## データモデル

定義は `backend/app/models/models.py`。マイグレーションは `backend/alembic/versions/p1d2e3f4a5b6_add_mission_rooms.py`。
追加したカラムはすべて nullable（`is_active` は false）で、既存の行はそのまま読める。

### 作戦マスター（`missions` / `Mission`）

| 項目 | 型 | 説明 |
|---|---|---|
| `enemy_config` | JSON | 既存。`{"enemies": [MissionUnitConfig, ...]}`。各機にロールと小隊を書ける |
| `objective` | JSON / null | 追加。作戦目標（`MissionObjectiveConfig`）。null は殲滅 |
| `allies_config` | JSON / null | 追加。友軍（`MissionUnitConfig` のリスト）。null は友軍なし |
| `layout` | JSON / null | 追加。スポーン領域と撤退ポイント（`MissionLayout`）。null は既定の配置 |
| `is_active` | bool | 追加。定期バトルのエントリーで選べるか。既定 false |
| `environment` | str | 既存。戦域の無い開催で使う環境 |

JSON 列は Pydantic モデルで読む（`Mission.objective_config()` / `enemy_unit_configs()` / `ally_unit_configs()` / `layout_config()`）。

* `MissionObjectiveConfig`: `type`（既定 `ANNIHILATION`）と `params`（種類ごとの引数）。種類から作戦目標を作るのは `build_objective()`（`backend/app/engine/objectives.py`）。今ある種類は `ANNIHILATION` と `RETREAT_SUPPORT`（[retreat-support-mission.md](retreat-support-mission.md)）。無い種類は組み立て時に `ValueError` になる
* `MissionUnitConfig`: `name` / `max_hp` / `armor` / `mobility` / `position` / `terrain_adaptability` / `weapon`（`id` / `name` / `power` / `range` / `accuracy`）/ `role` / `squad_id`。省略した項目は既存の作戦と同じ既定値になる。`role` は `VALID_UNIT_ROLES` のいずれかで、無い値は組み立て時に `ValueError` になる。撤退支援で足した項目（`current_hp` / `missing_parts` / `max_speed` / `hold_fire` など）は [retreat-support-mission.md](retreat-support-mission.md#作戦マスターの定義の拡張)。機体マスター・エースの参照（`master_mobile_suit_id` / `ace_id` / `current_hp_ratio`）は [retreat-support-mission.md](retreat-support-mission.md#機体マスターエースの参照issue-719)
* `MissionLayout`: `field_size`（フィールドの辺長 (m)。null は参加機数から決める）、`spawn_zones`（`SpawnZone` のリスト）と `retreat_points`（`RetreatPoint` のリスト）。`team_id` には `PLAYER`（プレイヤーと友軍）か `ENEMY` を書く。撤退ポイントの `team_id` が null なら全チームが使える。それ以外の値は読み込み時にエラーにする

配置の座標は 0 から `field_size` の内側に置く。`field_size` が null のときはフィールドの最小辺長（`MIN_FIELD_SIZE`）の内側に置く。フィールドの広さが参加機数で変わり、それより外は場外になりうるため。
作戦の戦闘ではエリア収縮をしない（Issue #711）。
スポーン領域を書くときは `PLAYER` と `ENEMY` の両方を書く。書かなかったチームはスポーン領域で配置されない。

既存の3件（殲滅戦）は `objective` が null なので殲滅として読める。`is_active` は false のままなので、定期バトルでは選べない（作戦ルームの対象は #686 の撤退支援から）。
有効にするときは DB の `is_active` を true にする（マスターデータの正本は DB）。

### バトルルーム（`battle_rooms` / `BattleRoom`）

| 項目 | 型 | 説明 |
|---|---|---|
| `mission_id` | int / null (FK → `missions.id`) | 追加。作戦ID。null はデイリーバトルロイヤル |

作戦ルームは、同じ開催のバトルロイヤルのルームと同じ `scheduled_at` / `theater_id` / `minovsky_density` で作る。
`BattleRoomService.find_open_room()` はバトルロイヤルのルーム（`mission_id` が null）だけを返す。

### バトル結果（`battle_results` / `BattleResult`）

| 項目 | 型 | 説明 |
|---|---|---|
| `mission_id` | int / null | 既存。作戦ルームの結果に作戦IDを入れる |
| `objective_status` | str / null | 追加。作戦の結果（`SUCCESS` / `FAILURE` / `DRAW`） |
| `objective_progress` | int / null | 追加。達成した数（例: 離脱させた友軍の数） |
| `objective_required` | int / null | 追加。成功に必要な数。0 は達成度を数えない目標 |

* 定期バッチ（`run_batch.py`）は、バトルロイヤルの結果にも殲滅の結果を入れる
* ソロミッション（`main.py`）と導入前のバトルは null。フロントエンドは null のとき作戦の結果を表示しない（#687）
* `win_loss` は作戦の結果から決める（`SUCCESS` → `WIN`、`FAILURE` → `LOSE`、`DRAW` → `DRAW`）。殲滅は `DRAW` を返さないので、バトルロイヤルの勝敗は変わらない

---

## エントリー

1ユーザーが1開催に出られるのは、バトルロイヤルか作戦のどちらか1つ（Epic の検討事項の案「最初はどちらか1つ」を採用）。

### `POST /api/entries`

リクエストに `mission_id`（任意）を追加した。

| 状況 | 処理 |
|---|---|
| `mission_id` なし | 今どおりバトルロイヤルのルームに入る |
| `mission_id` あり | バトルロイヤルのルームと同じ開催の作戦ルームを作って入る |
| 無い作戦・`is_active` が false の作戦 | 404 |
| 同じ出撃先にエントリー済み | エントリーの機体を上書きする（ルームは作り直さない） |
| 別の出撃先にエントリー済み | 前のエントリーを消して入り直す。前が作戦ルームなら、そのルームも消す |

レスポンス（`EntryResponse`）に `mission_id` を追加した。null はバトルロイヤル。

### ほかのエンドポイント

| エンドポイント | 変更 |
|---|---|
| `GET /api/entries/status` | 作戦のエントリーも `entry` に返す（`mission_id` 付き）。`next_room` はバトルロイヤルのルーム |
| `DELETE /api/entries` | 作戦のエントリーもキャンセルできる。作戦ルームも消す |
| `GET /api/entries/count` | バトルロイヤルのルームのエントリー数だけを数える |
| `POST /api/teams/entry` | バトルロイヤルのルームに入る。作戦にエントリー済みのメンバーがいると 409 |

チームでの作戦参加は Epic の検討事項のまま。作戦ルームに入れるのはソロのエントリーだけ。

### `GET /api/missions/available`

次回の開催でエントリーできる作戦（`is_active` が true）と、その開催の戦域を返す。認証は不要。

```json
{
  "theater": { "theater_id": "southeast_asia_jungle", "environment_id": "FOREST", "...": "TheaterForecast と同じ" },
  "missions": [
    {
      "id": 4,
      "name": "撤退支援",
      "description": "...",
      "difficulty": 2,
      "objective_type": "ANNIHILATION",
      "objective_params": {},
      "environment": "FOREST",
      "ally_count": 2,
      "enemy_count": 4
    }
  ]
}
```

* `theater` は今回の開催の戦域予報（`TheaterForecastService.forecast()`）。戦域の無い開催は null
* `environment` は戦う環境。戦域があれば戦域の環境タイプ、無ければ `Mission.environment`

開発用の `GET /api/missions`（全件、`main.py`）は変えていない。

フロントエンドは `services/entry.ts` の `entryBattle(mobileSuitId, missionId)` で作戦IDを渡せる。作戦を選ぶ UI は #687。

---

## マッチング（`MatchingService.create_rooms()`）

| ルーム | エントリーあり | エントリーなし |
|---|---|---|
| バトルロイヤル | 今どおり。チームの味方配置と NPC の補填をして `WAITING` にする | 今どおり。開催予定時刻を過ぎていれば翌日に延期する |
| 作戦ルーム | NPC で埋めずに `WAITING` にする | 延期せずにルームを消す |

---

## バッチでの実行（`run_batch._process_room()`）

作戦ルームは次の手順で実行する。組み立ては DB を使わない `build_mission_battle()`（`backend/app/services/mission_battle.py`）が行う。

1. ルームの戦域から戦闘の条件を作る（`TheaterService.battle_conditions()`）。戦域の無い開催は `Mission.environment` で戦う
2. プレイヤー機を組み立てる。作戦ルームに NPC のエントリーは無い
3. 作戦マスターから友軍と敵機を作る
   * 機体が参照する機体マスターとエースを `load_mission_masters()`（`backend/app/services/mission_master_loader.py`）で DB から読み、`build_mission_battle(masters=...)` に渡す
   * 参照先が無い作戦は `ValueError` で組み立てに失敗する。バッチは警告を出して、そのルームを飛ばす（`WAITING` のまま残す）
   * プレイヤー機と友軍は、先頭のプレイヤー機のチームに入る
   * 敵機は全員で1チーム（`mission-{作戦ID}-enemy`）になる
   * `role` / `squad_id` を書いた機体は `UnitAssignment` にする
4. 配置の `PLAYER` / `ENEMY` を戦闘のチーム ID に置き換え、スポーン領域と撤退ポイントを作る。スポーン領域は戦域の障害物密度を残して差し替える
5. `run_battle()` に作戦目標・撤退ポイント・ロールを渡して実行する
6. `_save_battle_results()` で結果を保存する

作戦の敵機・友軍は `BattleEntry` にしない。`BattleResult.enemies_info` に戦闘後の状態で入るので、戦歴から再生できる。

`_save_battle_results()` の変更:

* プレイヤーのチームは、戦闘に渡した機体の `team_id` を使う（作戦ではプレイヤーと友軍が1チームになるため）。バトルロイヤルでは今までの `resolve_team_id()` と同じ値になる
* 作戦ルームの結果に `mission_id` と作戦の結果を入れる
* ドロップは作戦ルームなら `DropScope.mission(mission_id)`、バトルロイヤルは今どおり戦域か共通テーブル。作戦のドロップテーブルが無ければドロップしない
* 作戦ルームでエースを撃破すると、エースの懸賞金（`bounty_exp` / `bounty_credits`）を報酬に足す（`_mission_bounty()`）。バトルロイヤルのエースには払わない（今までどおり）

---

## 挙動が変わらないことの確認

* バトルロイヤルの戦闘は、撤退ポイントとロールを渡さないので今と同じ引数でシミュレーターを作る
* `run_battle()` を `main` と比べた（2 / 8 / 20 機 × シード 1〜3、`seed_battle_rngs()` とユニット ID・`PYTHONHASHSEED` を固定）。9 戦すべてでログのハッシュ・勝敗・撃墜数・ステップ数が一致した
* `engine_ci_smoke.py` は 9 ラウンド完走した

---

## テスト

* `backend/tests/unit/test_mission_battle.py`: 既存の作戦を殲滅として読む、ソロミッションの敵機が共通化前と同じ値になる、友軍・敵機のチームとロール、複数プレイヤーが同じチームに入る、配置のチームの置き換え、戦域が無いときの環境、無いチーム・ロール・作戦目標の拒否、`run_battle()` に作戦の設定が渡る
* `backend/tests/test_mission_rooms.py`: 作戦ID なしのエントリーはバトルロイヤル、作戦ルームの作成、無効な作戦の拒否、出撃先の切り替え、状況・キャンセル・待機人数、チームエントリーの 409、マッチング（NPC で埋めない・空の作戦ルームを消す）、作戦ルームの実行と結果の保存（作戦ID・作戦の結果・作戦の環境・ドロップの適用範囲）、バトルロイヤルと作戦ルームを同じバッチで実行する、作戦の一覧 API
* `frontend/tests/unit/entryService.test.ts`: `entryBattle()` が `mission_id` を送る

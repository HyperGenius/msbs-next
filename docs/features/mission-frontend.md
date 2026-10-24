# 作戦の選択と結果表示（フロントエンド）

## 概要

Epic #682 の Sub-Issue 5（Issue #687）。プレイヤーが次回バトルのエントリー時に作戦を選べるようにし、作戦の結果と、BattleViewer での撤退ポイント・友軍を表示する。
バックエンドの作戦ルーム（[mission-rooms.md](mission-rooms.md)）と撤退支援（[retreat-support-mission.md](retreat-support-mission.md)）は実装済みで、本 Issue は画面側。

## 作戦の選択

| ファイル | 内容 |
|---|---|
| `services/missions.ts` | `useAvailableMissions()`。`GET /api/missions/available`（認証不要）から、エントリーできる作戦と今回の戦域を取る |
| `components/Dashboard/MissionSelector.tsx` | 出撃先のカード一覧。デイリーバトルロイヤルと各作戦を縦に並べる（モバイル幅でも1列） |
| `components/Dashboard/EntryDashboard.tsx` | 未エントリー時に `MissionSelector` を出す。エントリー済みのときは出撃先（バトルロイヤルか作戦名）を表示する。作戦は専用ルームなので参加者数は出さない |
| `components/Dashboard/EntrySelectionModal.tsx` | 機体が複数あるときのモーダルに、出撃先の作戦名を出す |
| `hooks/useEntryAction.ts` | 選択中の作戦ID（`selectedMissionId`）を持ち、`entryBattle(mobileSuitId, missionId)` に渡す。一覧に無い作戦（無効化など）はバトルロイヤルとして扱う |

作戦カードには、作戦名・難易度・目的（`utils/missionName.ts` の `describeObjective()`）・説明文・今回の戦域（環境・ミノフスキー濃度）を出す。作戦が1件も無いときは選択欄を出さず、今までと同じ画面になる。

## 結果と戦歴

* `BattleResultModal`: 作戦の結果（`objective`）があると「作戦」欄に、作戦名、成功・失敗・引き分け、離脱数（`離脱 2/3（必要 2）`）、撃破された友軍の数を出す
* `/history`（`BattleList`）: 作戦ルームの結果に「作戦」、バトルロイヤルに「BR」のタグを付け、作戦の結果と離脱数を出す
* `utils/missionName.ts` の `getObjectiveSummary()` は、作戦ID があり作戦の結果が入っているときだけ値を返す。バトルロイヤルと、作戦の結果が null の既存の戦歴（`main.py` の開発用経路を含む）は null で、今までどおりの表示にする

## BattleViewer

| 表示 | 内容 |
|---|---|
| 撤退ポイント | 地面の破線の円と薄い塗り、「撤退ポイント」のラベル（`scene/RetreatPointMarker.tsx`）。色は既存パレットの `#6fe6ff`。ゆっくり点滅する |
| 友軍 | 自機と同じチームの機体。索敵に関わらず常に出す。自機の幅広・点滅のリング（`#4488ff`）に対して、細い実線のリングと「友軍」（撤退ロールは「友軍 撤退中」）のラベルで区別する。HP バー（HUD）と LOS の対象は敵だけ |
| 離脱 | `RETREAT_COMPLETE` のログで、その場に「↩ 離脱」を3秒かけて薄くしながら出し、友軍の機体を消す（`scene/RetreatCompleteNotice.tsx`、`utils/retreat.ts`）。ログ一覧にも出る（シアン系のスタイル） |

新しい色は使っていない（`frontend/CLAUDE.md` の配色パレットに追記）。

### バックエンドの変更

撤退ポイントとロールは結果に残っていなかったので、`BattleResult.objective_detail`（既存の JSON 列、マイグレーションなし）に次を足した。

```json
{
  "total": 3, "lost": 1, "player_survived": true,
  "retreat_points": [{ "position": {"x": 0, "y": 0, "z": 0}, "radius": 50, "team_id": "..." }],
  "unit_roles": { "<unit_id>": "WITHDRAW" }
}
```

`mission_battle.objective_result_fields()`（Issue #699 で `run_batch._objective_fields()` から移した。ローカルシミュレータも使う）が、シミュレーターの撤退ポイントとロールから組み立てる。撤退ポイントもロールも無いバトルロイヤルは従来どおり（殲滅で友軍を数えないので null）。
友軍かどうかは `enemies_info` の `team_id` が自機と同じかで判断する。

## テスト

* `frontend/tests/unit/missionUtils.test.ts`: 目的の文言、作戦の結果のまとめ（バトルロイヤルと結果なしは null）、離脱ログの集計
* `backend/tests/test_mission_rooms.py`: `objective_detail` に撤退ポイントとロールが入る

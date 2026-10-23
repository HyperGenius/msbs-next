# 撤退支援ミッション

## 概要

最初の作戦として「撤退支援」を作る。損傷した友軍の機体を撤退ポイントまで逃がし、追撃してくる敵小隊から守る。
離脱できた友軍の数で成功・失敗と報酬が決まる。Epic #682「作戦（ミッション）と敵小隊のロール」の Sub-Issue 4（Issue #686）の範囲を記述する。

敵を全滅させなくても勝てる作戦なので、殲滅向けの重い機体だけでなく、足止め・護衛・索敵に向いたビルドに出番ができる。
撤退ポイント・撤退ロール・作戦目標・作戦ルームの仕組みは既存のもの（[mission-rooms.md](mission-rooms.md)、[battle-engine-feature.md 36・37章](battle-engine-feature.md#36-作戦目標epic-682-sub-issue-1)）を使い、追加した仕組みは次の4つだけ。

* 作戦目標 `RETREAT_SUPPORT`（`RetreatSupportObjective`）
* 作戦マスターの1機の定義に、開始時の HP・欠損部位・武器種別を書けるようにした
* 達成度の内訳を `BattleResult.objective_detail` に保存する
* 報酬を離脱数に応じて段階的に出す

## 作戦マスター

定義は `backend/app/services/retreat_support_mission.py`（`build_retreat_support_mission()`、`missions.id = 4`）。

| 項目 | 内容 |
|---|---|
| 友軍 | 3 機（撤退ロール `WITHDRAW`）。HP 35 / 50 / 30（最大 90）で開始し、1 機は左腕、1 機は右脚が欠けている |
| 追撃部隊 | 敵チーム 4 機。前衛（`VANGUARD`、格闘）1 機と後衛（`SNIPER`、射程 600、威力 28）1 機で 1 小隊を組み、2 小隊（`pursuit-1` / `pursuit-2`）。狙撃機は前衛の後方に位置取る（陣形、[battle-engine-feature.md 38章](battle-engine-feature.md#38-小隊の陣形epic-682-sub-issue-6)）。支援ターゲット選択（#689）はまだ |
| 撤退ポイント | プレイヤーのチーム専用。友軍のスポーン位置から約 650m 離す |
| 作戦目標 | `RETREAT_SUPPORT`、`params.required = 2` |
| 説明文 | 目的（2 機以上の離脱で成功、全員で報酬増）と、有利な構成のヒントを出す |

プレイヤー機は友軍と同じスポーン領域（中心 x=-250）に出る。追撃部隊は x=300 付近から追ってくる（前衛の機動 1.9）。
数値は暫定で、調整は #587 にまとめる。

### 作戦マスターの定義の拡張

`MissionUnitConfig`（友軍・敵機の1機の定義）に次を足した。省略した値は今までと同じなので、既存の3件は変わらない。

| 項目 | 説明 |
|---|---|
| `current_hp` | 開始時の HP。null は `max_hp`。部位の HP も同じ割合まで減らす |
| `missing_parts` | 開始時に欠けている部位（`ALL_PART_NAMES`）。無い部位は組み立て時に `ValueError` |
| `weapon.weapon_type` / `is_melee` / `fire_arc_deg` | 格闘機を書くための武器の項目。既定は射撃武器 |

## 作戦目標 `RETREAT_SUPPORT`

`backend/app/engine/objectives.py` の `RetreatSupportObjective`。護衛する友軍は、作戦マスターの `allies_config` から作った機体の ID を `build_objective(..., protected_unit_ids)` で渡す。

| 項目 | 内容 |
|---|---|
| 終了 | 友軍が全員「離脱（`RETREATED`）」か「撃破」になる。または敵が全滅する |
| 敵が全滅したとき | 戦場に残る友軍は離脱したものとして数え、終了する |
| 結果 | 離脱数が `required` 以上で `SUCCESS`、未満で `FAILURE`。最大ステップ数で打ち切ったときも、その時点の離脱数で判定する |
| プレイヤー機が撃破・離脱したとき | 作戦は続く。友軍が逃げ切れば成功（報酬は減る） |
| 達成度 | `ObjectiveResult` の `progress`（離脱数）/ `required` / `total`（友軍の数）/ `lost`（撃破された友軍の数）/ `player_survived`（護衛対象を除く自チームの機体が残ったか） |

## 達成度の保存

`BattleResult.objective_progress` / `objective_required` に離脱数と必要数、新しい `objective_detail`（JSON）に内訳を入れる。

```json
{ "total": 3, "lost": 1, "player_survived": true }
```

殲滅など友軍を数えない目標では null。

BattleViewer 用に、撤退ポイントと友軍のロールも同じ列に入れる（#687。[mission-frontend.md](mission-frontend.md)）。マイグレーションは `q2e3f4a5b6c7_add_objective_detail.py`（nullable の追加のみ）。

## 報酬

`PilotService.calculate_battle_rewards(win, kills, objective_result)`。`objective_result.total` が 1 以上の作戦だけ、離脱数に応じた報酬にする。それ以外は今までどおり勝敗と撃墜数で決める。

| 結果 | 経験値 | クレジット |
|---|---|---|
| 全員離脱 | 150 | 750 |
| 必要数を満たした | 100 | 500 |
| 失敗 | 20 + 離脱数 × 10 | 100 + 離脱数 × 50 |

* 成功してもプレイヤー機が撃破・離脱していたら、基本報酬を 0.7 倍にする（`ESCORT_PLAYER_DOWN_RATIO`）
* 撃墜ボーナスは殲滅戦の半分（`ESCORT_KILL_REWARD_RATIO`）
* ドロップ（`DropScope.mission(作戦ID)`）は、成功したときだけ抽選する（既存の `is_win` の扱いのまま）

## 本番への反映

作戦マスターは DB が正本。`backend/scripts/maintenance/upsert_retreat_support_mission.py` で追加・更新する。

```bash
cd backend
uv run python scripts/maintenance/upsert_retreat_support_mission.py          # 差分の表示のみ
uv run python scripts/maintenance/upsert_retreat_support_mission.py --apply  # 書き込み（承認後に実行）
```

`--inactive` を付けると `is_active` を false で入れる。先にマイグレーション（`alembic upgrade head`）を当てること。

## 検証

`backend/scripts/simulation/retreat_support_bench.py`（DB 不要）で、同程度の戦力の3ビルド（殲滅向け・中間・機動/索敵寄り）を、撤退支援と、同じ友軍・敵小隊の殲滅戦で比べる。

```bash
cd backend
uv run python scripts/simulation/retreat_support_bench.py --rounds 60
```

## 計測結果

3000 ステップ（定期バトルの上限）、30 ラウンド、`seed` 1〜30。

| 目標 | ビルド | 成功率 | 時間切れ | 平均離脱数 | プレイヤー機の生存 |
|---|---|---|---|---|---|
| 撤退支援 | 殲滅向け | 97% | 0% | 2.30 | 47% |
| 撤退支援 | 中間 | 90% | 0% | 2.40 | 37% |
| 撤退支援 | 機動・索敵寄り | 87% | 0% | 2.13 | 33% |
| 殲滅戦 | 殲滅向け | 17% | 0% | - | 17% |
| 殲滅戦 | 中間 | 0% | 0% | - | 0% |
| 殲滅戦 | 機動・索敵寄り | 0% | 0% | - | 0% |

* 殲滅戦（友軍と 4 機の追撃部隊をまとめて倒す）では機動・索敵寄りの成功率は 0% だが、撤退支援では 87% になる。殲滅向けとの差も、17 → 10 ポイントに縮まる。倒さなくても勝てる作戦になっている
* 時間切れで終わった戦闘は 0%。友軍が離脱か撃破になるか、敵が全滅して終わる
* **撤退支援は全ビルドで成功率が高く（87〜97%）、機動・索敵寄りが殲滅向けを上回るところまでは届いていない**。足止め・索敵に価値が出る難易度にするのは、#587（総合バランス調整）で行う。必要数を 3 に上げる、追撃部隊を増やす、友軍の HP を下げる、などで調整する
* ベンチのビルドは合成した 3 種で、本番のマスターの機体ではない

陣形（#688）を入れた後の計測は [battle-engine-feature.md 38.6](battle-engine-feature.md#386-計測) にある。

## テスト

* `backend/tests/unit/test_objectives.py`: 終了条件（友軍が残る間は続く、全員離脱か撃破で終える、敵の全滅で終える）、成功・失敗、プレイヤー機が撃破されても成功、敵が全滅したとき残る友軍の数え方、不正な引数の拒否、`build_objective()`
* `backend/tests/unit/test_mission_battle.py`: 撤退支援のマスターから組み立てる（損傷した友軍・欠損部位・ロール・専用の撤退ポイント・目標）、無い部位の拒否、最後まで実行できる
* `backend/tests/unit/test_pilot_service.py`: 段階的な報酬、プレイヤー機の撃破による減額と撃墜ボーナス、殲滅の結果を渡しても変わらない

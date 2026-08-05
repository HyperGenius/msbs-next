# Battle History ダイジェスト仕様書

## 概要

Battle History 一覧（`/history`）は従来「ミッション名 / WIN-LOSE-DRAW / 日時」のみを機械的に列挙していた。
バトル終了時に一度だけ戦闘ログを集計し、ルールベースでタグ付け→テンプレートプールから一言ログを選択することで、
一覧を戦闘のダイジェスト（結果・撃破数・被弾状況・搭乗機体・一言ログ）として表示する（Issue #415）。

LLM等の外部呼び出しは行わない、完全ルールベースの実装。

---

## データフロー

```
main.py（ソロバトル実行, POST /api/battle 相当）
  └─ sim.step() ループ実行（steps_used をカウント）
  └─ 勝敗・kills 確定
  └─ compute_digest_stats(player, sim.logs, kills, win_loss, steps_used, max_steps)
        → DigestStats（被弾回数・最大一撃・回避回数 等の集計値）
  └─ build_digest(stats, avoid_text)
        → determine_tag(stats) でタグ判定
        → TEMPLATE_POOLS[tag] からランダム選出（直前の一言ログと同一なら除外）
  └─ BattleResult に digest_tag / digest_text 等を保存
```

集計・タグ判定・テンプレート選択はすべて `backend/app/engine/battle_digest.py` に実装されている。

HPは回復要素がない（`simulation.py`/`combat.py` に repair 処理なし）ため、バトル終了時の `player.current_hp` が
そのままバトル中の最低到達HPと一致する前提で `min_hp_percent` を計算している。

---

## BattleResult の追加カラム

いずれも nullable。マイグレーション前の既存レコードは全カラム `NULL` のままで、バックフィルは行わない
（フロントエンドは `digest_text == null` の場合に旧表示へフォールバックする）。

| カラム | 型 | 説明 |
|---|---|---|
| `player_survived` | bool | 生還したか（撃墜されなかったか） |
| `min_hp_percent` | int | バトル中の最低到達HP割合 (%) |
| `damage_severity` | str | 被弾ランク: 無傷/軽微/中破/大破/撃墜 |
| `damage_taken_count` | int | 被弾回数（ATTACK/MELEE_COMBOで自機がtarget） |
| `max_hit_damage` | int | 自機が与えた一撃の最大ダメージ（絶対値） |
| `dodge_count` | int | 回避回数（MISSで自機がtarget） |
| `attacks_received_count` | int | 被攻撃回数（`damage_taken_count + dodge_count`） |
| `pilot_ms_name` | str | 搭乗機体名 |
| `digest_tag` | str | 判定されたダイジェストタグ |
| `digest_text` | str | 生成された一言ログ |

## マイグレーション

`backend/alembic/versions/v5w6x7y8z9a0_add_battle_digest_fields.py`（head: `u4v5w6x7y8z9` → `v5w6x7y8z9a0`）。

---

## タグ判定ルールと優先度

`determine_tag()` で判定。**WIN** の場合のみ以下の優先度リストを上から評価し、最初に該当した1つを採用する
（定数は `battle_digest.py` 冒頭に集約。閾値は初期見積もりであり、実プレイの分布を見て調整する前提）。

| 優先度 | タグ | 条件 | 定数 |
|---|---|---|---|
| 1 | 辛勝 | `min_hp_percent < 20` | `SHINSHOU_HP_THRESHOLD` |
| 2 | 完封 | `damage_taken_count == 0` | — |
| 3 | 殲滅 | `kills >= 5` | `ZENMETSU_KILLS_THRESHOLD` |
| 4 | 一撃必殺 | 自機の一撃で `damage / target_max_hp >= 0.4` | `ISSEKI_DAMAGE_RATIO_THRESHOLD` |
| 5 | 長期戦 | `steps_used / max_steps >= 0.7` | `CHOUKISEN_STEP_RATIO_THRESHOLD` |
| 6 | 回避特化 | `attacks_received_count >= 3` かつ `dodge_count / attacks_received_count >= 0.5` | `KAIHI_MIN_ATTACKS` / `KAIHI_DODGE_RATIO_THRESHOLD` |
| — | 通常 | 上記いずれにも該当しない場合のフォールバック | — |

**LOSE**: `kills >= 1` → 「力戦及ばず」、`kills == 0` → 「完敗」。
**DRAW**: 常に「痛み分け」。

---

## テンプレートプール

`battle_digest.py` の `TEMPLATE_POOLS: dict[str, list[str]]` にタグごと3〜5パターン定義。
プレースホルダーは `{ms_name}`（搭乗機体名）/`{min_hp}`（最低到達HP%）/`{kills}`（撃破数）/`{weapon_name}`（最頻出使用武器、無ければ「武装」）/`{max_hit_damage}`（最大一撃ダメージ）。

「直近未使用優先」は、同一ユーザーの直前の `BattleResult.digest_text` を1件だけ取得し（`user_id` があれば）、
同じ文言がプール内に複数候補ある場合はそれを除外してからランダム選出する軽量な実装（専用テーブルは持たない）。

---

## フロントエンド表示

`frontend/src/components/history/BattleList.tsx` の1行表示:

```
[ミッション名]                                    [WIN/LOSE/DRAW]
生還 / 撃破: 3機 / 被弾: 中破 / 搭乗機: Gelgoog
「敵ビームライフルの弾幕を掻い潜り、接近戦に持ち込んだ」
[日時]
```

`digest_text` が `null`（マイグレーション前の既存レコード）の場合は、ミッション名を主表示に戻す従来レイアウトにフォールバックする。

---

## 関連ファイル

| ファイル | 役割 |
|---|---|
| `backend/app/engine/battle_digest.py` | 集計・タグ判定・テンプレート選択のロジック本体 |
| `backend/app/models/models.py` | `BattleResult`/`BattleResultSummary` のカラム定義 |
| `backend/alembic/versions/v5w6x7y8z9a0_...py` | マイグレーション |
| `backend/main.py` | バトル終了時にダイジェストを計算し保存する呼び出し元 |
| `backend/tests/unit/test_battle_digest.py` | タグ判定・テンプレート生成の単体テスト |
| `frontend/src/types/battleCore.ts` | `BattleResult` 型への追加フィールド |
| `frontend/src/components/history/BattleList.tsx` | 一覧表示 |

# 定期実行ジョブ仕様 (run_batch.py)

## 概要

`backend/scripts/run_batch.py` は定期的に実行されるバッチスクリプトです。
マッチング・シミュレーション・報酬付与・ランキング更新・次回ルーム作成を一括で行います。

## 処理フロー

```
フェーズ1: マッチング
  └─ OPEN ルームのエントリーをグループ化し、不足分を NPC で補充
フェーズ2: シミュレーション
  └─ WAITING ルームで戦闘シミュレーションを実行 → 結果保存
フェーズ3: ランキング更新
  └─ バトル結果を集計してランキングテーブルを更新
フェーズ4: 次回ルーム作成
  └─ 既存 OPEN ルームがなければ翌日 21:00 JST 開始のルームを作成
```

## 主要関数

### `run_matching_phase(session)`

`MatchingService.create_rooms()` を呼び出し、エントリー済みプレイヤーをルームに割り当てます。
不足分は NPC エントリーで自動補充されます。

### `run_simulation_phase(session)`

`WAITING` 状態のルームを全件取得し、各ルームに対して `_process_room` を呼び出します。
個別ルームの処理でエラーが発生しても、他ルームの処理は継続されます。

### `_process_room(session, room)`

1. ルームのエントリーを取得し、プレイヤーと NPC に分類
2. `_prepare_battle_units` でシミュレーション用ユニットを構築
3. `_run_simulation` で戦闘を実行
4. `_save_battle_results` で結果・報酬・パイロット成長を保存

### `_save_battle_results(session, room, player_entries, npc_entries, simulator, ...)`

各プレイヤーエントリーに対して以下を順番に実行します：

1. **パイロット情報取得**: `PilotService.get_or_create_pilot` でパイロットを取得または新規作成し、`level_before` を記録
2. **報酬計算**: `PilotService.calculate_battle_rewards(win, kills)` で獲得 EXP・クレジットを算出
3. **報酬付与**: `PilotService.add_rewards` でパイロットデータを更新し、`level_after` を確定
4. **BattleResult 保存**: 詳細フィールドをすべてセットして `battle_results` テーブルに保存

パイロット更新と BattleResult 保存は同一 `session` 内で処理され、`session.commit()` で一括コミットされます。

### `create_next_open_room(session)`

既存の `OPEN` ルームがない場合、次の 21:00 JST（= 12:00 UTC）を `scheduled_at` とした新規ルームを作成します。

### `update_rankings(session)`

`RankingService.calculate_ranking()` を呼び出してランキングを再集計します。

## トランザクション設計

- パイロットデータの更新（`pilots` テーブル）と `BattleResult` の保存（`battle_results` テーブル）は同一セッション内で処理されます。
- `_save_battle_results` の末尾で `session.commit()` を一度だけ呼び出すことで、原子性を保証します。
- 報酬付与でエラーが発生した場合は警告ログを出力しつつ、そのプレイヤー分は `exp_gained = 0` などのデフォルト値で BattleResult が保存されます。

## 実行方法

```bash
# ローカル実行
cd backend
python scripts/run_batch.py

# 環境変数（必須）
NEON_DATABASE_URL=postgresql://...
CLERK_JWKS_URL=https://...
CLERK_SECRET_KEY=...
```

## 関連ドキュメント

- [BATTLE_RESULT.md](./BATTLE_RESULT.md) — バトル結果詳細フィールド仕様
- [BATCH_SYSTEM.md](../BATCH_SYSTEM.md) — バッチシステム全体アーキテクチャ

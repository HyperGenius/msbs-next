# バトル結果詳細仕様 (BattleResult)

## 概要

`battle_results` テーブルはバトル終了後にプレイヤーへ表示する詳細情報を保持します。
ログイン時の報酬モーダルや戦績画面で参照されます。

## フィールド一覧

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `id` | UUID | auto | 主キー |
| `user_id` | str \| null | null | Clerk User ID |
| `mission_id` | int \| null | null | ミッションID（ミッション戦の場合） |
| `room_id` | UUID \| null | null | バトルルームID（定期バトルの場合） |
| `win_loss` | str | — | 勝敗 (`WIN` / `LOSE` / `DRAW`) |
| `logs` | list | `[]` | バトルログ（ターンごとのイベント） |
| `environment` | str | `SPACE` | 戦闘環境 (`SPACE` / `GROUND` / `COLONY` / `UNDERWATER`) |
| `player_info` | dict \| null | null | プレイヤー機体スナップショット（シミュレーション実行時） |
| `enemies_info` | list \| null | null | 敵機体スナップショットリスト |
| `ms_snapshot` | dict \| null | null | **エントリー時点**の機体データスナップショット |
| `kills` | int | `0` | 撃墜数 |
| `exp_gained` | int | `0` | 獲得経験値 |
| `credits_gained` | int | `0` | 獲得クレジット |
| `level_before` | int | `0` | バトル前のパイロットレベル |
| `level_after` | int | `0` | バトル後のパイロットレベル |
| `level_up` | bool | `False` | レベルアップが発生したかどうか |
| `is_read` | bool | `False` | 既読フラグ（モーダル表示済みで `True` に更新） |
| `created_at` | datetime | now (UTC) | 作成日時 |

## `ms_snapshot` の不変性

`ms_snapshot` にはエントリー登録時点（`BattleEntry.mobile_suit_snapshot`）のデータが保存されます。
シミュレーション中に機体のパラメータが変化しても `ms_snapshot` は変わらず、
プレイヤーが「どの機体でどのバトルに参加したか」を正確に記録します。

## 報酬フィールドの設定タイミング

定期実行バッチ（`run_batch.py`）では、`BattleResult` 保存前に以下の順序で処理されます：

```
1. pilot = PilotService.get_or_create_pilot(user_id)
2. level_before = pilot.level
3. exp_gained, credits_gained = PilotService.calculate_battle_rewards(win, kills)
4. pilot, logs = PilotService.add_rewards(pilot, exp_gained, credits_gained)
5. level_after = pilot.level
6. level_up = level_after > level_before
7. BattleResult(..., level_before, level_after, level_up, ...) を保存
```

これにより `level_before` / `level_after` が確定した状態で `BattleResult` が作成されます。

## 後方互換性

過去バッチ（詳細フィールド追加前）で作成されたレコードは `ms_snapshot` 等が `NULL` になります。
フロントエンドのモーダルコンポーネントは `ms_snapshot` が `NULL` の場合でもエラーにならず、
スナップショット非表示の `WinNoSnapshot` ストーリーと同様の表示にフォールバックします。

## 関連ドキュメント

- [RUN_BATCH.md](./RUN_BATCH.md) — 定期実行ジョブ仕様
- [BATCH_SYSTEM.md](../BATCH_SYSTEM.md) — バッチシステム全体アーキテクチャ

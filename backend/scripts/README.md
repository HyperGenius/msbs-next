# backend/scripts

バックエンドの開発・運用補助スクリプト群です。
用途に応じて以下のサブディレクトリに分類されています。


## run_batch.py

定期実行バッチスクリプト。マッチング・シミュレーション・ランキング更新・次回ルーム作成を一括で実行します。

### 実行方法

```bash
cd backend
source .venv/bin/activate
NEON_DATABASE_URL=<接続文字列> python scripts/run_batch.py
```

### 必須環境変数

| 変数名 | 説明 |
|---|---|
| `NEON_DATABASE_URL` | NeonデータベースへのURL |

### オプション環境変数（Cloud Run Jobs 並列実行用）

| 変数名 | デフォルト | 説明 |
|---|---|---|
| `CLOUD_RUN_TASK_INDEX` | `0` | タスクインデックス |
| `CLOUD_RUN_TASK_COUNT` | `1` | 並列タスク総数 |

### 処理フロー

```
フェーズ1: マッチング
  └─ OPENルームのエントリーをグループ化し、不足分をNPCで補充

フェーズ2: シミュレーション
  └─ WAITING状態の各ルームでBattleSimulatorを実行し戦闘結果を保存
     └─ パイロットへ経験値・クレジット報酬を付与
     └─ ルームステータスをCOMPLETEDに更新

フェーズ3: ランキング更新
  └─ BattleResultを集計してRankingServiceでランキングを再計算

フェーズ4: 次回バトル用ルーム作成
  └─ OPENルームが存在しない場合、次の21:00 JST (12:00 UTC) を予定時刻として新規作成
```

### 主な関数

| 関数 | 説明 |
|---|---|
| `run_matching_phase()` | マッチングフェーズ（`MatchingService.create_rooms()` を呼び出し） |
| `run_simulation_phase()` | WAITINGルームの一覧を取得して各ルームを処理 |
| `_process_room()` | 1ルームの戦闘シミュレーション・結果保存を実行 |
| `update_rankings()` | `RankingService.calculate_ranking()` でランキングを更新 |
| `create_next_open_room()` | 翌サイクル用のOPENルームを作成 |

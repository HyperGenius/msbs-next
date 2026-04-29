# backend/scripts

バックエンドの開発・運用補助スクリプト群です。

---

## run_simulation.py

本番DBにReadOnly接続してミッションシミュレーションをローカル実行し、結果をJSONファイルに出力するスクリプトです。  
DBへの書き込みは一切行いません。

### 前提条件

- `backend/.venv` が有効化されていること
- `.env` に `NEON_DATABASE_URL`（本番DB接続文字列）が設定されていること

### 使い方

```bash
# カレントディレクトリを backend/ にして実行
cd backend

# 基本実行（出力ファイル名は自動生成）
python scripts/run_simulation.py --mission-id 1

# 出力先ファイルを指定
python scripts/run_simulation.py --mission-id 1 --output results/m1.json

# 最大ステップ数を指定（デフォルト: 5000）
python scripts/run_simulation.py --mission-id 1 --output results/m1.json --steps 500
```

### オプション

| オプション | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `--mission-id` | ✅ | — | 実行するミッションのID |
| `--output` | — | 自動生成 | 結果JSONの出力先ファイルパス |
| `--steps` | — | `5000` | 最大ステップ数（時間ステップ制） |

### 出力 JSON の構造

```json
{
  "mission_id": 1,
  "mission_name": "ミッション名",
  "environment": "SPACE",
  "win_loss": "WIN | LOSE | DRAW",
  "elapsed_time": 42.3,
  "step_count": 423,
  "kills": 2,
  "player": { "name": "ガンダム", "final_hp": 50, "max_hp": 100 },
  "enemies": [ { "name": "ザクII", "final_hp": 0, "max_hp": 80 } ],
  "logs": [ ... ]
}
```

`logs` 配列には `BattleLog`（`timestamp` ベースの新スキーマ）が含まれます。  
BattleViewer で読み込むことで戦闘を目視確認できます。

---

## clear_battle_results.py

`battle_results` テーブルのデータを削除するスクリプトです。  
バトルログのスキーマ変更など後方互換性がなくなった際に使用します。

> ⚠️ **破壊的操作です。本番DBに対して実行する場合は十分に注意してください。**

### 使い方

```bash
cd backend

# 削除対象件数を確認するだけ（実際には削除しない）
python scripts/clear_battle_results.py --dry-run

# 全件削除（確認プロンプトあり）
python scripts/clear_battle_results.py

# 確認プロンプトをスキップして全件削除
python scripts/clear_battle_results.py --yes

# 特定ユーザーの結果のみ削除
python scripts/clear_battle_results.py --user-id user_xxxxxxxxxxxx
```

### オプション

| オプション | 説明 |
|---|---|
| `--dry-run` | 削除対象件数を表示するだけで実際には削除しない |
| `--user-id USER_ID` | 削除対象を特定の Clerk User ID に絞り込む |
| `--yes` / `-y` | 確認プロンプトをスキップして即座に削除を実行 |

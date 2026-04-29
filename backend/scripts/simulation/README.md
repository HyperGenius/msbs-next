# run_simulation.py

本番DBにReadOnly接続してミッションシミュレーションをローカル実行し、結果をJSONファイルに出力するスクリプトです。  
DBへの書き込みは一切行いません。

## 前提条件

- `backend/.venv` が有効化されていること
- `.env` に `NEON_DATABASE_URL`（本番DB接続文字列）が設定されていること

## 使い方

```bash
# カレントディレクトリを backend/ にして実行
cd backend

# 基本実行（出力ファイル名は自動生成）
python scripts/simulation/run_simulation.py --mission-id 1

# 出力先ファイルを指定
python scripts/simulation/run_simulation.py --mission-id 1 --output results/m1.json

# 最大ステップ数を指定（デフォルト: 5000）
python scripts/simulation/run_simulation.py --mission-id 1 --output results/m1.json --steps 500
```

## オプション

| オプション | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `--mission-id` | ✅ | — | 実行するミッションのID |
| `--output` | — | 自動生成 | 結果JSONの出力先ファイルパス |
| `--steps` | — | `5000` | 最大ステップ数（時間ステップ制） |

## 出力 JSON の構造

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

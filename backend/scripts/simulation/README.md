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

---

# local_sim（ローカルバトルシミュレータ）

本番の参加機体を Read Only で取得し、ローカルでバトルを実行するツールです。
接続には `NEON_DATABASE_URL` ではなく `NEON_READONLY_DATABASE_URL`（SELECT 権限だけのロール）を使います。

```bash
cd backend
python -m scripts.simulation.local_sim check-readonly          # 書き込みが拒否されることを確認
python -m scripts.simulation.local_sim fetch --pilot user_xxx --npc 7
python -m scripts.simulation.local_sim run --roster <ロスター名> --rounds 20 --seed 611   # DB に接続しない
python -m scripts.simulation.local_sim list                    # 保存した世代の一覧
python -m scripts.simulation.local_sim pin <世代>               # 世代管理で削除しないようにする
python -m scripts.simulation.local_sim report <世代>            # 勝敗・戦闘時間・行動分布・機体ごとの撃墜数を集計
python -m scripts.simulation.local_sim compare <世代A> <世代B>   # 2つの世代の集計値と差を表示
```

詳細は `docs/features/local-battle-simulator.md` を参照してください。

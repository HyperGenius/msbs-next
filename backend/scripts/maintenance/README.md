# clear_battle_results.py

`battle_results` テーブルのデータを削除するスクリプトです。  
バトルログのスキーマ変更など後方互換性がなくなった際に使用します。

> ⚠️ **破壊的操作です。本番DBに対して実行する場合は十分に注意してください。**

## 使い方

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

## オプション

| オプション | 説明 |
|---|---|
| `--dry-run` | 削除対象件数を表示するだけで実際には削除しない |
| `--user-id USER_ID` | 削除対象を特定の Clerk User ID に絞り込む |
| `--yes` / `-y` | 確認プロンプトをスキップして即座に削除を実行 |

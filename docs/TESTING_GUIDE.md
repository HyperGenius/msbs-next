### Frontendテスト

フロントエンドのユニットテストには `Vitest` を使用し、E2Eテストには `Playwright` を使用します。

```bash
cd frontend

# ユニットテストの実行（1回のみ実行）
npx vitest run

# 特定のテストファイルのみを実行（例: logFormatter のテスト）
npx vitest run tests/unit/logFormatter.test.ts

# テストを監視モードで起動（コード変更時に自動再実行）
npx vitest

# UIモードでテスト結果をブラウザ確認
npx vitest --ui

# E2Eテスト（準備中）
npm run test:e2e
```

### Backendテスト
バックエンドのユニットテストには `pytest` を使用します。

```bash
cd backend
# ユニットテストの実行
pytest

# 特定のテストファイルのみを実行（例: test_battle.py）
pytest tests/unit/test_battle.py

# テストを詳細モードで実行
pytest -v

# テストカバレッジの測定
pytest --cov=app tests/unit
```

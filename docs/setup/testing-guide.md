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

### CI と pre-commit

frontend・admin-tool・backend の静的解析とテストは、CI と pre-commit の両方で実行します。
CI が必須の関門です。pre-commit は `--no-verify` で飛ばせるため、コミット前に早く気付くための補助です。

| 対象 | CI（GitHub Actions） | pre-commit |
|---|---|---|
| frontend | `frontend-ci.yaml`: ESLint（警告も失敗）、`tsc --noEmit`、Vitest（`unit` プロジェクト） | ESLint（ステージしたファイル、警告も失敗） |
| admin-tool | `frontend-ci.yaml`: ESLint（エラーのみ失敗）、`tsc --noEmit`、Vitest | ESLint（ステージしたファイル、エラーのみ失敗） |
| backend | `backend-ci.yaml`: Ruff、mypy、pytest | Ruff、mypy |

* `frontend-ci.yaml` は PR ごとに常に起動します。変更の無いディレクトリのジョブはスキップされ、成功として扱われます（Branch protection で必須チェックにしても、対象外の PR が止まらないようにするため）。
* admin-tool は、react-hook-form の `watch()` で `react-hooks/incompatible-library` の警告が残っているため、警告では失敗にしません。
* frontend の Vitest の `storybook` プロジェクトはブラウザ（Playwright）が要るため、CI では実行しません。

pre-commit の ESLint は、各ディレクトリにインストール済みの ESLint を使います。事前に `npm install` を実行してください。

```bash
# フックのインストール（初回のみ）
pre-commit install

# 全ファイルに対して手動で実行
pre-commit run --all-files
```

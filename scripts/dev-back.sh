#!/usr/bin/env bash
# バックエンド（FastAPI）を起動するスクリプト
# 使い方: ./scripts/dev-back.sh
set -euo pipefail

# スクリプトの場所からリポジトリルートを算出
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO_ROOT/backend"

# uv run は起動前に .venv を uv.lock と同期する。
exec uv run uvicorn main:app --reload

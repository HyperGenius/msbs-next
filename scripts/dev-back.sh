#!/usr/bin/env bash
# バックエンド（FastAPI）を起動するスクリプト
# 使い方: ./scripts/dev-back.sh
set -euo pipefail

# スクリプトの場所からリポジトリルートを算出
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO_ROOT/backend"

# Python 仮想環境を有効化
source .venv/bin/activate

# uvicorn でホットリロードを有効にして起動
exec uvicorn main:app --reload

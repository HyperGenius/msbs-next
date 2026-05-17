#!/usr/bin/env bash
# フロントエンド（Next.js）を起動するスクリプト
# 使い方: ./scripts/dev-front.sh
set -euo pipefail

# スクリプトの場所からリポジトリルートを算出
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO_ROOT/frontend"

# Next.js 開発サーバーを起動
exec npm run dev

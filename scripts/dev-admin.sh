#!/usr/bin/env bash
# 管理ツール（admin-tool, ポート3100）を起動するスクリプト
# 使い方: ./scripts/dev-admin.sh
set -euo pipefail

# スクリプトの場所からリポジトリルートを算出
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO_ROOT/admin-tool"

# Next.js 開発サーバーを起動（ポート3100）
exec npm run dev

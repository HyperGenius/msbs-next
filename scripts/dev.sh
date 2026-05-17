#!/usr/bin/env bash
# フロントエンドとバックエンドを並列で起動するスクリプト
# 使い方: ./scripts/dev.sh
# Ctrl+C で両プロセスをまとめて停止する
set -euo pipefail

# スクリプトの場所からリポジトリルートを算出
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# EXIT シグナル時にプロセスグループ全体を終了（Ctrl+C で両方止まる）
cleanup() {
  kill 0
}
trap cleanup EXIT

bash "$REPO_ROOT/scripts/dev-back.sh" &   # バックエンドをバックグラウンドで起動
bash "$REPO_ROOT/scripts/dev-front.sh" &  # フロントエンドをバックグラウンドで起動

# 両プロセスが終了するまで待機
wait

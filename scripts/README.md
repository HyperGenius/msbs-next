# scripts

開発用シェルスクリプト集。リポジトリルートから実行してください。

## スクリプト一覧

| スクリプト | 説明 |
|---|---|
| `dev.sh` | フロントエンドとバックエンドを同時起動 |
| `dev-front.sh` | フロントエンド（Next.js）のみ起動 |
| `dev-back.sh` | バックエンド（FastAPI）のみ起動 |

## 使い方

```bash
# 両方同時に起動（Ctrl+C で両方停止）
./scripts/dev.sh

# 個別に起動する場合
./scripts/dev-front.sh
./scripts/dev-back.sh
```

## 事前準備

バックエンドの初回起動前に Python 仮想環境のセットアップが必要です。

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

# Cloud Run用Dockerfile
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.20 /uv /bin/uv

# 作業ディレクトリを設定
WORKDIR /app

# イメージの python を使う。uv に別の Python を取得させない。
ENV UV_PYTHON_DOWNLOADS=0 \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1

# 依存関係をコピーしてインストール
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# アプリケーションコードをコピー
COPY . .

ENV PATH="/app/.venv/bin:$PATH"

# ポート8080で起動（Cloud Runのデフォルト）
ENV PORT=8080

# Uvicornでアプリケーションを起動
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

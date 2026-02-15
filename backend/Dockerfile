# Cloud Run用Dockerfile
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ポート8080で起動（Cloud Runのデフォルト）
ENV PORT=8080

# Uvicornでアプリケーションを起動
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
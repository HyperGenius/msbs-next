# デプロイガイド

このドキュメントでは、MSBS-NextをVercel（フロントエンド）とCloud Run（バックエンド）にデプロイする手順を説明します。

## 前提条件

- Google Cloud Platform (GCP) アカウント
- Vercel アカウント
- Neon PostgreSQL（本番用データベース）
- Clerk アカウント（認証設定）

## 1. バックエンド（Cloud Run）のデプロイ

### 1.1. Dockerイメージのビルドとプッシュ

```bash
cd backend

# Google Cloud プロジェクトを設定
export PROJECT_ID=your-gcp-project-id
export REGION=asia-northeast1
export SERVICE_NAME=msbs-next-api

# Artifact Registry にリポジトリを作成（初回のみ）
gcloud artifacts repositories create msbs-next \
  --repository-format=docker \
  --location=${REGION} \
  --description="MSBS-Next Docker repository"

# Dockerイメージをビルド
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/msbs-next/${SERVICE_NAME}
```

### 1.2. Cloud Run へデプロイ

```bash
gcloud run deploy ${SERVICE_NAME} \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/msbs-next/${SERVICE_NAME} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=your_neon_connection_string" \
  --set-env-vars "CLERK_SECRET_KEY=your_clerk_secret_key" \
  --set-env-vars "CLERK_JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json" \
  --set-env-vars "ALLOWED_ORIGINS=https://your-app.vercel.app"
```

デプロイ後、Cloud Run のサービスURLが表示されます（例: `https://msbs-next-api-xxxxx.run.app`）

### 1.3. 環境変数の更新（必要に応じて）

```bash
gcloud run services update ${SERVICE_NAME} \
  --region ${REGION} \
  --set-env-vars "ALLOWED_ORIGINS=https://your-app.vercel.app,https://your-app-preview.vercel.app"
```

## 2. データベース（Neon）のセットアップ

### 2.1. Neon プロジェクトの作成

1. [Neon Console](https://console.neon.tech/)にログイン
2. 新規プロジェクトを作成
3. 接続文字列を取得（例: `postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname`）

### 2.2. マイグレーションの実行

```bash
cd backend

# 環境変数を設定
export DATABASE_URL="your_neon_connection_string"

# マイグレーションを実行
alembic upgrade head

# シードデータの投入
python scripts/seed.py
```

## 3. フロントエンド（Vercel）のデプロイ

### 3.1. Vercel プロジェクトの作成

```bash
cd frontend

# Vercel CLI のインストール（未インストールの場合）
npm i -g vercel

# Vercelにログイン
vercel login

# デプロイ
vercel
```

### 3.2. 環境変数の設定

Vercel のダッシュボード、または CLI で環境変数を設定：

```bash
# Production 環境
vercel env add NEXT_PUBLIC_API_URL production
# 値: https://msbs-next-api-xxxxx.run.app (Cloud RunのURL)

vercel env add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY production
# 値: your_clerk_publishable_key

vercel env add CLERK_SECRET_KEY production
# 値: your_clerk_secret_key

# Preview 環境（オプション）
vercel env add NEXT_PUBLIC_API_URL preview
vercel env add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY preview
vercel env add CLERK_SECRET_KEY preview
```

### 3.3. 本番デプロイ

```bash
vercel --prod
```

## 4. Clerk の設定更新

### 4.1. 本番ドメインの追加

1. [Clerk Dashboard](https://dashboard.clerk.dev/)にログイン
2. プロジェクトを選択
3. **Settings** → **Domains** に移動
4. Vercel の本番ドメインを追加（例: `your-app.vercel.app`）
5. **Allowed Origins** に以下を追加：
   - `https://your-app.vercel.app`
   - `https://msbs-next-api-xxxxx.run.app` (Cloud RunのURL)

### 4.2. Webhook の設定（オプション）

バッチ処理やユーザー同期が必要な場合、Webhook を設定します。

## 5. 疎通確認

### 5.1. ヘルスチェック

```bash
# Backend
curl https://msbs-next-api-xxxxx.run.app/health

# 期待されるレスポンス:
# {"status":"ok","message":"MSBS-Next API is running"}
```

### 5.2. フロントエンドからの接続確認

1. `https://your-app.vercel.app` にアクセス
2. サインイン
3. パイロット登録（初回のみ）
4. ダッシュボードで機体の閲覧・更新が可能か確認
5. シミュレーション実行が正常に動作するか確認

## 6. トラブルシューティング

### CORS エラーが発生する場合

Cloud Run の環境変数 `ALLOWED_ORIGINS` に、Vercel の全てのドメイン（本番、プレビュー）が含まれているか確認：

```bash
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format="value(spec.template.spec.containers[0].env)"
```

### データベース接続エラーが発生する場合

1. Neon の接続文字列が正しいか確認
2. Cloud Run から Neon への接続が可能か確認
3. SSL 接続が有効になっているか確認（Neon は SSL 必須）

### 認証エラーが発生する場合

1. Clerk の設定で本番ドメインが追加されているか確認
2. `CLERK_SECRET_KEY` と `CLERK_JWKS_URL` が正しいか確認
3. フロントエンドの `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` が本番用のキーになっているか確認

## 7. 継続的デプロイ

### GitHub Actions の設定（推奨）

`.github/workflows/deploy.yml` を作成して、main ブランチへのプッシュで自動デプロイを実行できます。

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - name: Deploy to Cloud Run
        run: |
          cd backend
          gcloud builds submit --tag ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/msbs-next/msbs-next-api
          gcloud run deploy msbs-next-api --image ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/msbs-next/msbs-next-api --region ${{ secrets.GCP_REGION }}

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Vercel
        run: |
          npm i -g vercel
          cd frontend
          vercel --prod --token ${{ secrets.VERCEL_TOKEN }}
```

## 8. 参考リンク

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vercel Documentation](https://vercel.com/docs)
- [Neon Documentation](https://neon.tech/docs/introduction)
- [Clerk Documentation](https://clerk.com/docs)

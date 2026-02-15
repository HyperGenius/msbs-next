# Cloud Run Terraform 設定

このディレクトリには、MSBS-Next バックエンド API を Google Cloud Run にデプロイするための Terraform 設定が含まれています。

## 構成リソース

- **Artifact Registry**: Docker イメージの保存
- **Secret Manager**: 機密情報（Database URL, Clerk Keys）の安全な管理
- **Cloud Run Service**: バックエンド API のホスティング
- **Service Account**: Cloud Run が他の GCP リソースにアクセスするための権限管理
- **IAM**: サービスアカウントへの権限付与

## 前提条件

1. Google Cloud Platform アカウント
2. `gcloud` CLI のインストールと認証
3. Terraform >= 1.0
4. 以下の GCP API を有効化:
   ```bash
   gcloud services enable \
     run.googleapis.com \
     artifactregistry.googleapis.com \
     secretmanager.googleapis.com \
     cloudbuild.googleapis.com
   ```

## セットアップ手順

### 1. 認証設定

```bash
# GCP にログイン
gcloud auth application-default login

# プロジェクトを設定
gcloud config set project YOUR_PROJECT_ID
```

### 2. 変数ファイルの準備

```bash
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars` を編集して、以下の値を設定:

- `project_id`: GCP プロジェクト ID
- `database_url`: Neon データベース接続文字列
- `clerk_secret_key`: Clerk Secret Key
- `clerk_jwks_url`: Clerk JWKS URL
- `allowed_origins`: Vercel ドメイン（カンマ区切り）

### 3. Terraform の初期化

```bash
terraform init
```

### 4. プランの確認

```bash
terraform plan
```

### 5. リソースの作成

```bash
terraform apply
```

### 6. Docker イメージのビルドとプッシュ

```bash
# Artifact Registry にログイン
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# リポジトリURLを取得
REPO_URL=$(terraform output -raw artifact_registry_repository)

# Docker イメージをビルド
cd ../../backend
docker build -t ${REPO_URL}/msbs-next-api:latest .

# イメージをプッシュ
docker push ${REPO_URL}/msbs-next-api:latest
```

または、Cloud Build を使用:

```bash
cd ../../backend
gcloud builds submit --tag ${REPO_URL}/msbs-next-api:latest
```

### 7. サービスURLの確認

```bash
terraform output service_url
```

このURLをフロントエンド（Vercel）の環境変数 `NEXT_PUBLIC_API_URL` に設定します。

## 環境変数の更新

既にデプロイ済みのサービスの環境変数を更新する場合:

1. `terraform.tfvars` を編集
2. `terraform apply` を実行

Secret Manager を使用しているため、機密情報は安全に管理されます。

## リソースの削除

```bash
terraform destroy
```

**注意**: この操作により、すべてのリソース（Secret Manager のシークレットを含む）が削除されます。

## トラブルシューティング

### イメージがデプロイされない

Artifact Registry にイメージがプッシュされているか確認:

```bash
gcloud artifacts docker images list \
  $(terraform output -raw artifact_registry_repository)
```

### サービスがヘルスチェックに失敗する

Cloud Run のログを確認:

```bash
gcloud run services logs read msbs-next-api --region=asia-northeast1
```

### Secret Manager へのアクセスエラー

サービスアカウントに適切な権限があるか確認:

```bash
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$(terraform output -raw service_account_email)"
```

## CI/CD 統合

GitHub Actions での自動デプロイ例:

```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v1
  with:
    credentials_json: ${{ secrets.GCP_SA_KEY }}

- name: Build and Push Docker Image
  run: |
    gcloud builds submit --tag ${ARTIFACT_REGISTRY_URL}/msbs-next-api:${{ github.sha }}

- name: Deploy to Cloud Run
  run: |
    cd infra/cloud-run
    terraform apply -auto-approve -var="image_tag=${{ github.sha }}"
```

## 参考リンク

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Artifact Registry Documentation](https://cloud.google.com/artifact-registry/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

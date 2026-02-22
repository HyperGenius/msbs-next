# Cloud Run Terraform 設定

このディレクトリには、MSBS-Next バックエンド API を Google Cloud Run にデプロイするための Terraform 設定が含まれています。

## デプロイメントの流れ

Cloud Run サービスは Docker イメージを必要とするため、以下の順序でデプロイを行います：

1. **基盤リソースの作成**: Artifact Registry、Secret Manager、Service Account などを作成
2. **Docker イメージのビルドとプッシュ**: バックエンドアプリケーションをコンテナ化して Artifact Registry にプッシュ
3. **Cloud Run サービスの作成**: プッシュされたイメージを使用して Cloud Run サービスをデプロイ

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

# タグの設定等を必要に応じて行う

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

### 5. 基盤リソースの作成（Artifact Registry、Secret Manager など）

Cloud Run サービスを作成する前に、まず Artifact Registry とシークレット関連のリソースを作成します：

```bash
terraform apply -target=google_artifact_registry_repository.msbs_next \
  -target=google_secret_manager_secret.database_url \
  -target=google_secret_manager_secret_version.database_url \
  -target=google_secret_manager_secret.clerk_secret_key \
  -target=google_secret_manager_secret_version.clerk_secret_key \
  -target=google_service_account.cloud_run \
  -target=google_secret_manager_secret_iam_member.database_url_access \
  -target=google_secret_manager_secret_iam_member.clerk_secret_key_access
```

### 6. Docker イメージのビルドとプッシュ

基盤リソースが作成されたら、Docker イメージをビルドして Artifact Registry にプッシュします：

```bash
# Artifact Registry にログイン
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

PROJECT_ID=msbs-next

# Docker イメージをビルド
cd ../../backend

# Apple Silicon (M1/M2/M3) Mac の場合
docker build --platform linux/amd64 -t asia-northeast1-docker.pkg.dev/${PROJECT_ID}/msbs-next/msbs-next-api:latest .

# Intel Mac / Linux の場合
# docker build -t asia-northeast1-docker.pkg.dev/${PROJECT_ID}/msbs-next/msbs-next-api:latest .

# イメージをプッシュ
docker push asia-northeast1-docker.pkg.dev/${PROJECT_ID}/msbs-next/msbs-next-api:latest
```

**重要**: Apple Silicon Mac では `--platform linux/amd64` オプションが必須です。Cloud Run は AMD64 アーキテクチャで動作するため、ARM64 イメージは使用できません。

または、Cloud Build を使用（推奨: アーキテクチャを気にせず自動でビルド）:

```bash
cd ../../backend
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")

# サービスアカウントに Cloud Build の権限を付与
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/storage.objectViewer" \
    --role="roles/artifactregistry.writer"

# Cloud Build を使用してビルドとプッシュ
gcloud builds submit --tag asia-northeast1-docker.pkg.dev/${PROJECT_ID}/msbs-next/msbs-next-api:latest
```

**Cloud Runを公開アクセス可能にする**
Cloud Run サービスを公開アクセス可能にするには、以下のコマンドを実行して全員に Cloud Run Invoker ロールを付与します：

```bash
gcloud run services add-iam-policy-binding msbs-next-api \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --region=asia-northeast1
```

### 7. Cloud Run サービスの作成

Docker イメージがプッシュされた後、残りのリソース（Cloud Run サービス）を作成します：

```bash
cd ../../infra/cloud-run
terraform apply
```

### 8. サービスURLの確認

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

### Cloud Run サービス作成時に「イメージが見つからない」エラー

Docker イメージを Artifact Registry にプッシュする前に Cloud Run サービスを作成しようとすると、このエラーが発生します。上記の手順 5 → 6 → 7 の順序で実行してください。

イメージが正しくプッシュされているか確認:

```bash
gcloud artifacts docker images list \
  asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/msbs-next
```

### Artifact Registry のイメージを削除したい

誤ったアーキテクチャでビルドした場合など、プッシュ済みのイメージを削除する場合：

```bash
# イメージ一覧を確認
gcloud artifacts docker images list \
  asia-northeast1-docker.pkg.dev/msbs-next/msbs-next

# 特定のタグを削除
gcloud artifacts docker images delete \
  asia-northeast1-docker.pkg.dev/msbs-next/msbs-next/msbs-next-api:latest \
  --quiet

# または、確認しながら削除（--quiet なし）
gcloud artifacts docker images delete \
  asia-northeast1-docker.pkg.dev/msbs-next/msbs-next/msbs-next-api:latest
```

**Apple Silicon Mac で誤ってビルドした場合**: `--platform linux/amd64` オプションなしでビルドした場合は、上記コマンドで削除してから正しくビルドし直してください。

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
    gcloud auth configure-docker asia-northeast1-docker.pkg.dev
    docker build -t asia-northeast1-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/msbs-next/msbs-next-api:${{ github.sha }} backend/
    docker push asia-northeast1-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/msbs-next/msbs-next-api:${{ github.sha }}

- name: Deploy to Cloud Run
  run: |
    cd infra/cloud-run
    terraform init
    terraform apply -auto-approve -var="image_tag=${{ github.sha }}"
```

**注意**: 初回デプロイ時は、手順 5 で基盤リソースを先に作成してから CI/CD を実行してください。

## 参考リンク

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Artifact Registry Documentation](https://cloud.google.com/artifact-registry/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

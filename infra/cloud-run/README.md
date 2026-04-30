# MSBS-Next Backend Infrastructure (Cloud Run)

このディレクトリには、MSBS-Next の FastAPI バックエンドを Google Cloud Run にデプロイするための Terraform コードが含まれています。
再利用性を高めるため、共通リソース（モジュール）と環境ごとの設定（エンバイロメント）に分離した構成を採用しています。

## 📁 ディレクトリ構成

```text
infra/cloud-run/
├── modules/                   # 共通化されたTerraformモジュール
│   ├── base/                  # 基盤リソース（Artifact Registry等）
│   └── cloud-run/             # アプリケーション層（Cloud Run, IAM, Secret Manager）
└── environments/              # 環境ごとのデプロイ設定
    ├── prod/                  # 本番環境 (Production)
    └── (dev/)                 # ※必要に応じて追加可能
```

## 🛠️ 事前準備

デプロイを実行する前に、以下の準備が必要です。

1. **ツールのインストール**
   - [Terraform](https://developer.hashicorp.com/terraform/downloads) (>= 1.0)
   - [Google Cloud CLI (gcloud)](https://cloud.google.com/sdk/docs/install)

2. **GCP 認証**
   ```bash
   gcloud auth application-default login
   ```

3. **Terraform State 保存用の GCS バケット作成**
   Terraform の State ファイルを保存するための GCS バケットを、**初回のみ** 手動で作成します。
   ```bash
   # 1. CLI認証を更新（ブラウザが開く）
   gcloud auth login

   # 2. デフォルトプロジェクトをに切り替え
   gcloud config set project <YOUR_PROJECT_ID>

   # 3. ADC（ライブラリ用認証）のクォータプロジェクトも切り替え
   gcloud auth application-default set-quota-project <YOUR_PROJECT_ID>

   # 4. バケットを作成
   gcloud storage buckets create gs://<YOUR_GCS_BUCKET_NAME> \
     --project=<YOUR_PROJECT_ID> \
     --location=<REGION> \
     --uniform-bucket-level-access

   # 5. バケットへのState ファイルの誤上書き・削除からのリカバリに備え、バージョニングを有効化
   gcloud storage buckets update gs://<YOUR_GCS_BUCKET_NAME> --versioning
   ```
   > このバケットは Terraform の管理外で一度だけ作成します。バケット名はグローバルで一意である必要があります（例: `MSBS-Next-tfstate-prod`）。

4. **必要な認証情報・値の取得**
   - GCP プロジェクト ID
   - Terraform State 保存用の GCS バケット名（上記で作成したもの）
   - Neon Database の接続 URL (`postgresql://...`)
   - Clerk Secret Key (`sk_live_...` または `sk_test_...`)
   - Clerk JWKS URL

## 🚀 デプロイ手順（本番環境: prod の場合）

### 1. ディレクトリの移動
対象環境のディレクトリに移動します。

```bash
cd environments/prod
```

### 2. 変数ファイルの設定
サンプルの変数をコピーして、実際の値に書き換えます。

```bash
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars` をエディタで開き、必要な値を設定してください。（※このファイルは `.gitignore` に含まれるため、Gitにはコミットされません）

### 3. 初期化 (init)
Terraform を初期化します。Stateファイルを保存する GCS バケット名を指定してください。

```bash
terraform init -backend-config="bucket=<YOUR_GCS_BUCKET_NAME>"
```

### 4. 計画の確認 (plan)
どのようなリソースが作成・変更されるかを確認します。

```bash
terraform plan
```

### 5. デプロイの実行 (apply)
変更を適用し、リソースを作成します。

```bash
terraform apply
```
完了すると、Cloud RunのURLやArtifact RegistryのリポジトリURLが出力（Outputs）として表示されます。

> **Note:** `terraform apply` 時点でイメージが Artifact Registry に存在しない場合、Cloud Run サービスの作成に失敗します（`Image not found` エラー）。後述の「初回イメージのプッシュ」を実施してから再度 `terraform apply` を実行してください。

---

## 🐳 初回イメージのプッシュ

Terraform で Artifact Registry を作成した後、初回は手動でイメージをビルド・プッシュする必要があります。

### 1. Docker 認証の設定

```bash
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

### 2. イメージのビルド＆プッシュ

```bash
PROJECT_ID=<YOUR_PROJECT_ID>
cd <repo_root>/backend

docker build -t asia-northeast1-docker.pkg.dev/${PROJECT_ID}/msbs-next/msbs-next-api:latest .
# または
docker build --platform linux/amd64 -t asia-northeast1-docker.pkg.dev/${PROJECT_ID}/msbs-next/msbs-next-api:latest .

docker push asia-northeast1-docker.pkg.dev/${PROJECT_ID}/msbs-next/msbs-next-api:latest
```

### 3. terraform apply の再実行

```bash
cd <repo_root>/infra/cloud-run/environments/prod
terraform apply
```

---

## 🔄 継続的デプロイ（GitHub Actions）

初回セットアップ完了後は、GitHub Actions によって自動デプロイが行われます。
`main` ブランチへの push をトリガーに以下のフローが実行されます：

```
main へ push
  → docker build & push（Artifact Registry へ）
  → Cloud Run サービスの更新
```

手動でのイメージプッシュや `terraform apply` は通常不要です。

---

## 💡 新しい環境（例: dev）を追加する方法

モジュール化されているため、新しい環境の追加は非常に簡単です。

1. `environments/prod` ディレクトリをコピーして `environments/dev` を作成します。
2. `environments/dev/versions.tf` を開き、バックエンドの prefix を変更します。
   ```hcl
   backend "gcs" {
     prefix = "terraform/cloud-run/dev" # prod から dev に変更
   }
   ```
3. `environments/dev/terraform.tfvars` の `environment` 変数や各種シークレットを開発環境用の値に変更します。
4. あとは同様に `terraform init`, `plan`, `apply` を実行するだけです。

## 🔐 シークレットの管理について
本構成では、Secret Managerのリソース（枠組み）と IAM 権限の作成、および初期値の登録を Terraform で行っています。
GitHub Actions などの CI/CD パイプラインを構築する場合は、Terraform にはダミーの値を渡し、実際の最新シークレット値の更新は CI/CD 側、または手動で GCP コンソールから行う運用に切り替えることも検討してください。

---

## IAM Service Account Credentials APIの有効化
GitHub Actions から GCP にアクセスするための Workload Identity Federation を利用する必要があります。

> [TIPS] WIF を使って Google Cloud にアクセスする場合、GitHub の ID トークンを Google のアクセス（OAuth2）トークンに交換する必要があります。この交換作業を担うのが IAM Service Account Credentials API (iamcredentials.googleapis.com) です。これが無効だと、認証が完了せず、その後の docker push で「権限がない（Unauthenticated）」と怒られてしまいます。

ローカル環境のターミナル（対象プロジェクトの権限があるアカウント）で以下を実行します。

```bash
gcloud services enable iamcredentials.googleapis.com --project=<YOUR_PROJECT_ID>
```

---


## ⚙️ GitHub Actions セットアップ

※IAMの設定はTerraform で行いますが、GitHub Actions 側の Secrets 登録は手動で行う必要があります。

`.github/workflows/deploy.yml` は `main` ブランチの `backend/` 配下への push をトリガーに、イメージのビルド・プッシュ・Cloud Run へのデプロイを自動実行します。

### 必要な GitHub Secrets

| Secret 名 | 説明 |
|---|---|
| `GCP_PROJECT_ID` | GCP プロジェクト ID |
| `WIF_PROVIDER` | Workload Identity Federation プロバイダのリソース名 |
| `WIF_SERVICE_ACCOUNT` | デプロイ用サービスアカウントのメールアドレス |

GitHub リポジトリの **Settings → Secrets and variables → Actions** から登録してください。

### Workload Identity Federation の設定（初回のみ）

キーレス認証のための WIF リソースは `infra/gcp-iam/` の Terraform で管理しています。
詳細な手順は [infra/gcp-iam/README.md](../gcp-iam/README.md) を参照してください。

```bash
cd infra/gcp-iam
cp terraform.tfvars.example terraform.tfvars
terraform init -backend-config="bucket=<YOUR_PROJECT_ID>-tfstate-prod"
terraform apply
```

### GitHub Secrets への登録値の確認

apply 完了後、以下のコマンドで各 Secret の値を取得できます。

```bash
cd infra/gcp-iam

# WIF_PROVIDER
terraform output workload_identity_provider_id

# WIF_SERVICE_ACCOUNT
terraform output service_account_email
```
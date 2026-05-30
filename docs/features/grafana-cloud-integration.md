# Grafana Cloud 統合

**バージョン:** v1.0  
**関連 Issue:** #371

## 概要

Cloud Run（FastAPI バックエンド）のログおよびメトリクスを **Grafana Cloud Free Plan** で可視化・監視する機能です。  
GCP のサービスアカウントを使ったプル型の統合により、追加のインフラ（Pub/Sub・Loki Agent 等）を不要で実現します。

## アーキテクチャ

```
Cloud Run
   │
   ▼ 自動転送
Cloud Logging / Cloud Monitoring
   │
   ▼ サービスアカウント認証でプル
Grafana Cloud (Loki / Mimir)
```

## インフラ構成

`infra/grafana/` に独立した Terraform root module として管理します。

| ファイル | 役割 |
|---|---|
| `main.tf` | SA・IAM・SA キーの定義 |
| `variables.tf` | `project_id`, `region` |
| `outputs.tf` | `grafana_sa_key_json`（sensitive） |
| `versions.tf` | Terraform / Provider バージョン、GCS backend |
| `terraform.tfvars.example` | 設定サンプル |
| `README.md` | 適用・接続手順 |

### 作成される GCP リソース

| リソース | 詳細 |
|---|---|
| Service Account | `grafana-cloud-reader@<PROJECT>.iam.gserviceaccount.com` |
| IAM | `roles/logging.viewer` — Cloud Logging 閲覧権限 |
| IAM | `roles/monitoring.viewer` — Cloud Monitoring 閲覧権限 |
| SA Key | Grafana Cloud に登録する JSON キー（terraform output で取得） |

## セットアップ手順

### 1. Terraform 適用

```bash
cd infra/grafana
cp terraform.tfvars.example terraform.tfvars
# project_id を設定

terraform init -backend-config="bucket=<GCS_BUCKET_NAME>"
terraform apply

# JSON キーを取得
terraform output -raw grafana_sa_key_json > /tmp/grafana-sa-key.json
```

### 2. Grafana Cloud への接続

1. Grafana Cloud にログイン
2. **Connections → Add new connection → Google Cloud Logs** を開く
3. JSON キーを貼り付けて認証
4. ログフィルタを設定：

```
resource.type="cloud_run_revision"
resource.labels.service_name="msbs-next-api-prod"
```

### 3. セキュリティ

- JSON キーは使用後に `/tmp/` から削除する
- サービスアカウントは読み取り専用権限（`viewer`）のみ付与
- SA キーのローテーションは Terraform で管理（`terraform apply` で再生成）

## Grafana Cloud Free Plan の制限

| 項目 | 上限 |
|---|---|
| ログ取り込み | 50 GB / 月 |
| ログ保持期間 | 14 日 |
| メトリクス | 10,000 シリーズ |
| アラート | 無制限 |

## 関連ファイル

- [infra/grafana/](../../infra/grafana/)
- [infra/gcp-iam/](../../infra/gcp-iam/) — GitHub Actions WIF（別途管理）

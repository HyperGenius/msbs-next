# infra/grafana

Cloud Run のログ・メトリクスを **Grafana Cloud Free Plan** に転送するための Terraform モジュールです。

## 概要

Grafana Cloud の [Google Cloud 統合](https://grafana.com/docs/grafana-cloud/monitor-infrastructure/integrations/integration-reference/integration-google-cloud-monitoring/) を使い、Cloud Logging からログをプル取得します。

```
Cloud Run → Cloud Logging（自動） → Grafana Cloud（SA キーで認証してプル）
```

## 作成されるリソース

| リソース | 内容 |
|---|---|
| `google_service_account` | `grafana-cloud-reader` — 読み取り専用 SA |
| `google_project_iam_member` | `roles/logging.viewer` — Cloud Logging 閲覧 |
| `google_project_iam_member` | `roles/monitoring.viewer` — Cloud Monitoring 閲覧 |
| `google_service_account_key` | Grafana Cloud に登録する JSON キー |

## 適用手順

### 1. 初期化

```bash
cd infra/grafana
cp terraform.tfvars.example terraform.tfvars
# project_id を編集

terraform init -backend-config="bucket=<GCS_BUCKET_NAME>"
terraform plan
terraform apply
```

### 2. JSON キーの取得

```bash
terraform output -raw grafana_sa_key_json > /tmp/grafana-sa-key.json
```

> **注意:** `/tmp/grafana-sa-key.json` はセキュリティのため使用後に削除してください。

### 3. Grafana Cloud への登録

1. Grafana Cloud にログイン
2. **Connections → Add new connection → Google Cloud Logs** を選択
3. 手順に従い、取得した JSON キーを貼り付ける
4. **Log filter** に以下を設定：

```
resource.type="cloud_run_revision"
resource.labels.service_name="msbs-next-api-prod"
```

## Grafana Cloud Free Plan の制限

| 項目 | 上限 |
|---|---|
| ログ取り込み | 50 GB / 月 |
| ログ保持期間 | 14 日 |
| メトリクス | 10,000 シリーズ |

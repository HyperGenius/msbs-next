output "grafana_sa_email" {
  description = "Grafana Cloud Reader サービスアカウントのメールアドレス"
  value       = google_service_account.grafana.email
}

output "grafana_sa_key_json" {
  description = "Grafana Cloud の Google Cloud 統合に登録する JSON キー（terraform output -raw grafana_sa_key_json で取得）"
  value       = base64decode(google_service_account_key.grafana.private_key)
  sensitive   = true
}

# Grafana Cloud が Cloud Logging / Cloud Monitoring をプルするためのサービスアカウント

resource "google_service_account" "grafana" {
  account_id   = "grafana-cloud-reader"
  display_name = "Grafana Cloud Reader"
  description  = "Grafana Cloud が Cloud Logging と Cloud Monitoring をプル読み取りするための SA"
}

resource "google_project_iam_member" "grafana_logs" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.grafana.email}"
}

resource "google_project_iam_member" "grafana_metrics" {
  project = var.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.grafana.email}"
}

# Grafana Cloud の Google Cloud 統合に登録する JSON キー
resource "google_service_account_key" "grafana" {
  service_account_id = google_service_account.grafana.name
}

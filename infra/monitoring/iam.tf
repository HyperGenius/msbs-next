# ==========================================
# Cloud Monitoring 読み取り用 SA
# Grafana Cloud stackdriver data source が使用
# ==========================================
resource "google_service_account" "monitoring_reader" {
  account_id   = "monitoring-reader"
  display_name = "Monitoring Reader for Grafana Cloud"
  project      = var.project_id
}

resource "google_project_iam_member" "monitoring_reader_viewer" {
  project = var.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.monitoring_reader.email}"
}

# Grafana の stackdriver data source は SA key (JSON) を使って認証する
resource "google_service_account_key" "monitoring_reader" {
  service_account_id = google_service_account.monitoring_reader.name
}

# ==========================================
# ログ転送 Cloud Functions 用 SA
# ==========================================
resource "google_service_account" "log_forwarder" {
  account_id   = "log-forwarder"
  display_name = "Log Forwarder for Grafana Cloud Loki"
  project      = var.project_id
}

resource "google_project_iam_member" "log_forwarder_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.log_forwarder.email}"
}

resource "google_project_iam_member" "log_forwarder_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.log_forwarder.email}"
}

# Cloud Functions v2 のデプロイに必要 (ビルド時に Artifact Registry を使う)
resource "google_project_iam_member" "log_forwarder_ar_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.log_forwarder.email}"
}

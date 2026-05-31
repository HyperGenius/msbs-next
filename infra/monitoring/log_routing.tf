# ==========================================
# Pub/Sub トピック
# ==========================================
resource "google_pubsub_topic" "cloud_run_logs" {
  name    = "cloud-run-logs-${var.environment}"
  project = var.project_id

  message_retention_duration = "86400s" # 1日（転送失敗時のバッファ）

  labels = {
    environment = var.environment
    managed-by  = "terraform"
  }
}

# Cloud Functions v2 は Pub/Sub push trigger のため subscription は不要
# （GCP が内部で push endpoint を作成する）

# ==========================================
# Cloud Logging → Pub/Sub Log Router sink
# ==========================================
resource "google_logging_project_sink" "cloud_run_to_pubsub" {
  name        = "cloud-run-logs-to-pubsub-${var.environment}"
  project     = var.project_id
  destination = "pubsub.googleapis.com/${google_pubsub_topic.cloud_run_logs.id}"

  # フィルター: INFO未満と HTTP 200 アクセスログを除外してコストを抑える
  filter = <<-EOT
    resource.type=("cloud_run_revision" OR "cloud_run_job")
    severity>="INFO"
    NOT httpRequest.status=200
  EOT

  unique_writer_identity = true
}

# Log Router sink の writer identity に Pub/Sub 発行権限を付与
resource "google_pubsub_topic_iam_member" "log_sink_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.cloud_run_logs.name
  role    = "roles/pubsub.publisher"
  member  = google_logging_project_sink.cloud_run_to_pubsub.writer_identity
}

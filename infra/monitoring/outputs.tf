output "monitoring_reader_sa_email" {
  description = "Cloud Monitoring 読み取り用サービスアカウント（Grafana が使用）"
  value       = google_service_account.monitoring_reader.email
}

output "log_forwarder_sa_email" {
  description = "ログ転送 Cloud Functions 用サービスアカウント"
  value       = google_service_account.log_forwarder.email
}

output "pubsub_topic_name" {
  description = "Cloud Run ログ転送用 Pub/Sub トピック名"
  value       = google_pubsub_topic.cloud_run_logs.name
}

output "log_forwarder_function_name" {
  description = "ログ転送 Cloud Functions 名"
  value       = google_cloudfunctions2_function.log_forwarder.name
}

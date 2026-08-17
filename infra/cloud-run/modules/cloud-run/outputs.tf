# infra/modules/cloud-run/outputs.tf
output "service_url" {
  value = google_cloud_run_v2_service.main.uri
}

output "service_name" {
  value = google_cloud_run_v2_service.main.name
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository URL"
  value       = var.repository_url
}

output "service_account_email" {
  value = google_service_account.cloud_run.email
}

output "batch_job_name" {
  description = "Cloud Run Jobs のジョブ名（バッチ実行用）"
  value       = google_cloud_run_v2_job.msbs_batch.name
}

output "battle_logs_bucket_name" {
  description = "バトルログオフロード先GCSバケット名（Issue #493）"
  value       = google_storage_bucket.battle_logs.name
}

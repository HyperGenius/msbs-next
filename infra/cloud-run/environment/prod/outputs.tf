# infra/environments/prod/outputs.tf
output "service_url" {
  description = "Cloud Run service URL"
  value       = module.cloud_run.service_url
}

output "service_name" {
  description = "Cloud Run service name"
  value       = module.cloud_run.service_name
}

output "artifact_registry_repository_url" {
  description = "Artifact Registry repository URL"
  value       = module.base.repository_url
}

output "battle_logs_bucket_name" {
  description = "バトルログオフロード先GCSバケット名（Issue #493）"
  value       = module.cloud_run.battle_logs_bucket_name
}
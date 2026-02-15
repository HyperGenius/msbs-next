output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.msbs_next_api.uri
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.msbs_next_api.name
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.msbs_next.repository_id}"
}

output "service_account_email" {
  description = "Service account email for Cloud Run"
  value       = google_service_account.cloud_run.email
}

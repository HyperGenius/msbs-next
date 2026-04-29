# infra/modules/cloud-run/outputs.tf
output "service_url" {
  value = google_cloud_run_v2_service.main.uri
}

output "service_name" {
  value = google_cloud_run_v2_service.main.name
}

output "service_account_email" {
  value = google_service_account.cloud_run.email
}
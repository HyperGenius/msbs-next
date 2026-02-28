# infra/gcp-iam/outputs.tf

output "workload_identity_provider_id" {
  description = "GitHub Actionsの workload_identity_provider に設定する値"
  value       = google_iam_workload_identity_pool_provider.github_provider.name
}

output "service_account_email" {
  description = "GitHub Actionsの service_account に設定する値"
  value       = google_service_account.github_actions.email
}

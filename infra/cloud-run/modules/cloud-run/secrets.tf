# infra/modules/cloud-run/secrets.tf
# シークレットIDに ${var.environment} を含めることで、同じGCPプロジェクト内で dev と prod のシークレットを共存できるようにする

resource "google_project_service" "secretmanager" {
  project                    = var.project_id
  service                    = "secretmanager.googleapis.com"
  disable_on_destroy         = false
  disable_dependent_services = false
}

# Secret Manager: Database URL
resource "google_secret_manager_secret" "database_url" {
  depends_on = [google_project_service.secretmanager]
  secret_id = "${var.service_name}-db-url-${var.environment}"

  replication {
    auto {}
  }
  labels = { environment = var.environment }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = var.database_url
}

# Secret Manager: Clerk Secret Key
resource "google_secret_manager_secret" "clerk_secret_key" {
  depends_on = [google_project_service.secretmanager]
  secret_id = "${var.service_name}-clerk-key-${var.environment}"

  replication {
    auto {}
  }
  labels = { environment = var.environment }
}

resource "google_secret_manager_secret_version" "clerk_secret_key" {
  secret      = google_secret_manager_secret.clerk_secret_key.id
  secret_data = var.clerk_secret_key
}
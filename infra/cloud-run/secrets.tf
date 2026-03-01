# infra/cloud-run/secrets.tf
# Secret Manager: Database URL
resource "google_secret_manager_secret" "database_url" {
  secret_id = "msbs-next-database-url"

  replication {
    auto {}
  }

  labels = {
    service = var.service_name
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = var.database_url
}

# Secret Manager: Clerk Secret Key
resource "google_secret_manager_secret" "clerk_secret_key" {
  secret_id = "msbs-next-clerk-secret-key"

  replication {
    auto {}
  }

  labels = {
    service = var.service_name
  }
}

resource "google_secret_manager_secret_version" "clerk_secret_key" {
  secret      = google_secret_manager_secret.clerk_secret_key.id
  secret_data = var.clerk_secret_key
}
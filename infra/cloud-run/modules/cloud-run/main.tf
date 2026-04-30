# infra/modules/cloud-run/main.tf
# サービスアカウント
resource "google_service_account" "cloud_run" {
  account_id   = "${var.service_name}-${var.environment}-sa"
  display_name = "Service Account for ${var.service_name} (${var.environment})"
}

# Secret Manager へのアクセス権限
resource "google_secret_manager_secret_iam_member" "database_url_access" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_secret_manager_secret_iam_member" "clerk_secret_key_access" {
  secret_id = google_secret_manager_secret.clerk_secret_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Cloud Run サービス
resource "google_cloud_run_v2_service" "main" {
  name     = "${var.service_name}-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  labels = {
    environment = var.environment
  }

  template {
    service_account = google_service_account.cloud_run.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.image_url

      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
      }

      ports {
        container_port = 8080
      }

      env {
        name = "NEON_DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "CLERK_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.clerk_secret_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "CLERK_JWKS_URL"
        value = var.clerk_jwks_url
      }

      env {
        name  = "ALLOWED_ORIGINS"
        value = var.allowed_origins
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 5
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 5
      }
    }
    max_instance_request_concurrency = var.container_concurrency
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image, # GitHub Actions側でタグを更新するため
      client,                          # gcloud等からの変更を無視
      client_version
    ]
  }

  depends_on = [
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.clerk_secret_key,
    google_secret_manager_secret_iam_member.database_url_access,
    google_secret_manager_secret_iam_member.clerk_secret_key_access,
  ]
}

# 一般公開アクセス
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  name     = google_cloud_run_v2_service.main.name
  project  = google_cloud_run_v2_service.main.project
  location = google_cloud_run_v2_service.main.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
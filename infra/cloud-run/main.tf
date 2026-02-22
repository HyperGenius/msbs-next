# Artifact Registry リポジトリ
resource "google_artifact_registry_repository" "msbs_next" {
  location      = var.region
  repository_id = "msbs-next"
  description   = "Docker repository for MSBS-Next backend images"
  format        = "DOCKER"

  labels = {
    environment = "production"
    project     = "msbs-next"
  }
}

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

# Cloud Run サービスアカウント
resource "google_service_account" "cloud_run" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service Account for ${var.service_name}"
  description  = "Used by Cloud Run service to access GCP resources"
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
resource "google_cloud_run_v2_service" "msbs_next_api" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  labels = {
    environment = "production"
    project     = "msbs-next"
  }

  template {
    service_account = google_service_account.cloud_run.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.msbs_next.repository_id}/${var.service_name}:${var.image_tag}"

      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
      }

      ports {
        container_port = 8080
      }

      # 環境変数（Secret Managerから取得）
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

      # 通常の環境変数
      env {
        name  = "CLERK_JWKS_URL"
        value = var.clerk_jwks_url
      }

      env {
        name  = "ALLOWED_ORIGINS"
        value = var.allowed_origins
      }

      # ヘルスチェック
      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 0
        timeout_seconds       = 1
        period_seconds        = 3
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 10
        timeout_seconds       = 1
        period_seconds        = 10
        failure_threshold     = 3
      }
    }

    max_instance_request_concurrency = var.container_concurrency
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.clerk_secret_key,
    google_secret_manager_secret_iam_member.database_url_access,
    google_secret_manager_secret_iam_member.clerk_secret_key_access,
  ]
}

# Cloud Run サービスへの一般公開アクセスを許可
#resource "google_cloud_run_v2_service_iam_member" "public_access" {
#  name     = google_cloud_run_v2_service.msbs_next_api.name
#  location = google_cloud_run_v2_service.msbs_next_api.location
#  role     = "roles/run.invoker"
#  member   = "allUsers"
#}

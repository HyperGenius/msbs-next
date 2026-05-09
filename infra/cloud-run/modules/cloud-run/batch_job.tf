# infra/cloud-run/modules/cloud-run/batch_job.tf
# Cloud Run Jobs リソース（バッチ実行用）
resource "google_cloud_run_v2_job" "msbs_batch" {
  name     = "msbs-next-batch-${var.environment}"
  location = var.region

  labels = {
    environment = var.environment
  }

  template {
    template {
      service_account = google_service_account.cloud_run.email

      # バッチは冪等性を担保しているため再試行しない
      max_retries = 0

      # デフォルトタイムアウト: 3600秒（1時間）。大規模バトルでは延長を検討
      timeout = "3600s"

      containers {
        image = "${var.repository_url}/msbs-next-batch:${var.batch_image_tag}"

        resources {
          limits = {
            cpu    = var.batch_cpu_limit
            memory = var.batch_memory_limit
          }
        }

        # Secret Manager からシークレットを注入
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
          name  = "MAX_SIMULATION_STEPS"
          value = tostring(var.max_simulation_steps)
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.clerk_secret_key,
    google_secret_manager_secret_iam_member.database_url_access,
    google_secret_manager_secret_iam_member.clerk_secret_key_access,
  ]
}

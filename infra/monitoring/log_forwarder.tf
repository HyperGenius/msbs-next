# ==========================================
# Loki パスワードを Secret Manager に保存
# ==========================================
resource "google_secret_manager_secret" "loki_password" {
  secret_id = "loki-password-${var.environment}"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed-by  = "terraform"
  }
}

resource "google_secret_manager_secret_version" "loki_password" {
  secret      = google_secret_manager_secret.loki_password.id
  secret_data = var.loki_password
}

# ==========================================
# Cloud Functions v2 ソースを GCS にアップロード
# ==========================================
data "archive_file" "log_forwarder" {
  type        = "zip"
  source_dir  = "${path.module}/functions/log_forwarder"
  output_path = "${path.module}/.terraform/log_forwarder.zip"
}

resource "google_storage_bucket_object" "log_forwarder_source" {
  name   = "functions/log_forwarder-${data.archive_file.log_forwarder.output_md5}.zip"
  bucket = var.gcs_functions_bucket
  source = data.archive_file.log_forwarder.output_path
}

# ==========================================
# Cloud Functions v2 (Pub/Sub trigger)
# ==========================================
resource "google_cloudfunctions2_function" "log_forwarder" {
  name     = "cloud-run-log-forwarder-${var.environment}"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "python312"
    entry_point = "forward_to_loki"

    source {
      storage_source {
        bucket = var.gcs_functions_bucket
        object = google_storage_bucket_object.log_forwarder_source.name
      }
    }
  }

  service_config {
    service_account_email = google_service_account.log_forwarder.email
    available_memory      = "256M"
    timeout_seconds       = 60
    max_instance_count    = 10

    environment_variables = {
      LOKI_URL    = var.loki_url
      LOKI_USERNAME = var.loki_username
      ENVIRONMENT = var.environment
    }

    secret_environment_variables {
      key        = "LOKI_PASSWORD"
      project_id = var.project_id
      secret     = google_secret_manager_secret.loki_password.secret_id
      version    = "latest"
    }
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.cloud_run_logs.id
    retry_policy   = "RETRY_POLICY_RETRY"
  }

  labels = {
    environment = var.environment
    managed-by  = "terraform"
  }
}

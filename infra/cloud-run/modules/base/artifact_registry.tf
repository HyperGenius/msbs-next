# infra/cloud-run/modules/artifact_registry.tf
# Artifact Registry リポジトリ
resource "google_artifact_registry_repository" "main" {
  depends_on    = [google_project_service.required_apis]
  location      = var.region
  repository_id = var.repository_id
  description   = "Docker repository for ${var.environment} environment"
  format        = "DOCKER"

  labels = {
    environment = var.environment
    project     = "msbs-next"
  }

  # 1. 古いイメージを自動削除（最新の5つだけ保持）
  cleanup_policies {
    id     = "keep-latest-versions"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }

  # 2. タグのないイメージ（古いlatestなど）を削除
  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"
    condition {
      tag_state = "UNTAGGED"
    }
  }

  # 3. 30日以上経過したイメージを削除（任意。さらに厳しく制限する場合）
  cleanup_policies {
    id     = "delete-old-images"
    action = "DELETE"
    condition {
      older_than = "2592000s" # 30日を秒で指定
    }
  }
}
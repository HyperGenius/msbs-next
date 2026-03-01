# infra/cloud-run/artifact_registry.tf
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
# infra/modules/base/main.tf

# 必要なAPIの有効化
resource "google_project_service" "required_apis" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "run.googleapis.com",
    "orgpolicy.googleapis.com",
  ])

  project                    = var.project_id
  service                    = each.key
  disable_on_destroy         = false
  disable_dependent_services = false
}

# Cloud Run サービスへの allUsers IAM 付与を許可するための組織ポリシー上書き
# デフォルトでは組織ポリシーにより allUsers への IAM 付与が禁止されているため
resource "google_project_organization_policy" "allow_public_iam" {
  project    = var.project_id
  constraint = "constraints/iam.allowedPolicyMemberDomains"

  list_policy {
    allow {
      all = true
    }
  }

  depends_on = [google_project_service.required_apis]
}
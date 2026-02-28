# 1. Artifact Registry へのアクセス権限（イメージのプッシュ用）
resource "google_project_iam_member" "artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# 2. Cloud Run の管理者権限（デプロイ用）
resource "google_project_iam_member" "cloud_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# 3. サービスアカウントユーザー権限
# Cloud Run実行用サービスアカウントを指定
resource "google_project_iam_member" "iam_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# 4. Terraformで他のリソース（VPCコネクタやIAM等）を操作する場合必要に応じてロールを追加
# roles/editor で広く持たせるか、特定のリソース管理者権限を付与
resource "google_project_iam_member" "terraform_editor" {
  project = var.project_id
  role    = "roles/editor"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# 5. GCS Backendを利用している場合（Terraform State保存用）
resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}
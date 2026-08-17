# infra/cloud-run/modules/cloud-run/battle_log_storage.tf
# バトルリプレイ用生ログのオフロード先GCSバケット（Issue #493）
#
# GET /api/battles/{id}/logs はリプレイ閲覧のたびにNeon(PostgreSQL)から生ログ全量を
# 読み出しており、これがNeonの課金対象Network Transferをそのまま消費していた。
# ログ本体をこのバケットへオフロードし、Neonにはgcs_path（オブジェクトパス）のみを
# 残すことでこの転送経路からログ本体を完全に外す
# （詳細は backend/app/services/battle_log_storage_service.py、
# docs/features/battle-log-feature.md 参照）。

resource "google_storage_bucket" "battle_logs" {
  name                        = "${var.project_id}-battle-logs-${var.environment}"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  labels = { environment = var.environment }

  # 保持期間短縮（対策候補の一つ）。ログ本体をNeonから切り離したことで、
  # コード変更なしにバケットのライフサイクルルールだけで実現できる。
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }

  # storage.googleapis.com の有効化は base モジュール（required_apis）側で行う。
  # この module は base の repository_url 経由でしか base に依存していないため、
  # storage API 自体への直接依存は表現できないが、対象プロジェクトには既存の
  # バケット（tfstate等）があり storage API は有効化済みのため実害はない。
}

# Cloud Runサービス（main.py）・Cloud Run Jobs（run_batch.py、バックフィルスクリプト
# 実行時も含む）はいずれも同じ google_service_account.cloud_run を使うため、
# 1つのIAMバインディングで両方をカバーする。
#
# 配信をCloud Run自身によるGCSストリーム中継方式（署名付きURLリダイレクトではない）
# にしたため、roles/iam.serviceAccountTokenCreator（signBlob用）は不要。読み書きに
# 必要な最小権限として objectViewer（get/list） + objectCreator（アップロード）のみ
# 付与する（objectAdmin は delete 権限まで含むが、アプリコードはオブジェクトを
# 削除しないため不要。バケットのライフサイクルルールによる削除はGCS自体が
# サービスエージェントとして行うため、Cloud Run側SAの権限とは無関係）。
resource "google_storage_bucket_iam_member" "battle_logs_viewer" {
  bucket = google_storage_bucket.battle_logs.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_storage_bucket_iam_member" "battle_logs_creator" {
  bucket = google_storage_bucket.battle_logs.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.cloud_run.email}"
}

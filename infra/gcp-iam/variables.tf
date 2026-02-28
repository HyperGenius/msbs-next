variable "project_id" {
  description = "Google Cloud のプロジェクトID"
  type        = string
}

variable "region" {
  description = "デフォルトのリソース配置リージョン"
  type        = string
  default     = "asia-northeast1"
}

variable "github_repository" {
  description = "GitHubのリポジトリ（形式: ユーザー名/リポジトリ名）"
  type        = string
  # 例: "your-name/msbs-next"
}

variable "pool_id" {
  description = "Workload Identity プールのID"
  type        = string
  default     = "github-actions-pool"
}

variable "provider_id" {
  description = "Workload Identity プロバイダのID"
  type        = string
  default     = "github-provider"
}

variable "service_account_id" {
  description = "GitHub Actionsが使用するサービスアカウントのID"
  type        = string
  default     = "github-actions-deployer"
}

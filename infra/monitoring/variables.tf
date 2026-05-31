# ==========================================
# GCP 基本設定
# ==========================================
variable "project_id" {
  description = "GCP プロジェクト ID"
  type        = string
}

variable "region" {
  description = "GCP リージョン"
  type        = string
  default     = "asia-northeast1"
}

variable "environment" {
  description = "環境識別子"
  type        = string
  default     = "prod"
}

# ==========================================
# 監視対象 Cloud Run リソース
# ==========================================
variable "cloud_run_service_name" {
  description = "監視対象の Cloud Run サービス名"
  type        = string
  default     = "msbs-next-api-prod"
}

variable "cloud_run_job_name" {
  description = "監視対象の Cloud Run ジョブ名"
  type        = string
  default     = "msbs-next-batch-prod"
}

# ==========================================
# Grafana Cloud 接続設定
# ==========================================
variable "grafana_url" {
  description = "Grafana Cloud スタック URL (例: https://yourorg.grafana.net)"
  type        = string
}

variable "grafana_auth" {
  description = "Grafana Cloud サービスアカウントトークン"
  type        = string
  sensitive   = true
}

variable "loki_url" {
  description = "Grafana Cloud Loki のベース URL (例: https://logs-prod-xxx.grafana.net)"
  type        = string
}

variable "loki_username" {
  description = "Grafana Cloud Loki のユーザー名（数値 ID）"
  type        = string
}

variable "loki_password" {
  description = "Grafana Cloud token（Loki 送信用）"
  type        = string
  sensitive   = true
}

# ==========================================
# Cloud Functions ソースの格納先
# ==========================================
variable "gcs_functions_bucket" {
  description = "Cloud Functions ソース zip を置く GCS バケット名（既存の tfstate バケットを流用可）"
  type        = string
}

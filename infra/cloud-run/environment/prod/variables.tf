# infra/environments/prod/variables.tf
# ==========================================
# GCP 基本設定
# ==========================================
variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "asia-northeast1"
}

variable "environment" {
  type    = string
  default = "prod"
}

# ==========================================
# Cloud Run サービス設定
# ==========================================
variable "service_name" {
  type    = string
  default = "msbs-next-api"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

# ==========================================
# リソース設定
# ==========================================
variable "container_concurrency" {
  type    = number
  default = 80
}

variable "min_instances" {
  type    = number
  default = 0
}

variable "max_instances" {
  type    = number
  default = 10
}

variable "cpu_limit" {
  type    = string
  default = "1"
}

variable "memory_limit" {
  type    = string
  default = "512Mi"
}

# ==========================================
# アプリケーション設定・シークレット
# ==========================================
variable "database_url" {
  type      = string
  sensitive = true
}

variable "clerk_secret_key" {
  type      = string
  sensitive = true
}

variable "clerk_jwks_url" {
  type = string
}

variable "allowed_origins" {
  type    = list(string)
}

# ==========================================
# Cloud Run Jobs（バッチ）設定
# ==========================================
variable "batch_image_tag" {
  description = "バッチ Docker イメージタグ"
  type        = string
  default     = "latest"
}

variable "batch_cpu_limit" {
  description = "バッチジョブの CPU 上限"
  type        = string
  default     = "2"
}

variable "batch_memory_limit" {
  description = "バッチジョブのメモリ上限"
  type        = string
  default     = "2Gi"
}

variable "max_simulation_steps" {
  description = "バトル 1 戦あたりの最大シミュレーションステップ数 (1 step = 0.1 s)"
  type        = number
  default     = 3000
}
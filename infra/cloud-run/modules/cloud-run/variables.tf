# infra/modules/cloud-run/variables.tf
# ==========================================
# GCP 基本設定
# ==========================================
variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "environment" {
  type = string
}

# ==========================================
# Cloud Run サービス設定
# ==========================================
variable "service_name" {
  description = "Cloud Run service base name"
  type        = string
}

variable "image_url" {
  description = "Full URL of the Docker image to deploy (e.g., region-docker.pkg.dev/project/repo/image:tag)"
  type        = string
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
  type    = string
  default = ""
}

# ==========================================
# Cloud Run Jobs（バッチ）設定
# ==========================================
variable "repository_url" {
  description = "Base URL of the Artifact Registry repository (e.g., region-docker.pkg.dev/project/repo)"
  type        = string
}

variable "batch_image_tag" {
  description = "Docker image tag for the batch job"
  type        = string
  default     = "latest"
}

variable "batch_cpu_limit" {
  description = "CPU limit for the batch job container"
  type        = string
  default     = "1"
}

variable "batch_memory_limit" {
  description = "Memory limit for the batch job container"
  type        = string
  default     = "512Mi"
}

variable "max_simulation_steps" {
  description = "Maximum number of simulation steps per battle (1 step = 0.1 s)"
  type        = number
  default     = 3000
}
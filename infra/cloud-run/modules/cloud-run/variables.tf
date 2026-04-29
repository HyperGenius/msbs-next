# infra/modules/cloud-run/variables.tf
variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "environment" {
  type = string
}

variable "service_name" {
  description = "Cloud Run service base name"
  type        = string
}

variable "image_url" {
  description = "Full URL of the Docker image to deploy (e.g., region-docker.pkg.dev/project/repo/image:tag)"
  type        = string
}

# リソース設定
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

# アプリケーション設定
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
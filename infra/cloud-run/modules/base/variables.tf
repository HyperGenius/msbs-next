# infra/modules/base/variables.tf
# コンテナイメージを格納するArtifact Registryを作成する
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., dev, stg, prod)"
  type        = string
}

variable "repository_id" {
  description = "Artifact Registry repository ID"
  type        = string
  default     = "msbs-next"
}
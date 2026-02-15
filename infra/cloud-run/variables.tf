variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region for Cloud Run deployment"
  type        = string
  default     = "asia-northeast1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "msbs-next-api"
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "database_url" {
  description = "Neon Database connection URL"
  type        = string
  sensitive   = true
}

variable "clerk_secret_key" {
  description = "Clerk Secret Key for authentication"
  type        = string
  sensitive   = true
}

variable "clerk_jwks_url" {
  description = "Clerk JWKS URL for JWT verification"
  type        = string
}

variable "allowed_origins" {
  description = "Comma-separated list of allowed CORS origins (e.g., Vercel domains)"
  type        = string
  default     = ""
}

variable "container_concurrency" {
  description = "Maximum number of concurrent requests per container instance"
  type        = number
  default     = 80
}

variable "min_instances" {
  description = "Minimum number of container instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of container instances"
  type        = number
  default     = 10
}

variable "cpu_limit" {
  description = "CPU limit for each container instance"
  type        = string
  default     = "1"
}

variable "memory_limit" {
  description = "Memory limit for each container instance"
  type        = string
  default     = "512Mi"
}

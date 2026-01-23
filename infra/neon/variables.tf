variable "neon_api_key" {
  description = "Neon API Key"
  type        = string
  sensitive   = true
}

variable "project_name" {
  description = "Name of the Neon project"
  type        = string
  default     = "msbs-next"
}

variable "db_owner" {
  description = "Database owner username"
  type        = string
  default     = "msbs_owner"
}

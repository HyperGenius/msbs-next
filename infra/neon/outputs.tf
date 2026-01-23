output "database_url" {
  description = "Database connection string for .env (pooled connection recommended)"
  value       = "postgresql://${neon_role.owner.name}:${neon_role.owner.password}@${neon_project.this.database_host}/${neon_database.main.name}?sslmode=require"
  sensitive   = true
}

output "project_id" {
  value = neon_project.this.id
}

# infra/environments/prod/main.tf
# base モジュールで作成した Artifact Registry の URL を参照して
# cloud-run モジュールに渡すイメージ URL を組み立てる

# 1. 基盤リソース（Artifact Registry等）
module "base" {
  source = "../../modules/base"

  project_id    = var.project_id
  region        = var.region
  environment   = var.environment
  repository_id = "msbs-next"
}

# 2. アプリケーションリソース（Cloud Run, Secret Manager, IAM等）
module "cloud_run" {
  source = "../../modules/cloud-run"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment

  service_name = var.service_name
  
  # baseモジュールの出力（repository_url）を利用してイメージURLを構築
  image_url = "${module.base.repository_url}/${var.service_name}:${var.image_tag}"

  # スケーリング・リソース設定
  container_concurrency = var.container_concurrency
  min_instances         = var.min_instances
  max_instances         = var.max_instances
  cpu_limit             = var.cpu_limit
  memory_limit          = var.memory_limit

  # 環境変数・シークレット
  database_url     = var.database_url
  clerk_secret_key = var.clerk_secret_key
  clerk_jwks_url   = var.clerk_jwks_url
  allowed_origins  = join(",", var.allowed_origins)

  # Artifact Registry
  repository_url = module.base.repository_url

  # batch_job 設定
  batch_image_tag       = var.batch_image_tag
  batch_cpu_limit       = var.batch_cpu_limit
  batch_memory_limit    = var.batch_memory_limit
  max_simulation_steps  = var.max_simulation_steps
}
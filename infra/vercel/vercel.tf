# プロジェクトの定義
resource "vercel_project" "msbs_next" {
  name           = "msbs-next"
  framework      = "nextjs"
  root_directory = "frontend"

  # GitHubリポジトリの連携
  git_repository = {
    type = "github"
    repo = "HyperGenius/msbs-next"
  }

  # プロバイダーの仕様ズレや意図しない初期化を防ぐため、特定項目の変更を無視
  lifecycle {
    ignore_changes = [
      oidc_token_config,
      vercel_authentication,
      protection_bypass_for_automation_secret
    ]
  }
}

# ドメインの定義
resource "vercel_project_domain" "liber_biz" {
  project_id = vercel_project.msbs_next.id
  domain     = "msbs-next.liber-biz.com"
}
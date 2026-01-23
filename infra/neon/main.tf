# プロジェクト作成
resource "neon_project" "this" {
  name                      = var.project_name
  history_retention_seconds = 0 # フリープランの上限エラーを回避
  region_id                 = "aws-ap-southeast-1"
}

# デフォルトブランチ (main) の取得 (プロジェクト作成時に自動で作られる)
# 明示的に管理したい場合は neon_branch リソースを使用しますが、
# ここではシンプルにプロジェクト作成時のデフォルトを参照します。

# ロール (DBユーザー) の作成
resource "neon_role" "owner" {
  project_id = neon_project.this.id
  branch_id  = neon_project.this.default_branch_id
  name       = var.db_owner
}

# データベースの作成
resource "neon_database" "main" {
  project_id = neon_project.this.id
  branch_id  = neon_project.this.default_branch_id
  name       = "msbs_db"
  owner_name = neon_role.owner.name
}

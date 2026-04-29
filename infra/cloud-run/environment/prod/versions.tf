# infra/environments/prod/version.tf
# プロバイダの設定とtfstateの保存先（Backend）を定義
# GCSの保存パス（prefix）に prod を含めることで他の環境とStateファイルが混ざらないようにする
terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    # bucket は terraform init -backend-config="bucket=<BUCKET_NAME>" で渡す想定
    prefix = "terraform/cloud-run/prod"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
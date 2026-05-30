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
    prefix = "terraform/grafana"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

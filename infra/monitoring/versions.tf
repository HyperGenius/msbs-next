terraform {
  required_version = ">= 1.3"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    grafana = {
      source  = "grafana/grafana"
      version = "~> 3.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }

  backend "gcs" {
    # bucket は terraform init -backend-config="bucket=<BUCKET_NAME>" で渡す
    prefix = "terraform/monitoring/prod"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "grafana" {
  url  = var.grafana_url
  auth = var.grafana_auth
}

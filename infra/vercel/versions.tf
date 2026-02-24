terraform {
  required_providers {
    vercel = {
      source  = "vercel/vercel"
      version = "~> 2.0" # バージョンは環境に合わせて調整してください
    }
  }
}

provider "vercel" {
    api_token = var.vercel_api_token
    team = "team_TjT7txejqX8eFfBoKOwpa2kT"
}
# Infrastructure Setup Guide

本プロジェクトでは、データベース (Neon) の管理に Terraform を使用しています。

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.0
- Neon Account

## 1. Neon Database Setup

Neon の Project, Role, Database を Terraform でプロビジョニングします。

### ディレクトリ
`infra/neon/`

### 実行手順

1.  **Neon API Key の取得**:
    - [Neon Console](https://console.neon.tech/) にログイン。
    - 次の手順でキーを作成・コピーします。
        - Organization settings > API keys > Create new API key > Org-wide

2.  **Terraform の初期化**:
    ```bash
    cd infra/neon
    terraform init
    ```

3.  **実行計画の確認 (Plan)**:
    APIキーは環境変数 `TF_VAR_neon_api_key` で渡すことを推奨します。
    ```bash
    export TF_VAR_neon_api_key="your_api_key_here"
    terraform plan
    ```

4.  **適用の実行 (Apply)**:
    ```bash
    terraform apply
    # 内容を確認し、問題なければ 'yes' と入力
    ```

5.  **環境変数の設定**:
    完了後、Output に接続文字列が表示されます（sensitive扱いのためマスクされる場合があります）。
    その場合は以下のコマンドで確認してください。
    
    ```bash
    terraform output database_url
    ```

    取得したURLを `backend/.env` に設定します：
    ```ini
    DATABASE_URL="postgresql://..."
    ```

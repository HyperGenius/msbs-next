# Clerk 認証セットアップガイド

このプロジェクトでは Clerk を使用して認証を実装しています。

## 1. Clerk アプリケーションの作成

1. [Clerk Dashboard](https://dashboard.clerk.com/) にアクセスし、新しいアプリケーションを作成します
2. API キーを取得します：
   - **Publishable Key** (公開キー)
   - **Secret Key** (秘密キー)

## 2. フロントエンド設定

1. `frontend/.env.local.example` を `frontend/.env.local` にコピーします：
   ```bash
   cd frontend
   cp .env.local.example .env.local
   ```

2. `.env.local` ファイルを編集し、Clerk の API キーを設定します：
   ```env
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
   CLERK_SECRET_KEY=sk_test_xxxxx
   ```

3. 必要に応じて、Clerk のドメインを設定します（デフォルトで自動設定されます）

## 3. バックエンド設定

1. `backend/.env.example` を `backend/.env` にコピーします：
   ```bash
   cd backend
   cp .env.example .env
   ```

2. `.env` ファイルを編集し、Clerk の設定を追加します：
   ```env
   CLERK_SECRET_KEY=sk_test_xxxxx
   CLERK_JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json
   ```

   **JWKS URL の確認方法：**
   - Clerk Dashboard → API Keys → Advanced → JWKS Endpoint
   - または、あなたの Clerk ドメインが `example-app-123.clerk.accounts.dev` の場合：
     ```
     https://example-app-123.clerk.accounts.dev/.well-known/jwks.json
     ```

3. Python 依存関係をインストールします：
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

## 4. アプリケーションの起動

### バックエンド
```bash
cd backend
uvicorn main:app --reload
```

### フロントエンド
```bash
cd frontend
npm run dev
```

## 5. 認証の動作確認

1. ブラウザで `http://localhost:3000` にアクセス
2. ヘッダーの「Sign In」ボタンをクリック
3. Clerk の認証モーダルでサインアップ/ログイン
4. ログイン後、ユーザーアイコンが表示されることを確認
5. `/garage` ページにアクセスして、保護されたルートが機能することを確認

## トラブルシューティング

### フロントエンドで認証エラーが発生する場合
- `.env.local` ファイルが正しく配置されているか確認
- API キーが正しくコピーされているか確認
- Next.js を再起動（Ctrl+C してから `npm run dev`）

### バックエンドで JWT 検証エラーが発生する場合
- JWKS URL が正しいか確認
- Clerk Dashboard で発行されたトークンの形式を確認
- バックエンドのログで詳細なエラーメッセージを確認

### CORS エラーが発生する場合
- `backend/main.py` の CORS 設定を確認
- フロントエンドの URL が許可リストに含まれているか確認

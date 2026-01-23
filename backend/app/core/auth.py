# backend/app/core/auth.py
"""
Clerk JWT認証モジュール
"""
import os
from typing import Optional

import httpx
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

# Clerk設定
CLERK_JWKS_URL = os.getenv(
    "CLERK_JWKS_URL",
    "https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json"
)

# HTTPBearerスキーム設定
security = HTTPBearer(auto_error=False)

# JWKSキャッシュ（本番環境では適切なキャッシュ機構を使用）
_jwks_cache: Optional[dict] = None


async def get_jwks() -> dict:
    """
    ClerkのJWKS（JSON Web Key Set）を取得する。
    本番環境ではキャッシュ機構を導入すべき。
    """
    global _jwks_cache
    
    if _jwks_cache is not None:
        return _jwks_cache
    
    async with httpx.AsyncClient() as client:
        response = await client.get(CLERK_JWKS_URL)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache


async def verify_clerk_token(token: str) -> dict:
    """
    ClerkのJWTトークンを検証し、ペイロードを返す。
    
    Args:
        token: JWTトークン文字列
        
    Returns:
        dict: デコードされたトークンペイロード
        
    Raises:
        HTTPException: トークンが無効な場合
    """
    try:
        # JWTヘッダーを取得
        unverified_header = jwt.get_unverified_header(token)
        
        # JWKSを取得
        jwks = await get_jwks()
        
        # 対応する公開鍵を検索
        rsa_key = {}
        for key in jwks.get("keys", []):
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
        
        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key"
            )
        
        # JWTを検証してデコード
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False}  # Clerkはaudクレームを使用しない場合がある
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    リクエストヘッダーからJWTトークンを取得し、検証してユーザーIDを返す。
    
    FastAPI依存関数として使用される。
    
    Args:
        credentials: HTTPベアラートークン
        
    Returns:
        str: Clerk User ID
        
    Raises:
        HTTPException: 認証に失敗した場合
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = await verify_clerk_token(token)
    
    # ClerkのUser IDを取得（"sub"クレームに含まれる）
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    return user_id


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    オプショナルな認証用の依存関数。
    認証されていなくてもエラーを投げず、Noneを返す。
    
    Args:
        credentials: HTTPベアラートークン
        
    Returns:
        Optional[str]: Clerk User ID または None
    """
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        payload = await verify_clerk_token(token)
        return payload.get("sub")
    except HTTPException:
        return None

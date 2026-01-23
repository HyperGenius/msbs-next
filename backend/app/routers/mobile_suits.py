"""モビルスーツAPIのエンドポイント定義."""

from typing import Any

from fastapi import APIRouter, Depends
from supabase import Client

from app.db import supabase as supabase_client
from app.models.models import MobileSuitUpdate
from app.services import mobile_suit_service

router = APIRouter(prefix="/api/mobile_suits", tags=["mobile_suits"])


def get_supabase() -> Client:
    """Supabaseクライアントの依存性注入.

    Returns:
        Supabaseクライアントインスタンス
    """
    return supabase_client


@router.get("")
def get_mobile_suits(
    supabase: Client = Depends(get_supabase),
) -> list[dict[str, Any]]:
    """全機体データを取得するエンドポイント.

    Args:
        supabase: 依存性注入されたSupabaseクライアント

    Returns:
        全機体データのリスト
    """
    return mobile_suit_service.get_all_mobile_suits(supabase)


@router.put("/{ms_id}")
def update_mobile_suit(
    ms_id: str,
    data: MobileSuitUpdate,
    supabase: Client = Depends(get_supabase),
) -> dict[str, Any]:
    """指定された機体のデータを更新するエンドポイント.

    Args:
        ms_id: 更新対象の機体UUID
        data: 更新内容
        supabase: 依存性注入されたSupabaseクライアント

    Returns:
        更新後の機体データ
    """
    return mobile_suit_service.update_mobile_suit(supabase, ms_id, data)

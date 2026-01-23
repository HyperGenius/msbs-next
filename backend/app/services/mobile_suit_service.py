"""モビルスーツ関連のビジネスロジックを担当するServiceクラス."""

from typing import Any

from fastapi import HTTPException
from supabase import Client

from app.models.models import MobileSuitUpdate


def get_all_mobile_suits(supabase: Client) -> list[dict[str, Any]]:
    """DBから全機体データを取得する.

    Args:
        supabase: Supabaseクライアント

    Returns:
        全機体データのリスト

    Raises:
        HTTPException: DBからのデータ取得に失敗した場合
    """
    try:
        response = supabase.table("mobile_suits").select("*").execute()
        return response.data  # type: ignore[return-value]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch mobile suits: {str(e)}"
        ) from e


def update_mobile_suit(
    supabase: Client, ms_id: str, data: MobileSuitUpdate
) -> dict[str, Any]:
    """指定された機体のデータを更新する.

    Args:
        supabase: Supabaseクライアント
        ms_id: 更新対象の機体UUID
        data: 更新内容（MobileSuitUpdateモデル）

    Returns:
        更新後の機体データ

    Raises:
        HTTPException: 機体が存在しない、または更新に失敗した場合
    """
    # 更新データをdict化（Noneは除外）
    update_dict = data.model_dump(exclude_none=True)

    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        # データの存在確認
        existing = supabase.table("mobile_suits").select("id").eq("id", ms_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Mobile Suit not found")

        # 更新実行
        response = (
            supabase.table("mobile_suits")
            .update(update_dict)
            .eq("id", ms_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Mobile Suit not found")

        return response.data[0]  # type: ignore[return-value]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update mobile suit: {str(e)}"
        ) from e

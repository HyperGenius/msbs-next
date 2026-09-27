"""設計図APIルーター."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.auth import get_current_user
from app.db import get_session
from app.models.models import BlueprintCollectionItem, PlayerBlueprintResponse
from app.services.blueprint_collection_service import BlueprintCollectionService
from app.services.blueprint_service import BlueprintService

router = APIRouter(prefix="/api/blueprints", tags=["blueprints"])


@router.get("/me", response_model=list[PlayerBlueprintResponse])
async def get_my_blueprints(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> list[PlayerBlueprintResponse]:
    """ログイン中プレイヤーの所持設計図一覧を返す."""
    return BlueprintService.get_player_blueprints(session, user_id)


@router.get("/collection", response_model=list[BlueprintCollectionItem])
async def get_my_blueprint_collection(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> list[BlueprintCollectionItem]:
    """ログイン中プレイヤーの設計図コレクション（図鑑）の一覧を返す."""
    return BlueprintCollectionService.get_collection(session, user_id)

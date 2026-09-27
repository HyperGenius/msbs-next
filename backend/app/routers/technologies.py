"""技術APIルーター."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.auth import get_current_user
from app.db import get_session
from app.models.models import PlayerTechnologyProgress
from app.services.blueprint_collection_service import BlueprintCollectionService

router = APIRouter(prefix="/api/technologies", tags=["technologies"])


@router.get("/me", response_model=list[PlayerTechnologyProgress])
async def get_my_technologies(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> list[PlayerTechnologyProgress]:
    """ログイン中プレイヤーの技術ごとのLv・累計断片数・断片の入手先を返す."""
    return BlueprintCollectionService.get_technologies(session, user_id)

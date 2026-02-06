"""Engineering API router for mobile suit upgrades."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.db import get_session
from app.models.models import MobileSuit, Pilot
from app.services.engineering_service import EngineeringService

router = APIRouter(prefix="/api/engineering", tags=["engineering"])


class UpgradeRequest(BaseModel):
    """Request to upgrade a mobile suit stat."""

    mobile_suit_id: str
    target_stat: str  # "hp", "armor", "mobility", "weapon_power"


class UpgradeResponse(BaseModel):
    """Response from upgrade operation."""

    message: str
    mobile_suit: MobileSuit
    remaining_credits: int
    cost_paid: int


class UpgradePreviewResponse(BaseModel):
    """Preview of what an upgrade would do."""

    mobile_suit_id: str
    stat_type: str
    current_value: int | float
    new_value: int | float
    cost: int
    at_max_cap: bool


@router.post("/upgrade", response_model=UpgradeResponse)
async def upgrade_mobile_suit(
    request: UpgradeRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> UpgradeResponse:
    """Upgrade a specific stat of a mobile suit.

    Args:
        request: Upgrade request with mobile suit ID and target stat
        session: Database session
        user_id: Current user ID from authentication

    Returns:
        UpgradeResponse with updated mobile suit and remaining credits

    Raises:
        HTTPException: If upgrade fails due to various reasons
    """
    # Get pilot
    statement = select(Pilot).where(Pilot.user_id == user_id)
    pilot = session.exec(statement).first()

    if not pilot:
        raise HTTPException(status_code=404, detail="パイロット情報が見つかりません")

    # Initialize service
    service = EngineeringService(session)

    try:
        # Perform upgrade
        updated_ms, updated_pilot, cost = service.upgrade_stat(
            request.mobile_suit_id, request.target_stat, pilot
        )

        return UpgradeResponse(
            message=f"{request.target_stat.upper()} を強化しました！",
            mobile_suit=updated_ms,
            remaining_credits=updated_pilot.credits,
            cost_paid=cost,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/preview/{mobile_suit_id}/{stat_type}", response_model=UpgradePreviewResponse
)
async def get_upgrade_preview(
    mobile_suit_id: str,
    stat_type: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> UpgradePreviewResponse:
    """Get a preview of what an upgrade would do.

    Args:
        mobile_suit_id: ID of the mobile suit
        stat_type: Type of stat to preview
        session: Database session
        user_id: Current user ID from authentication

    Returns:
        UpgradePreviewResponse with cost and value changes

    Raises:
        HTTPException: If preview fails
    """
    service = EngineeringService(session)

    try:
        preview = service.get_upgrade_preview(mobile_suit_id, stat_type)

        return UpgradePreviewResponse(
            mobile_suit_id=mobile_suit_id,
            stat_type=stat_type,
            current_value=preview["current_value"],
            new_value=preview["new_value"],
            cost=preview["cost"],
            at_max_cap=preview["at_max_cap"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

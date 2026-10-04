"""戦域APIルーター."""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db import get_session
from app.models.models import TheaterForecast
from app.services.theater_forecast_service import (
    FORECAST_DEFAULT_DAYS,
    FORECAST_MAX_DAYS,
    FORECAST_MIN_DAYS,
    TheaterForecastService,
)

router = APIRouter(prefix="/api/theaters", tags=["theaters"])


@router.get("/forecast", response_model=list[TheaterForecast])
async def get_theater_forecast(
    days: int = Query(
        default=FORECAST_DEFAULT_DAYS, ge=FORECAST_MIN_DAYS, le=FORECAST_MAX_DAYS
    ),
    session: Session = Depends(get_session),
) -> list[TheaterForecast]:
    """今回と次回以降の開催の戦域・環境・ミノフスキー濃度を返す."""
    return TheaterForecastService.forecast(session, days)

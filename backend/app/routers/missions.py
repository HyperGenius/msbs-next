"""作戦APIルーター."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, col, select

from app.db import get_session
from app.models.models import Mission, TheaterForecast
from app.services.theater_forecast_service import TheaterForecastService

router = APIRouter(prefix="/api/missions", tags=["missions"])


class AvailableMission(BaseModel):
    """次回の開催で出撃できる作戦."""

    id: int
    name: str
    description: str
    difficulty: int
    objective_type: str
    objective_params: dict
    environment: str
    """戦う環境。戦域があれば戦域の環境タイプ、無ければ作戦の既定の環境。"""
    ally_count: int
    enemy_count: int


class AvailableMissionsResponse(BaseModel):
    """次回の開催で出撃できる作戦の一覧と、その開催の戦域."""

    theater: TheaterForecast | None
    """次回の開催の戦域。戦域の無い開催は null。"""
    missions: list[AvailableMission]


@router.get("/available", response_model=AvailableMissionsResponse)
async def get_available_missions(
    session: Session = Depends(get_session),
) -> AvailableMissionsResponse:
    """次回の開催でエントリーできる作戦と、その開催の戦域を返す."""
    forecasts = TheaterForecastService.forecast(session, 1)
    theater = forecasts[0] if forecasts and forecasts[0].is_current else None
    missions = session.exec(
        select(Mission).where(col(Mission.is_active)).order_by(col(Mission.id))
    ).all()
    return AvailableMissionsResponse(
        theater=theater,
        missions=[
            AvailableMission(
                id=mission.id,
                name=mission.name,
                description=mission.description,
                difficulty=mission.difficulty,
                objective_type=mission.objective_config().type,
                objective_params=mission.objective_config().params,
                environment=(
                    theater.environment_id if theater else mission.environment
                ),
                ally_count=len(mission.ally_unit_configs()),
                enemy_count=len(mission.enemy_unit_configs()),
            )
            for mission in missions
        ],
    )

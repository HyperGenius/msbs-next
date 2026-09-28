"""今回と次回以降の開催の戦域予報を作るサービス."""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, select

from app.models.models import (
    MasterEnvironment,
    MasterTheater,
    MinovskyLevel,
    TerrainGrade,
    TheaterForecast,
)
from app.services.battle_room_service import BattleRoomService
from app.services.theater_service import TheaterAssignment, TheaterService

# 濃度がこの値未満なら LOW、MEDIUM_MAX 未満なら MEDIUM、それ以上は HIGH。
MINOVSKY_LEVEL_LOW_MAX = 0.33
MINOVSKY_LEVEL_MEDIUM_MAX = 0.66

FORECAST_MIN_DAYS = 1
FORECAST_MAX_DAYS = 7
FORECAST_DEFAULT_DAYS = 3


def minovsky_level(density: float) -> MinovskyLevel:
    """ミノフスキー濃度を低・中・高の段階にする."""
    if density < MINOVSKY_LEVEL_LOW_MAX:
        return MinovskyLevel.LOW
    if density < MINOVSKY_LEVEL_MEDIUM_MAX:
        return MinovskyLevel.MEDIUM
    return MinovskyLevel.HIGH


class TheaterForecastService:
    """戦域予報サービス."""

    @staticmethod
    def forecast(
        session: Session, days: int, now: datetime | None = None
    ) -> list[TheaterForecast]:
        """今回と、その後 days − 1 回分の開催の予報を返す.

        今回は OPEN ルームに保存された値を返す。ルームが無ければ、作成したときと同じ計算で
        次の開催の値を返す（GET でルームを作らないため）。次回以降は開催日から計算する。
        戦域の無い開催は予報に含めない。
        """
        room = BattleRoomService.find_open_room(session)
        if room is not None:
            current_at = room.scheduled_at
            if current_at.tzinfo is None:
                current_at = current_at.replace(tzinfo=UTC)
            current = TheaterAssignment(
                battle_date=TheaterService.battle_date_of(current_at),
                theater_id=room.theater_id,
                environment_id=None,
                minovsky_density=room.minovsky_density or 0.0,
            )
        else:
            current_at = BattleRoomService.next_scheduled_at(now or datetime.now(UTC))
            current = TheaterService.resolve_for_date(
                session, TheaterService.battle_date_of(current_at)
            )

        upcoming = TheaterService.forecast(
            session, current.battle_date + timedelta(days=1), days - 1
        )
        slots = [(current_at, True, current)] + [
            (current_at + timedelta(days=offset), False, assignment)
            for offset, assignment in enumerate(upcoming, start=1)
        ]

        theaters = TheaterForecastService._theaters_by_id(
            session, {a.theater_id for _, _, a in slots if a.theater_id is not None}
        )
        environments = TheaterForecastService._environments_by_id(
            session, {t.environment_id for t in theaters.values()}
        )

        forecasts: list[TheaterForecast] = []
        for scheduled_at, is_current, assignment in slots:
            theater = theaters.get(assignment.theater_id or "")
            if theater is None:
                continue
            environment = environments.get(theater.environment_id)
            forecasts.append(
                TheaterForecast(
                    scheduled_at=scheduled_at,
                    is_current=is_current,
                    theater_id=theater.id,
                    theater_name=theater.name,
                    environment_id=theater.environment_id,
                    environment_name=(
                        environment.name if environment else theater.environment_id
                    ),
                    default_terrain_grade=(
                        environment.default_terrain_grade
                        if environment
                        else TerrainGrade.A
                    ),
                    minovsky_density=assignment.minovsky_density,
                    minovsky_level=minovsky_level(assignment.minovsky_density),
                    hint=theater.hint,
                    description=theater.description,
                )
            )
        return forecasts

    @staticmethod
    def _theaters_by_id(
        session: Session, theater_ids: set[str]
    ) -> dict[str, MasterTheater]:
        if not theater_ids:
            return {}
        return {
            t.id: t
            for t in session.exec(
                select(MasterTheater).where(col(MasterTheater.id).in_(theater_ids))
            ).all()
        }

    @staticmethod
    def _environments_by_id(
        session: Session, environment_ids: set[str]
    ) -> dict[str, MasterEnvironment]:
        if not environment_ids:
            return {}
        return {
            e.id: e
            for e in session.exec(
                select(MasterEnvironment).where(
                    col(MasterEnvironment.id).in_(environment_ids)
                )
            ).all()
        }

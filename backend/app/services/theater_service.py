"""開催日ごとの戦域とミノフスキー濃度を決めるサービス."""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone

from sqlmodel import Session, col, select

from app.engine.environment import EnvironmentProfile
from app.models.models import BattleField, MasterEnvironment, MasterTheater

JST = timezone(timedelta(hours=9), "JST")

# 開催日と基準日の差でローテーション位置を決める。
# 変えると全開催日の戦域がずれる。
THEATER_ROTATION_EPOCH = date(2026, 1, 1)


@dataclass(frozen=True)
class TheaterAssignment:
    """開催日に割り当てる戦域とミノフスキー濃度."""

    battle_date: date
    theater_id: str | None
    environment_id: str | None
    minovsky_density: float


class TheaterService:
    """戦域サービス."""

    @staticmethod
    def battle_date_of(scheduled_at: datetime) -> date:
        """開催予定時刻の JST の日付を返す。タイムゾーン無しは UTC とみなす."""
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=UTC)
        return scheduled_at.astimezone(JST).date()

    @staticmethod
    def active_theaters(session: Session) -> list[MasterTheater]:
        """ローテーションに含める戦域を巡回順に返す."""
        return list(
            session.exec(
                select(MasterTheater)
                .where(col(MasterTheater.is_active).is_(True))
                .order_by(col(MasterTheater.rotation_order), col(MasterTheater.id))
            ).all()
        )

    @staticmethod
    def roll_minovsky(battle_date: date, theater: MasterTheater) -> float:
        """開催日と戦域から決まるミノフスキー濃度を返す.

        シードが開催日と戦域だけで決まるため、予報の値と実際の値が一致する。
        """
        rng = random.Random(f"{battle_date.isoformat()}:{theater.id}")
        value = rng.uniform(
            theater.base_minovsky - theater.minovsky_variance,
            theater.base_minovsky + theater.minovsky_variance,
        )
        return round(min(max(value, 0.0), 1.0), 2)

    @staticmethod
    def assign(
        theaters: Sequence[MasterTheater], battle_date: date
    ) -> TheaterAssignment:
        """巡回順に並んだ戦域から、開催日の戦域と濃度を決める."""
        if not theaters:
            return TheaterAssignment(
                battle_date=battle_date,
                theater_id=None,
                environment_id=None,
                minovsky_density=0.0,
            )
        index = (battle_date - THEATER_ROTATION_EPOCH).days % len(theaters)
        theater = theaters[index]
        return TheaterAssignment(
            battle_date=battle_date,
            theater_id=theater.id,
            environment_id=theater.environment_id,
            minovsky_density=TheaterService.roll_minovsky(battle_date, theater),
        )

    @staticmethod
    def resolve_for_date(session: Session, battle_date: date) -> TheaterAssignment:
        """開催日の戦域とミノフスキー濃度を決める.

        有効な戦域が無いときは戦域なし（濃度 0）を返す。
        """
        return TheaterService.assign(
            TheaterService.active_theaters(session), battle_date
        )

    @staticmethod
    def forecast(
        session: Session, from_date: date, days: int
    ) -> list[TheaterAssignment]:
        """from_date から days 日分の戦域とミノフスキー濃度を返す."""
        theaters = TheaterService.active_theaters(session)
        return [
            TheaterService.assign(theaters, from_date + timedelta(days=offset))
            for offset in range(days)
        ]

    @staticmethod
    def environment_profile(environment: MasterEnvironment) -> EnvironmentProfile:
        """環境タイプのマスターから、戦闘エンジンに渡すプロファイルを作る."""
        return EnvironmentProfile(
            environment_id=environment.id,
            sensor_range_multiplier=environment.sensor_range_multiplier,
            ranged_accuracy_penalty=environment.ranged_accuracy_penalty,
            ranged_penalty_ref_distance=environment.ranged_penalty_ref_distance,
            default_obstacle_density=environment.default_obstacle_density,
            default_terrain_grade=environment.default_terrain_grade,
        )

    @staticmethod
    def resolve_environment_profile(
        session: Session, environment_id: str | None
    ) -> EnvironmentProfile | None:
        """環境タイプIDからプロファイルを作る。見つからなければ None を返す."""
        if environment_id is None:
            return None
        environment = session.get(MasterEnvironment, environment_id)
        if environment is None:
            return None
        return TheaterService.environment_profile(environment)

    @staticmethod
    def battlefield_for(theater: MasterTheater | None) -> BattleField:
        """戦域の障害物密度を反映した BattleField を返す.

        戦域が密度を指定しないときは obstacle_density を渡さない。
        エンジンが環境タイプの既定値を使う。
        """
        if theater is None or theater.obstacle_density is None:
            return BattleField()
        return BattleField(obstacle_density=theater.obstacle_density)

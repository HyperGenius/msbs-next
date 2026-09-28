"""開催日ごとの戦域と濃度を決め、戦闘と結果表示に使う戦域の情報を返すサービス."""

import logging
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

from sqlmodel import Session, col, select

from app.engine.environment import EnvironmentProfile
from app.models.models import (
    BattleField,
    BattleResult,
    MasterEnvironment,
    MasterTheater,
)

logger = logging.getLogger(__name__)

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


@dataclass(frozen=True)
class BattleConditions:
    """戦闘に適用する戦域の条件.

    既定値は戦域を導入する前の条件（宇宙・濃度0・障害物 MEDIUM）。
    """

    theater_id: str | None = None
    environment: str = "SPACE"
    environment_profile: EnvironmentProfile | None = None
    minovsky_density: float = 0.0
    battlefield: BattleField = field(default_factory=BattleField)

    def simulator_kwargs(self) -> dict[str, Any]:
        """`BattleSimulator` に渡すキーワード引数を返す."""
        return {
            "environment": self.environment,
            "environment_profile": self.environment_profile,
            "minovsky_density": self.minovsky_density,
            "battlefield": self.battlefield,
        }


@dataclass(frozen=True)
class TheaterLabel:
    """バトル結果に表示する戦域と環境タイプの名前."""

    theater_name: str | None = None
    environment_name: str | None = None
    viewer_preset: str | None = None


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

    @staticmethod
    def battle_conditions(
        session: Session, theater_id: str | None, minovsky_density: float | None
    ) -> BattleConditions:
        """戦域と濃度から、戦闘に適用する条件を組み立てる.

        戦域なし、または戦域・環境タイプのマスターが無いときは、既定の条件を返す。
        """
        if theater_id is None:
            return BattleConditions()
        theater = session.get(MasterTheater, theater_id)
        if theater is None:
            logger.warning(
                "戦域 %s が見つかりません。既定の条件で戦闘します。", theater_id
            )
            return BattleConditions()
        profile = TheaterService.resolve_environment_profile(
            session, theater.environment_id
        )
        if profile is None:
            logger.warning(
                "環境タイプ %s が見つかりません。既定の条件で戦闘します。",
                theater.environment_id,
            )
            return BattleConditions()
        return BattleConditions(
            theater_id=theater.id,
            environment=profile.environment_id,
            environment_profile=profile,
            minovsky_density=minovsky_density or 0.0,
            battlefield=TheaterService.battlefield_for(theater),
        )

    @staticmethod
    def labels_for(
        session: Session, battles: Sequence[BattleResult]
    ) -> list[TheaterLabel]:
        """バトル結果ごとに、戦域と環境タイプの名前を返す.

        マスターに無い戦域・環境タイプの名前は None にする。
        クエリは一覧の数によらず最大2回。
        """
        theater_ids = {b.theater_id for b in battles if b.theater_id is not None}
        environment_ids = {b.environment for b in battles}
        theater_names: dict[str, str] = {}
        if theater_ids:
            theater_names = dict(
                session.exec(
                    select(MasterTheater.id, MasterTheater.name).where(
                        col(MasterTheater.id).in_(theater_ids)
                    )
                ).all()
            )
        environments: dict[str, tuple[str, str]] = {}
        if environment_ids:
            for env_id, name, preset in session.exec(
                select(
                    MasterEnvironment.id,
                    MasterEnvironment.name,
                    MasterEnvironment.viewer_preset,
                ).where(col(MasterEnvironment.id).in_(environment_ids))
            ).all():
                environments[env_id] = (name, preset)

        labels: list[TheaterLabel] = []
        for battle in battles:
            environment = environments.get(battle.environment)
            labels.append(
                TheaterLabel(
                    theater_name=theater_names.get(battle.theater_id or ""),
                    environment_name=environment[0] if environment else None,
                    viewer_preset=environment[1] if environment else None,
                )
            )
        return labels

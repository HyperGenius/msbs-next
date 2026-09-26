"""管理者用に、ドロップテーブルの取得と保存を行うサービス."""

from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import and_
from sqlmodel import Session, col, delete, select

from app.models.models import (
    BlueprintTargetSummary,
    BlueprintTargetType,
    DropTable,
    DropTableDetail,
    DropTableEntry,
    DropTableEntryDetail,
    DropTableUpdate,
    MasterBlueprint,
    MasterMobileSuit,
    MasterWeapon,
)
from app.services.drop_service import DropScope, DropService

# テーブルが未作成のときに返す設定。drop_rate が0なのでドロップは起きない。
DEFAULT_TABLE_NAMES = {DropScope.batch(): "定期バトル"}
DEFAULT_DROP_RATE = 0.0
DEFAULT_WIN_RATE_MULTIPLIER = 1.0


class DropTableService:
    """ドロップテーブル管理サービス."""

    @staticmethod
    def get_detail(session: Session, scope: DropScope) -> DropTableDetail:
        """適用範囲のテーブルを、エントリーの表示情報付きで返す.

        テーブルが無ければ、エントリー無しの既定値を返す。
        クエリはエントリー数によらず最大3回。
        """
        table = DropService.find_table(session, scope)
        entries: list[DropTableEntry] = []
        if table is not None:
            entries = list(
                session.exec(
                    select(DropTableEntry)
                    .where(DropTableEntry.drop_table_id == table.id)
                    .order_by(col(DropTableEntry.id))
                ).all()
            )
        summaries = DropTableService._blueprint_summaries(session)

        entry_details = [
            DropTableEntryDetail(
                **summaries[entry.blueprint_id].model_dump(),
                weight=entry.weight,
                requires_win=entry.requires_win,
            )
            for entry in entries
            if entry.blueprint_id in summaries
        ]
        in_table = {entry.blueprint_id for entry in entries}
        unobtainable = [
            summary
            for blueprint_id, summary in summaries.items()
            if not summary.is_standard_issue and blueprint_id not in in_table
        ]

        if table is None:
            return DropTableDetail(
                id=None,
                name=DEFAULT_TABLE_NAMES.get(scope, scope.scope_key),
                drop_rate=DEFAULT_DROP_RATE,
                win_rate_multiplier=DEFAULT_WIN_RATE_MULTIPLIER,
                entries=entry_details,
                unobtainable_blueprints=unobtainable,
            )
        return DropTableDetail(
            id=table.id,
            name=table.name,
            drop_rate=table.drop_rate,
            win_rate_multiplier=table.win_rate_multiplier,
            entries=entry_details,
            unobtainable_blueprints=unobtainable,
        )

    @staticmethod
    def save(
        session: Session, scope: DropScope, data: DropTableUpdate
    ) -> DropTableDetail:
        """適用範囲のテーブルを保存し、保存後の内容を返す.

        テーブルが無ければ作成する。エントリーは `data.entries` で置き換える。

        Raises:
            ValueError: 同じ設計図が2つ以上のエントリーにある場合。
                または設計図マスターに無い設計図がある場合。
        """
        blueprint_ids = [entry.blueprint_id for entry in data.entries]
        duplicated = sorted(
            blueprint_id
            for blueprint_id, count in Counter(blueprint_ids).items()
            if count > 1
        )
        if duplicated:
            raise ValueError(f"Duplicate blueprints: {', '.join(duplicated)}")

        if blueprint_ids:
            existing = set(
                session.exec(
                    select(MasterBlueprint.id).where(
                        col(MasterBlueprint.id).in_(blueprint_ids)
                    )
                ).all()
            )
            missing = sorted(set(blueprint_ids) - existing)
            if missing:
                raise ValueError(f"Blueprints not found: {', '.join(missing)}")

        table = DropService.find_table(session, scope)
        if table is None:
            table = DropTable(
                scope_type=scope.scope_type.value,
                scope_key=scope.scope_key,
                name=data.name,
                drop_rate=data.drop_rate,
                win_rate_multiplier=data.win_rate_multiplier,
            )
        else:
            table.name = data.name
            table.drop_rate = data.drop_rate
            table.win_rate_multiplier = data.win_rate_multiplier
            table.updated_at = datetime.now(UTC)
        session.add(table)
        session.flush()

        session.exec(  # type: ignore[call-overload]
            delete(DropTableEntry).where(col(DropTableEntry.drop_table_id) == table.id)
        )
        for entry in data.entries:
            session.add(
                DropTableEntry(
                    drop_table_id=table.id,
                    blueprint_id=entry.blueprint_id,
                    weight=entry.weight,
                    requires_win=entry.requires_win,
                )
            )
        session.commit()
        return DropTableService.get_detail(session, scope)

    @staticmethod
    def _blueprint_summaries(session: Session) -> dict[str, BlueprintTargetSummary]:
        """全設計図の表示情報を、設計図ID順に返す."""
        rows = session.exec(
            select(MasterBlueprint, MasterMobileSuit, MasterWeapon)
            .outerjoin(
                MasterMobileSuit,
                and_(
                    col(MasterBlueprint.target_type)
                    == BlueprintTargetType.MOBILE_SUIT.value,
                    col(MasterBlueprint.target_id) == col(MasterMobileSuit.id),
                ),
            )
            .outerjoin(
                MasterWeapon,
                and_(
                    col(MasterBlueprint.target_type)
                    == BlueprintTargetType.WEAPON.value,
                    col(MasterBlueprint.target_id) == col(MasterWeapon.id),
                ),
            )
            .order_by(col(MasterBlueprint.id))
        ).all()

        summaries: dict[str, BlueprintTargetSummary] = {}
        for blueprint, mobile_suit, weapon in rows:
            name = blueprint.target_id
            faction = ""
            if mobile_suit is not None:
                name = mobile_suit.name_ja or mobile_suit.name
                faction = mobile_suit.faction
            elif weapon is not None:
                name = weapon.name
            summaries[blueprint.id] = BlueprintTargetSummary(
                blueprint_id=blueprint.id,
                target_type=blueprint.target_type,
                target_id=blueprint.target_id,
                target_name=name,
                faction=faction,
                is_standard_issue=blueprint.is_standard_issue,
            )
        return summaries

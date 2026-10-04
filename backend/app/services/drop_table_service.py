"""管理者用に、ドロップテーブルの取得と保存を行うサービス."""

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_
from sqlmodel import Session, col, delete, select

from app.models.models import (
    BlueprintTargetSummary,
    BlueprintTargetType,
    DropRewardType,
    DropScopeType,
    DropTable,
    DropTableDetail,
    DropTableEntry,
    DropTableEntryDetail,
    DropTableScopeSummary,
    DropTableUpdate,
    MasterBlueprint,
    MasterMobileSuit,
    MasterTechnology,
    MasterTheater,
    MasterWeapon,
)
from app.services.drop_service import DropScope, DropService
from app.services.technology_service import TechnologyService

# 共通テーブルが未作成のときに返す設定。drop_rate が0なのでドロップは起きない。
DEFAULT_TABLE_NAMES = {DropScope.batch(): "定期バトル"}
DEFAULT_DROP_RATE = 0.0
DEFAULT_WIN_RATE_MULTIPLIER = 1.0

COMMON_TABLE_LABEL = "共通テーブル"


class DropTableService:
    """ドロップテーブル管理サービス."""

    @staticmethod
    def list_scopes(session: Session) -> list[DropTableScopeSummary]:
        """共通テーブルと全戦域のテーブルの有無を返す.

        戦域は巡回順に並べる。無効な戦域も含める。
        """
        batch_scope = DropScope.batch()
        theater_table_keys = set(
            session.exec(
                select(DropTable.scope_key).where(
                    DropTable.scope_type == DropScopeType.THEATER.value
                )
            ).all()
        )
        summaries = [
            DropTableScopeSummary(
                scope_type=batch_scope.scope_type.value,
                scope_key=batch_scope.scope_key,
                label=COMMON_TABLE_LABEL,
                is_active=True,
                has_table=DropService.find_table(session, batch_scope) is not None,
            )
        ]
        for theater in session.exec(
            select(MasterTheater).order_by(
                col(MasterTheater.rotation_order), col(MasterTheater.id)
            )
        ).all():
            summaries.append(
                DropTableScopeSummary(
                    scope_type=DropScopeType.THEATER.value,
                    scope_key=theater.id,
                    label=theater.name,
                    is_active=theater.is_active,
                    has_table=theater.id in theater_table_keys,
                )
            )
        return summaries

    @staticmethod
    def get_detail(session: Session, scope: DropScope) -> DropTableDetail:
        """適用範囲のテーブルを、エントリーの表示情報付きで返す.

        共通テーブルが無ければ、エントリー無しの既定値を返す。
        戦域のテーブルが無ければ、共通テーブルの内容を戦域名で返す。
        保存すると、その内容で戦域のテーブルを作成できる。
        クエリはエントリー数によらず最大6回。

        Raises:
            LookupError: 戦域がマスターに無い場合。
        """
        theater_name = DropTableService._theater_name(session, scope)
        table = DropService.find_table(session, scope)
        if table is None and theater_name is not None:
            common = DropTableService.get_detail(session, DropScope.batch())
            return common.model_copy(
                update={"id": None, "name": theater_name, "uses_common_table": True}
            )

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
        tech_names = TechnologyService.tech_names(
            session, [entry.tech_id for entry in entries if entry.tech_id]
        )

        entry_details: list[DropTableEntryDetail] = []
        for entry in entries:
            if entry.reward_type == DropRewardType.TECH_FRAGMENT:
                if entry.tech_id not in tech_names:
                    continue
                entry_details.append(
                    DropTableEntryDetail(
                        reward_type=entry.reward_type,
                        tech_id=entry.tech_id,
                        target_name=tech_names[entry.tech_id],
                        weight=entry.weight,
                        requires_win=entry.requires_win,
                    )
                )
            elif entry.blueprint_id in summaries:
                entry_details.append(
                    DropTableEntryDetail(
                        reward_type=entry.reward_type,
                        **summaries[entry.blueprint_id].model_dump(),
                        weight=entry.weight,
                        requires_win=entry.requires_win,
                    )
                )
        in_table = {entry.blueprint_id for entry in entries if entry.blueprint_id}
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
            LookupError: 戦域がマスターに無い場合。
            ValueError: 同じ設計図・技術が2つ以上のエントリーにある場合。
                または設計図マスター・技術マスターに無いIDがある場合。
        """
        DropTableService._theater_name(session, scope)
        blueprint_ids = [e.blueprint_id for e in data.entries if e.blueprint_id]
        tech_ids = [e.tech_id for e in data.entries if e.tech_id]
        DropTableService._check_references(
            session, "blueprints", blueprint_ids, col(MasterBlueprint.id)
        )
        DropTableService._check_references(
            session, "technologies", tech_ids, col(MasterTechnology.id)
        )

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
                    reward_type=entry.reward_type.value,
                    blueprint_id=entry.blueprint_id,
                    tech_id=entry.tech_id,
                    weight=entry.weight,
                    requires_win=entry.requires_win,
                )
            )
        session.commit()
        return DropTableService.get_detail(session, scope)

    @staticmethod
    def delete_theater_table(session: Session, theater_id: str) -> bool:
        """戦域のテーブルを削除する。以降、その戦域は共通テーブルで抽選する.

        Returns:
            削除したら True。テーブルが無ければ False。
        """
        if not DropTableService.remove_theater_table(session, theater_id):
            return False
        session.commit()
        return True

    @staticmethod
    def remove_theater_table(session: Session, theater_id: str) -> bool:
        """戦域のテーブルとエントリーを削除する。コミットは呼び出し側で行う.

        Returns:
            削除したら True。テーブルが無ければ False。
        """
        table = DropService.find_table(session, DropScope.theater(theater_id))
        if table is None:
            return False
        session.exec(  # type: ignore[call-overload]
            delete(DropTableEntry).where(col(DropTableEntry.drop_table_id) == table.id)
        )
        session.delete(table)
        return True

    @staticmethod
    def _theater_name(session: Session, scope: DropScope) -> str | None:
        """戦域の適用範囲なら戦域名を返す。それ以外は None を返す.

        Raises:
            LookupError: 戦域がマスターに無い場合。
        """
        if scope.scope_type != DropScopeType.THEATER:
            return None
        theater = session.get(MasterTheater, scope.scope_key)
        if theater is None:
            raise LookupError(f"Theater '{scope.scope_key}' not found.")
        return theater.name

    @staticmethod
    def _check_references(
        session: Session, label: str, ids: list[str], id_column: Any
    ) -> None:
        """エントリーのIDに重複が無く、すべてマスターにあることを検証する.

        Raises:
            ValueError: 重複したIDか、マスターに無いIDがある場合。
        """
        duplicated = sorted(i for i, count in Counter(ids).items() if count > 1)
        if duplicated:
            raise ValueError(f"Duplicate {label}: {', '.join(duplicated)}")
        if not ids:
            return
        existing = set(session.exec(select(id_column).where(id_column.in_(ids))).all())
        missing = sorted(set(ids) - existing)
        if missing:
            raise ValueError(f"{label.capitalize()} not found: {', '.join(missing)}")

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

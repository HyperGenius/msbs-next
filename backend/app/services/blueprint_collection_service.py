"""設計図コレクション（図鑑）の一覧を組み立てるサービス."""

from sqlalchemy import and_
from sqlmodel import Session, col, select

from app.core.gamedata import is_available_to_faction
from app.models.models import (
    BlueprintCollectionItem,
    BlueprintTargetType,
    DropScopeType,
    DropTable,
    DropTableEntry,
    MasterBlueprint,
    MasterMobileSuit,
    MasterWeapon,
    ObtainableTheater,
    Pilot,
    PlayerBlueprint,
)
from app.services.drop_service import DropScope

# 戦域マスターが無い間は、定期バトルのテーブルが全戦域で共通になる。
ALL_THEATERS_LABEL = "全戦域"


def theater_label_for(scope: DropScope) -> str | None:
    """ドロップテーブルの適用範囲を、図鑑に表示する戦域名に変換する.

    Returns:
        戦域の表示名。図鑑に出さない適用範囲（ミッション）なら None。
    """
    if scope == DropScope.batch():
        return ALL_THEATERS_LABEL
    return None


class BlueprintCollectionService:
    """設計図コレクションサービス."""

    @staticmethod
    def get_collection(session: Session, user_id: str) -> list[BlueprintCollectionItem]:
        """プレイヤーの図鑑の一覧を、設計図ID順に返す.

        機体・武器マスターが無い設計図は含めない。
        クエリは設計図の数によらず4回。
        """
        pilot_faction = (
            session.exec(select(Pilot.faction).where(Pilot.user_id == user_id)).first()
            or ""
        )
        owned = {
            owned.blueprint_id: owned
            for owned in session.exec(
                select(PlayerBlueprint).where(PlayerBlueprint.user_id == user_id)
            ).all()
        }
        theaters = BlueprintCollectionService._obtainable_theaters(session)

        items: list[BlueprintCollectionItem] = []
        for blueprint, name, faction in BlueprintCollectionService._targets(session):
            owned_blueprint = owned.get(blueprint.id)
            available = is_available_to_faction(pilot_faction, faction)
            show_theaters = (
                available
                and owned_blueprint is None
                and not blueprint.is_standard_issue
            )
            items.append(
                BlueprintCollectionItem(
                    blueprint_id=blueprint.id,
                    target_type=blueprint.target_type,
                    target_id=blueprint.target_id,
                    target_name=name,
                    faction=faction,
                    is_standard_issue=blueprint.is_standard_issue,
                    is_owned=owned_blueprint is not None,
                    acquired_at=owned_blueprint.acquired_at
                    if owned_blueprint
                    else None,
                    source=owned_blueprint.source if owned_blueprint else None,
                    is_available_to_faction=available,
                    obtainable_theaters=(
                        theaters.get(blueprint.id, []) if show_theaters else []
                    ),
                )
            )
        return items

    @staticmethod
    def _targets(session: Session) -> list[tuple[MasterBlueprint, str, str]]:
        """設計図と、対象の表示名・勢力の組を設計図ID順に返す."""
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

        targets: list[tuple[MasterBlueprint, str, str]] = []
        for blueprint, mobile_suit, weapon in rows:
            if mobile_suit is not None:
                targets.append(
                    (
                        blueprint,
                        mobile_suit.name_ja or mobile_suit.name,
                        mobile_suit.faction,
                    )
                )
            elif weapon is not None:
                targets.append((blueprint, weapon.name, ""))
        return targets

    @staticmethod
    def _obtainable_theaters(
        session: Session,
    ) -> dict[str, list[ObtainableTheater]]:
        """設計図IDごとに、入手できる戦域をテーブルID順に返す.

        同じ戦域に変換されるテーブルが複数あれば1件にまとめる。
        どれか1つでも敗北時にドロップするなら、勝利時のみとしない。
        """
        rows = session.exec(
            select(
                DropTableEntry.blueprint_id,
                DropTable.scope_type,
                DropTable.scope_key,
                DropTableEntry.requires_win,
            )
            .join(DropTable, col(DropTable.id) == col(DropTableEntry.drop_table_id))
            .order_by(col(DropTable.id))
        ).all()

        requires_win_by_label: dict[str, dict[str, bool]] = {}
        for blueprint_id, scope_type, scope_key, requires_win in rows:
            label = theater_label_for(DropScope(DropScopeType(scope_type), scope_key))
            if label is None:
                continue
            by_label = requires_win_by_label.setdefault(blueprint_id, {})
            by_label[label] = by_label.get(label, True) and requires_win

        return {
            blueprint_id: [
                ObtainableTheater(label=label, requires_win=requires_win)
                for label, requires_win in by_label.items()
            ]
            for blueprint_id, by_label in requires_win_by_label.items()
        }

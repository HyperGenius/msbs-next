"""設計図コレクション（図鑑）と技術Lvの一覧を組み立てるサービス."""

from typing import Any

from sqlalchemy import and_
from sqlmodel import Session, col, select

from app.core.gamedata import is_available_to_faction
from app.models.models import (
    BlueprintCollectionItem,
    BlueprintTargetType,
    DropTable,
    DropTableEntry,
    MasterBlueprint,
    MasterMobileSuit,
    MasterTechnology,
    MasterWeapon,
    ObtainableTheater,
    Pilot,
    PlayerBlueprint,
    PlayerTechnologyProgress,
    TechRequirementStatus,
)
from app.services.drop_source_service import TheaterDropSources
from app.services.technology_service import TechnologyService


class BlueprintCollectionService:
    """設計図コレクションサービス."""

    @staticmethod
    def get_collection(session: Session, user_id: str) -> list[BlueprintCollectionItem]:
        """プレイヤーの図鑑の一覧を、設計図ID順に返す.

        機体・武器マスターが無い設計図は含めない。
        クエリは設計図の数によらず8回。
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
        theaters = BlueprintCollectionService._obtainable_theaters(
            session, col(DropTableEntry.blueprint_id)
        )
        requirements = TechnologyService.requirements_by_blueprint(session)
        tech_names = TechnologyService.tech_names(session)
        levels = TechnologyService.levels_by_tech(session, user_id)

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
                    tech_requirements=[]
                    if blueprint.is_standard_issue
                    else [
                        TechRequirementStatus(
                            tech_id=r.tech_id,
                            tech_name=tech_names.get(r.tech_id, r.tech_id),
                            required_lv=r.required_lv,
                            current_lv=levels.get(r.tech_id, 0),
                        )
                        for r in requirements.get(blueprint.id, [])
                    ],
                )
            )
        return items

    @staticmethod
    def get_technologies(
        session: Session, user_id: str
    ) -> list[PlayerTechnologyProgress]:
        """プレイヤーの技術ごとの進捗と、断片の入手先を技術ID順に返す.

        クエリは技術の数によらず4回。
        """
        counts = TechnologyService.fragment_counts(session, user_id)
        theaters = BlueprintCollectionService._obtainable_theaters(
            session, col(DropTableEntry.tech_id)
        )
        progresses: list[PlayerTechnologyProgress] = []
        for tech in session.exec(
            select(MasterTechnology).order_by(col(MasterTechnology.id))
        ).all():
            count = counts.get(tech.id, 0)
            progress = TechnologyService.progress(tech.level_thresholds, count)
            progresses.append(
                PlayerTechnologyProgress(
                    tech_id=tech.id,
                    name=tech.name,
                    description=tech.description,
                    level=progress.level,
                    max_level=progress.max_level,
                    fragment_count=count,
                    next_level_threshold=progress.next_level_threshold,
                    fragments_to_next_level=progress.fragments_to_next_level,
                    overflow_credit_value=tech.overflow_credit_value,
                    obtainable_theaters=theaters.get(tech.id, []),
                )
            )
        return progresses

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
        session: Session, reward_key: Any
    ) -> dict[str, list[ObtainableTheater]]:
        """報酬のIDごとに、入手できる有効な戦域を巡回順に返す.

        `reward_key` に DropTableEntry.blueprint_id を渡すと設計図IDごと、
        tech_id を渡すと技術IDごとに集計する。
        同じ戦域が複数のテーブルにあれば1件にまとめる。
        どれか1つでも敗北時にドロップするなら、勝利時のみとしない。
        """
        sources = TheaterDropSources.load(session)
        rows = session.exec(
            select(
                reward_key,
                DropTable.scope_type,
                DropTable.scope_key,
                DropTableEntry.requires_win,
            )
            .join(DropTable, col(DropTable.id) == col(DropTableEntry.drop_table_id))
            .where(reward_key.is_not(None))
            .order_by(col(DropTable.id))
        ).all()

        # 報酬ID → 戦域名 → (表示順, 勝利時のみか)
        by_reward: dict[str, dict[str, tuple[int, bool]]] = {}
        for reward_id, scope_type, scope_key, requires_win in rows:
            for source in sources.sources_for(scope_type, scope_key):
                by_label = by_reward.setdefault(reward_id, {})
                _, win_only = by_label.get(source.label, (source.order, True))
                by_label[source.label] = (source.order, win_only and requires_win)

        return {
            reward_id: [
                ObtainableTheater(label=label, requires_win=requires_win)
                for label, (_, requires_win) in sorted(
                    by_label.items(), key=lambda item: item[1][0]
                )
            ]
            for reward_id, by_label in by_reward.items()
        }

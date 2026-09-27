"""戦利品に表示用の名前を付けるサービス."""

from collections.abc import Iterable, Sequence

from sqlmodel import Session, col, select

from app.models.models import (
    BattleResult,
    BattleResultSummary,
    BlueprintTargetType,
    LootItem,
    LootItemDetail,
    LootKind,
    MasterMobileSuit,
    MasterWeapon,
)
from app.services.technology_service import TechnologyService

TargetKey = tuple[str, str]


class LootService:
    """戦利品の表示情報サービス."""

    @staticmethod
    def with_names(
        session: Session,
        loots: Sequence[Sequence[LootItem | dict] | None],
    ) -> list[list[LootItemDetail] | None]:
        """戦利品の一覧ごとに、表示名を付けて返す.

        名前は保存済みの loot に書き込まず、機体・武器・技術マスターから引く。
        導入済みのバトル結果にも名前を付けるため。
        クエリは一覧の数によらず最大3回。

        Returns:
            `loots` と同じ順序の一覧。`None`（導入前のバトル）は `None` のまま返す。
        """
        parsed = [
            None if loot is None else [LootItem.model_validate(item) for item in loot]
            for loot in loots
        ]
        items = [item for loot in parsed if loot for item in loot]
        names = LootService._target_names(session, items)
        tech_names = TechnologyService.tech_names(
            session,
            sorted(
                {
                    item.tech_id
                    for item in items
                    if item.kind == LootKind.TECH_FRAGMENT and item.tech_id
                }
            ),
        )

        def name_of(item: LootItem) -> str:
            if item.kind == LootKind.TECH_FRAGMENT:
                return tech_names.get(item.tech_id or "", item.tech_id or "")
            return names.get(
                (item.target_type or "", item.target_id or ""), item.target_id or ""
            )

        return [
            None
            if loot is None
            else [
                LootItemDetail(**item.model_dump(), target_name=name_of(item))
                for item in loot
            ]
            for loot in parsed
        ]

    @staticmethod
    def summaries(
        session: Session, battles: Sequence[BattleResult]
    ) -> list[BattleResultSummary]:
        """バトル結果を、戦利品の名前付きのサマリーにして返す."""
        loots = LootService.with_names(session, [battle.loot for battle in battles])
        return [
            BattleResultSummary.model_validate(battle, update={"loot": loot})
            for battle, loot in zip(battles, loots, strict=True)
        ]

    @staticmethod
    def _target_names(
        session: Session, items: Iterable[LootItem]
    ) -> dict[TargetKey, str]:
        mobile_suit_ids: set[str] = set()
        weapon_ids: set[str] = set()
        for item in items:
            if item.target_id is None:
                continue
            if item.target_type == BlueprintTargetType.MOBILE_SUIT:
                mobile_suit_ids.add(item.target_id)
            elif item.target_type == BlueprintTargetType.WEAPON:
                weapon_ids.add(item.target_id)

        names: dict[TargetKey, str] = {}
        if mobile_suit_ids:
            mobile_suits = session.exec(
                select(
                    MasterMobileSuit.id, MasterMobileSuit.name, MasterMobileSuit.name_ja
                ).where(col(MasterMobileSuit.id).in_(mobile_suit_ids))
            ).all()
            for ms_id, name, name_ja in mobile_suits:
                names[(BlueprintTargetType.MOBILE_SUIT.value, ms_id)] = name_ja or name
        if weapon_ids:
            weapons = session.exec(
                select(MasterWeapon.id, MasterWeapon.name).where(
                    col(MasterWeapon.id).in_(weapon_ids)
                )
            ).all()
            for weapon_id, name in weapons:
                names[(BlueprintTargetType.WEAPON.value, weapon_id)] = name
        return names

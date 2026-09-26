"""戦利品に表示用の対象の名前を付けるサービス."""

from collections.abc import Iterable, Sequence

from sqlmodel import Session, col, select

from app.models.models import (
    BattleResult,
    BattleResultSummary,
    BlueprintTargetType,
    LootItem,
    LootItemDetail,
    MasterMobileSuit,
    MasterWeapon,
)

TargetKey = tuple[str, str]


class LootService:
    """戦利品の表示情報サービス."""

    @staticmethod
    def with_names(
        session: Session,
        loots: Sequence[Sequence[LootItem | dict] | None],
    ) -> list[list[LootItemDetail] | None]:
        """戦利品の一覧ごとに、対象の名前を付けて返す.

        名前は保存済みの loot に書き込まず、機体・武器マスターから引く。
        導入済みのバトル結果にも名前を付けるため。
        クエリは一覧の数によらず最大2回。

        Returns:
            `loots` と同じ順序の一覧。`None`（導入前のバトル）は `None` のまま返す。
        """
        parsed = [
            None if loot is None else [LootItem.model_validate(item) for item in loot]
            for loot in loots
        ]
        names = LootService._target_names(
            session, (item for loot in parsed if loot for item in loot)
        )
        return [
            None
            if loot is None
            else [
                LootItemDetail(
                    **item.model_dump(),
                    target_name=names.get(
                        (item.target_type, item.target_id), item.target_id
                    ),
                )
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

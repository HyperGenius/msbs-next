"""バトル終了時の戦利品の抽選と付与を行うサービス."""

import random
import uuid
from dataclasses import dataclass

from sqlalchemy import and_
from sqlmodel import Session, col, select

from app.core.gamedata import is_available_to_faction
from app.models.models import (
    BlueprintSource,
    BlueprintTargetType,
    DropScopeType,
    DropTable,
    DropTableEntry,
    LootItem,
    LootKind,
    MasterBlueprint,
    MasterMobileSuit,
    Pilot,
)
from app.services.blueprint_service import BlueprintService

# 定期バトルにはミッションも戦闘環境も無いため、全ルームで1つのテーブルを共有する。
BATCH_SCOPE_KEY = "default"


@dataclass(frozen=True)
class DropScope:
    """ドロップテーブルを選ぶための、戦闘の適用範囲."""

    scope_type: DropScopeType
    scope_key: str

    @classmethod
    def mission(cls, mission_id: int) -> "DropScope":
        """ソロミッションの適用範囲を返す."""
        return cls(DropScopeType.MISSION, str(mission_id))

    @classmethod
    def batch(cls) -> "DropScope":
        """定期バトルの適用範囲を返す."""
        return cls(DropScopeType.BATCH, BATCH_SCOPE_KEY)


@dataclass(frozen=True)
class _Candidate:
    blueprint_id: str
    target_type: str
    target_id: str
    weight: int


class DropService:
    """ドロップ抽選サービス."""

    @staticmethod
    def effective_drop_rate(table: DropTable, is_win: bool) -> float:
        """勝敗を反映したドロップ率を返す."""
        if not is_win:
            return table.drop_rate
        return min(table.drop_rate * table.win_rate_multiplier, 1.0)

    @staticmethod
    def find_table(session: Session, scope: DropScope) -> DropTable | None:
        """適用範囲のドロップテーブルを返す."""
        return session.exec(
            select(DropTable).where(
                DropTable.scope_type == scope.scope_type.value,
                DropTable.scope_key == scope.scope_key,
            )
        ).first()

    @staticmethod
    def roll(
        session: Session,
        user_id: str,
        scope: DropScope,
        is_win: bool,
        battle_result_id: uuid.UUID,
        rng: random.Random,
    ) -> list[LootItem]:
        """プレイヤー1人分の戦利品を抽選し、設計図を付与する.

        ドロップは1回のバトルで最大1個。コミットは呼び出し側で行う。

        Args:
            session: DBセッション
            user_id: 抽選するプレイヤー。NPC なら抽選しない
            scope: 戦闘の適用範囲。対応するテーブルが無ければドロップしない
            is_win: 勝利したか。DRAW は敗北として渡す
            battle_result_id: 所持設計図の `source_battle_id` に記録するバトル結果ID
            rng: 抽選に使う乱数生成器

        Returns:
            得た戦利品。ドロップしなければ空のリスト。
        """
        pilot = session.exec(select(Pilot).where(Pilot.user_id == user_id)).first()
        if pilot is None or pilot.is_npc:
            return []

        table = DropService.find_table(session, scope)
        if table is None:
            return []

        if rng.random() >= DropService.effective_drop_rate(table, is_win):
            return []

        candidates = DropService._candidates(session, table, pilot.faction, is_win)
        if not candidates:
            return []

        chosen = rng.choices(candidates, weights=[c.weight for c in candidates])[0]
        grant = BlueprintService.grant_blueprint(
            session,
            user_id,
            chosen.blueprint_id,
            BlueprintSource.DROP,
            source_battle_id=battle_result_id,
        )
        return [
            LootItem(
                kind=LootKind.BLUEPRINT.value,
                blueprint_id=grant.blueprint_id,
                target_type=chosen.target_type,
                target_id=chosen.target_id,
                is_new=grant.is_new,
                credits_awarded=grant.credits_awarded,
            )
        ]

    @staticmethod
    def _candidates(
        session: Session, table: DropTable, pilot_faction: str, is_win: bool
    ) -> list[_Candidate]:
        statement = (
            select(DropTableEntry, MasterBlueprint, MasterMobileSuit.faction)
            .join(
                MasterBlueprint,
                col(DropTableEntry.blueprint_id) == col(MasterBlueprint.id),
            )
            .outerjoin(
                MasterMobileSuit,
                and_(
                    col(MasterBlueprint.target_type)
                    == BlueprintTargetType.MOBILE_SUIT.value,
                    col(MasterBlueprint.target_id) == col(MasterMobileSuit.id),
                ),
            )
            .where(DropTableEntry.drop_table_id == table.id)
            # 抽選結果を乱数のシードだけで決めるため、候補の順序を固定する。
            .order_by(col(DropTableEntry.blueprint_id))
        )
        if not is_win:
            statement = statement.where(col(DropTableEntry.requires_win).is_(False))

        return [
            _Candidate(
                blueprint_id=entry.blueprint_id,
                target_type=blueprint.target_type,
                target_id=blueprint.target_id,
                weight=entry.weight,
            )
            for entry, blueprint, faction in session.exec(statement).all()
            if is_available_to_faction(pilot_faction, faction or "")
        ]

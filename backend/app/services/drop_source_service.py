"""ドロップテーブルを、そのテーブルで抽選する戦域の表示名に変換するサービス."""

from dataclasses import dataclass

from sqlalchemy import and_
from sqlmodel import Session, col, select

from app.models.models import DropScopeType, DropTable, MasterTheater

# 有効な戦域がすべて共通テーブルを使うときの表示名。
ALL_THEATERS_LABEL = "全戦域"


@dataclass(frozen=True)
class TheaterSource:
    """ドロップテーブルで抽選する戦域の表示名."""

    label: str
    order: int
    """表示順。戦域の巡回順で、全戦域は先頭にする。"""


@dataclass(frozen=True)
class TheaterDropSources:
    """有効な戦域と、自分のテーブルを持つ戦域の一覧."""

    active_theaters: tuple[tuple[str, str], ...]
    """有効な戦域のIDと名前の組。巡回順に並ぶ。"""
    theaters_with_table: frozenset[str]

    @classmethod
    def load(cls, session: Session) -> "TheaterDropSources":
        """有効な戦域と、そのテーブルの有無を1回のクエリで読む."""
        rows = session.exec(
            select(MasterTheater.id, MasterTheater.name, DropTable.id)
            .outerjoin(
                DropTable,
                and_(
                    col(DropTable.scope_type) == DropScopeType.THEATER.value,
                    col(DropTable.scope_key) == col(MasterTheater.id),
                ),
            )
            .where(col(MasterTheater.is_active).is_(True))
            .order_by(col(MasterTheater.rotation_order), col(MasterTheater.id))
        ).all()
        return cls(
            active_theaters=tuple((theater_id, name) for theater_id, name, _ in rows),
            theaters_with_table=frozenset(
                theater_id for theater_id, _, table_id in rows if table_id is not None
            ),
        )

    def sources_for(self, scope_type: str, scope_key: str) -> list[TheaterSource]:
        """テーブルで抽選する有効な戦域を返す.

        戦域のテーブルは、その戦域が有効なときだけ返す。
        共通テーブルは、自分のテーブルを持たない有効な戦域を返す。
        すべての有効な戦域が共通テーブルを使うなら、全戦域の1件にまとめる。
        ミッションのテーブルは定期バトルで使わないため、空のリストを返す。
        """
        if scope_type == DropScopeType.THEATER.value:
            return [
                TheaterSource(label=name, order=order)
                for order, (theater_id, name) in enumerate(self.active_theaters)
                if theater_id == scope_key
            ]
        if scope_type != DropScopeType.BATCH.value:
            return []
        using_common = [
            TheaterSource(label=name, order=order)
            for order, (theater_id, name) in enumerate(self.active_theaters)
            if theater_id not in self.theaters_with_table
        ]
        # 有効な戦域が無いときも全戦域にする。ルームは戦域なしで共通テーブルを使う。
        if len(using_common) == len(self.active_theaters):
            return [TheaterSource(label=ALL_THEATERS_LABEL, order=-1)]
        return using_common

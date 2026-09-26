"""add_active_mobile_suit_id_to_pilots.

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-09-26

Note:
    NPC パイロットの出撃機体を明示的に保持するカラムを追加する (Issue #542)。
    select_npcs_for_room() は ORDER BY なしで取得した所有機体の先頭を出撃させて
    いたため、複数機所有の NPC では出撃機体が不定だった。

    既存 NPC は所有機体が1機のみのため、所有機体がちょうど1機の NPC パイロットに
    その機体 ID をバックフィルする。2機以上所有する NPC は NULL のまま残し、
    次回マッチング時に所有機から1機が選ばれて保存される。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0a1b2c3d4e5"
down_revision: str | Sequence[str] | None = "e9f0a1b2c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FK_NAME = "pilots_active_mobile_suit_id_fkey"


def upgrade() -> None:
    """Add pilots.active_mobile_suit_id and backfill NPC pilots."""
    op.add_column(
        "pilots",
        sa.Column("active_mobile_suit_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        FK_NAME,
        "pilots",
        "mobile_suits",
        ["active_mobile_suit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE pilots
        SET active_mobile_suit_id = owned.suit_id
        FROM (
            SELECT user_id, (array_agg(id))[1] AS suit_id
            FROM mobile_suits
            WHERE side = 'ENEMY' AND user_id IS NOT NULL
            GROUP BY user_id
            HAVING COUNT(*) = 1
        ) AS owned
        WHERE pilots.is_npc = TRUE
          AND pilots.user_id = owned.user_id
        """
    )


def downgrade() -> None:
    """Drop pilots.active_mobile_suit_id."""
    op.drop_constraint(FK_NAME, "pilots", type_="foreignkey")
    op.drop_column("pilots", "active_mobile_suit_id")

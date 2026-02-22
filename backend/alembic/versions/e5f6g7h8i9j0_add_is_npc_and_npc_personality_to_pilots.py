"""add_is_npc_and_npc_personality_to_pilots.

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-02-22 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6g7h8i9j0"
down_revision: str | None = "d4e5f6g7h8i9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add is_npc and npc_personality fields to pilots table."""
    op.add_column(
        "pilots",
        sa.Column("is_npc", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_pilots_is_npc", "pilots", ["is_npc"])
    op.add_column(
        "pilots",
        sa.Column("npc_personality", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Remove is_npc and npc_personality fields from pilots table."""
    op.drop_column("pilots", "npc_personality")
    op.drop_index("ix_pilots_is_npc", table_name="pilots")
    op.drop_column("pilots", "is_npc")

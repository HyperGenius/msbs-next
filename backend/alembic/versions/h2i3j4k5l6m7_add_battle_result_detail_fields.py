"""add_battle_result_detail_fields.

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-02-28 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h2i3j4k5l6m7"
down_revision: str | Sequence[str] | None = "g1h2i3j4k5l6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "battle_results",
        sa.Column("ms_snapshot", sa.JSON(), nullable=True),
    )
    op.add_column(
        "battle_results",
        sa.Column("kills", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "battle_results",
        sa.Column("exp_gained", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "battle_results",
        sa.Column("credits_gained", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "battle_results",
        sa.Column("level_before", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "battle_results",
        sa.Column("level_after", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "battle_results",
        sa.Column("level_up", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "battle_results",
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_battle_results_is_read", "battle_results", ["is_read"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_battle_results_is_read", table_name="battle_results")
    op.drop_column("battle_results", "is_read")
    op.drop_column("battle_results", "level_up")
    op.drop_column("battle_results", "level_after")
    op.drop_column("battle_results", "level_before")
    op.drop_column("battle_results", "credits_gained")
    op.drop_column("battle_results", "exp_gained")
    op.drop_column("battle_results", "kills")
    op.drop_column("battle_results", "ms_snapshot")

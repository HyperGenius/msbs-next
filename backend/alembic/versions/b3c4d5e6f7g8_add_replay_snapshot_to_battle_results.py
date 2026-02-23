"""add_replay_snapshot_to_battle_results.

Revision ID: b3c4d5e6f7g8
Revises: a2b3c4d5e6f7
Create Date: 2026-02-23 07:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7g8"
down_revision: str | Sequence[str] | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "battle_results",
        sa.Column(
            "environment",
            sqlmodel.sql.sqltypes.AutoString(),
            server_default="SPACE",
            nullable=False,
        ),
    )
    op.add_column(
        "battle_results",
        sa.Column("player_info", sa.JSON(), nullable=True),
    )
    op.add_column(
        "battle_results",
        sa.Column("enemies_info", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("battle_results", "enemies_info")
    op.drop_column("battle_results", "player_info")
    op.drop_column("battle_results", "environment")

"""add_obstacles_info_to_battle_results.

Revision ID: c5d6e7f8g9h0
Revises: b3c4d5e6f7g8
Create Date: 2026-05-14 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5d6e7f8g9h0"
down_revision: str | Sequence[str] | None = "b3c4d5e6f7g8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "battle_results",
        sa.Column("obstacles_info", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("battle_results", "obstacles_info")

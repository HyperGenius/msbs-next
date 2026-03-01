"""add_faction_to_pilots.

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-03-01 08:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i3j4k5l6m7n8"
down_revision: str | None = "h2i3j4k5l6m7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add faction field to pilots table."""
    op.add_column(
        "pilots",
        sa.Column("faction", sa.String(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    """Remove faction field from pilots table."""
    op.drop_column("pilots", "faction")

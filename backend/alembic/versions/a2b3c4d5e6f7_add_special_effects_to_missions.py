"""add_special_effects_to_missions.

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-02-23 14:35:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "missions",
        sa.Column(
            "special_effects",
            sa.JSON(),
            nullable=True,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("missions", "special_effects")

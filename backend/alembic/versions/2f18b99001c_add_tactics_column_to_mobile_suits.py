"""add_tactics_column_to_mobile_suits.

Revision ID: 2f18b99001c
Revises: 27a590afd0ec
Create Date: 2026-02-05 04:49:05.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2f18b99001c"
down_revision: str | Sequence[str] | None = "27a590afd0ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add tactics column with default value
    op.add_column(
        "mobile_suits",
        sa.Column(
            "tactics",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default='{"priority": "CLOSEST", "range": "BALANCED"}',
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove tactics column
    op.drop_column("mobile_suits", "tactics")

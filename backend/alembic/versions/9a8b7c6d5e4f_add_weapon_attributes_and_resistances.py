"""add_weapon_attributes_and_resistances.

Revision ID: 9a8b7c6d5e4f
Revises: 2f18b99001c
Create Date: 2026-02-07 06:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a8b7c6d5e4f"
down_revision: str | Sequence[str] | None = "2f18b99001c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add resistance columns to mobile_suits table
    op.add_column(
        "mobile_suits",
        sa.Column(
            "beam_resistance",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "physical_resistance",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove resistance columns
    op.drop_column("mobile_suits", "physical_resistance")
    op.drop_column("mobile_suits", "beam_resistance")

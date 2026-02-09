"""add_combat_resource_management.

Revision ID: a1b2c3d4e5f6
Revises: 9a8b7c6d5e4f
Create Date: 2026-02-08 07:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "9a8b7c6d5e4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add resource management columns to mobile_suits table
    op.add_column(
        "mobile_suits",
        sa.Column(
            "max_en",
            sa.Integer(),
            nullable=False,
            server_default="1000",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "en_recovery",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "max_propellant",
            sa.Integer(),
            nullable=False,
            server_default="1000",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove resource management columns
    op.drop_column("mobile_suits", "max_propellant")
    op.drop_column("mobile_suits", "en_recovery")
    op.drop_column("mobile_suits", "max_en")

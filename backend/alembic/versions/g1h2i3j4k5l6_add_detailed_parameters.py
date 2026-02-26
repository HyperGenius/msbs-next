"""add_detailed_parameters.

Revision ID: g1h2i3j4k5l6
Revises: c4d5e6f7g8h9
Create Date: 2026-02-26 04:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: str | Sequence[str] | None = "c4d5e6f7g8h9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "mobile_suits",
        sa.Column(
            "melee_aptitude",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "shooting_aptitude",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "accuracy_bonus",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "evasion_bonus",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "acceleration_bonus",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "turning_bonus",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("mobile_suits", "turning_bonus")
    op.drop_column("mobile_suits", "acceleration_bonus")
    op.drop_column("mobile_suits", "evasion_bonus")
    op.drop_column("mobile_suits", "accuracy_bonus")
    op.drop_column("mobile_suits", "shooting_aptitude")
    op.drop_column("mobile_suits", "melee_aptitude")

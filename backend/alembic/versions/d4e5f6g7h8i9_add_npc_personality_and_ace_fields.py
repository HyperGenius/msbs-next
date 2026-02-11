"""add_npc_personality_and_ace_fields.

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-02-11 08:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: str | None = "c3d4e5f6g7h8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add NPC personality and ace pilot fields to mobile_suits table."""
    # Add personality field
    op.add_column("mobile_suits", sa.Column("personality", sa.String(), nullable=True))

    # Add ace pilot fields
    op.add_column(
        "mobile_suits",
        sa.Column("is_ace", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("mobile_suits", sa.Column("ace_id", sa.String(), nullable=True))
    op.add_column("mobile_suits", sa.Column("pilot_name", sa.String(), nullable=True))
    op.add_column(
        "mobile_suits",
        sa.Column("bounty_exp", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "mobile_suits",
        sa.Column("bounty_credits", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Remove NPC personality and ace pilot fields from mobile_suits table."""
    op.drop_column("mobile_suits", "personality")
    op.drop_column("mobile_suits", "is_ace")
    op.drop_column("mobile_suits", "ace_id")
    op.drop_column("mobile_suits", "pilot_name")
    op.drop_column("mobile_suits", "bounty_exp")
    op.drop_column("mobile_suits", "bounty_credits")

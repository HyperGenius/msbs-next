"""add_pilot_skill_fields.

Revision ID: 7b8c9d0e1f2a
Revises: 6a7b8c9d0e1f
Create Date: 2026-02-06 08:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b8c9d0e1f2a"
down_revision: str | Sequence[str] | None = "6a7b8c9d0e1f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add skill_points column
    op.add_column(
        "pilots",
        sa.Column("skill_points", sa.Integer(), nullable=False, server_default="0"),
    )
    # Add skills column (JSON)
    op.add_column(
        "pilots",
        sa.Column("skills", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    # Set default value for existing rows
    op.execute("UPDATE pilots SET skills = '{}' WHERE skills IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("pilots", "skills")
    op.drop_column("pilots", "skill_points")

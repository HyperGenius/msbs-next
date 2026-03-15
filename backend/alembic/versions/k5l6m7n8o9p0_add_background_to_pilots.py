"""add_background_to_pilots.

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-03-14 08:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k5l6m7n8o9p0"
down_revision: str | None = "j4k5l6m7n8o9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """パイロットテーブルに経歴フィールドを追加する."""
    op.add_column(
        "pilots",
        sa.Column("background", sa.String(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    """パイロットテーブルから経歴フィールドを削除する."""
    op.drop_column("pilots", "background")

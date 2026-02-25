"""add team_id to mobile_suits.

Revision ID: c4d5e6f7g8h9
Revises: b3c4d5e6f7g8
Create Date: 2026-02-25 13:08:56.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7g8h9"
down_revision: str | Sequence[str] | None = "b3c4d5e6f7g8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade: mobile_suitsテーブルにteam_idカラムを追加."""
    op.add_column(
        "mobile_suits",
        sa.Column(
            "team_id",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade: mobile_suitsテーブルからteam_idカラムを削除."""
    op.drop_column("mobile_suits", "team_id")

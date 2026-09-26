"""add_master_mobile_suit_id_to_mobile_suits.

Revision ID: h2c3d4e5f6a7
Revises: g1b2c3d4e5f6
Create Date: 2026-09-26

Note:
    機体がどの機体マスターから作られたかを記録するカラムを追加する (Issue #545)。
    機体マスターを削除しても機体を残すため FK は張らない。
    既存の機体はマスターと紐付かないため、バックフィルせず NULL のまま残す。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "g1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add mobile_suits.master_mobile_suit_id."""
    op.add_column(
        "mobile_suits",
        sa.Column("master_mobile_suit_id", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Drop mobile_suits.master_mobile_suit_id."""
    op.drop_column("mobile_suits", "master_mobile_suit_id")

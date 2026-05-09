"""add_body_turn_rate_to_mobile_suits.

Revision ID: p0q1r2s3t4u5
Revises: o9p0q1r2s3t4
Create Date: 2026-05-09

Note:
    MobileSuit モデルに胴体旋回速度パラメータを追加する (Phase 6-1)。
    - body_turn_rate: 胴体（砲塔）の最大旋回速度 (deg/s) (デフォルト: 720.0)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "p0q1r2s3t4u5"
down_revision: str | None = "o9p0q1r2s3t4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add body_turn_rate column to mobile_suits table."""
    op.add_column(
        "mobile_suits",
        sa.Column(
            "body_turn_rate",
            sa.Float(),
            nullable=False,
            server_default="720.0",
        ),
    )


def downgrade() -> None:
    """Remove body_turn_rate column from mobile_suits table."""
    op.drop_column("mobile_suits", "body_turn_rate")

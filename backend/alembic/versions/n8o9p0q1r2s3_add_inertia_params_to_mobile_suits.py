"""add_inertia_params_to_mobile_suits.

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2026-04-28

Note:
    MobileSuit モデルに慣性モデル用の物理パラメータを追加する (Phase 3-1)。
    - max_speed: 最大速度 (m/s)
    - acceleration: 加速度 (m/s²)
    - deceleration: 減速度 (m/s²)
    - max_turn_rate: 最大旋回速度 (deg/s)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n8o9p0q1r2s3"
down_revision: str | None = "m7n8o9p0q1r2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add inertia physics columns to mobile_suits table."""
    op.add_column(
        "mobile_suits",
        sa.Column(
            "max_speed",
            sa.Float(),
            nullable=False,
            server_default="80.0",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "acceleration",
            sa.Float(),
            nullable=False,
            server_default="30.0",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "deceleration",
            sa.Float(),
            nullable=False,
            server_default="50.0",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "max_turn_rate",
            sa.Float(),
            nullable=False,
            server_default="360.0",
        ),
    )


def downgrade() -> None:
    """Remove inertia physics columns from mobile_suits table."""
    op.drop_column("mobile_suits", "max_turn_rate")
    op.drop_column("mobile_suits", "deceleration")
    op.drop_column("mobile_suits", "acceleration")
    op.drop_column("mobile_suits", "max_speed")

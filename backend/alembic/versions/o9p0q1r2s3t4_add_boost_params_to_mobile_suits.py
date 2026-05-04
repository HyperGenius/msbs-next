"""add_boost_params_to_mobile_suits.

Revision ID: o9p0q1r2s3t4
Revises: n8o9p0q1r2s3
Create Date: 2026-05-04

Note:
    MobileSuit モデルにブーストダッシュシステム用パラメータを追加する (Phase B)。
    - boost_speed_multiplier: ブースト時速度倍率 (デフォルト: 2.0)
    - boost_en_cost: ブースト中 EN 消費量 (/s) (デフォルト: 5.0)
    - boost_max_duration: 1 回のブーストの最大継続時間 (s) (デフォルト: 3.0)
    - boost_cooldown: ブースト終了後の再使用不可時間 (s) (デフォルト: 5.0)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "o9p0q1r2s3t4"
down_revision: str | None = "n8o9p0q1r2s3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add boost dash parameter columns to mobile_suits table."""
    op.add_column(
        "mobile_suits",
        sa.Column(
            "boost_speed_multiplier",
            sa.Float(),
            nullable=False,
            server_default="2.0",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "boost_en_cost",
            sa.Float(),
            nullable=False,
            server_default="5.0",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "boost_max_duration",
            sa.Float(),
            nullable=False,
            server_default="3.0",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "boost_cooldown",
            sa.Float(),
            nullable=False,
            server_default="5.0",
        ),
    )


def downgrade() -> None:
    """Remove boost dash parameter columns from mobile_suits table."""
    op.drop_column("mobile_suits", "boost_cooldown")
    op.drop_column("mobile_suits", "boost_max_duration")
    op.drop_column("mobile_suits", "boost_en_cost")
    op.drop_column("mobile_suits", "boost_speed_multiplier")

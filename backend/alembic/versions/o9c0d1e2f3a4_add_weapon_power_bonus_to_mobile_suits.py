"""add_weapon_power_bonus_to_mobile_suits.

Revision ID: o9c0d1e2f3a4
Revises: n8b9c0d1e2f3
Create Date: 2026-10-18

Note:
    機体強化（weapon_power）の加算値を mobile_suits に持つ。
    weapons を書き直す処理が、この値を足し直せるようにするため。
    既存の行は 0 で作る。加算値の推定と設定は
    scripts/maintenance/backfill_weapon_power_bonus.py で行う。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "o9c0d1e2f3a4"
down_revision: str | Sequence[str] | None = "n8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add weapon_power_bonus column to mobile_suits."""
    op.add_column(
        "mobile_suits",
        sa.Column(
            "weapon_power_bonus", sa.Integer(), nullable=False, server_default="0"
        ),
    )


def downgrade() -> None:
    """Drop weapon_power_bonus column from mobile_suits."""
    op.drop_column("mobile_suits", "weapon_power_bonus")

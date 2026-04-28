"""add_strategy_mode_to_mobile_suits.

Revision ID: m7n8o9p0q1r2
Revises: l6m7n8o9p0q1
Create Date: 2026-04-28

Note:
    MobileSuit モデルに strategy_mode フィールドを追加する。
    有効な値: AGGRESSIVE / DEFENSIVE / SNIPER / ASSAULT / RETREAT
    NULL（未設定）の場合は BattleSimulator が AGGRESSIVE にフォールバックする。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m7n8o9p0q1r2"
down_revision: str | None = "l6m7n8o9p0q1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add strategy_mode column to mobile_suits table."""
    op.add_column(
        "mobile_suits",
        sa.Column("strategy_mode", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Remove strategy_mode column from mobile_suits table."""
    op.drop_column("mobile_suits", "strategy_mode")

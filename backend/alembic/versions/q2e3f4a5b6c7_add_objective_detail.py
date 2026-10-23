"""add_objective_detail.

Revision ID: q2e3f4a5b6c7
Revises: p1d2e3f4a5b6
Create Date: 2026-10-23

Note:
    撤退支援の達成度の内訳（友軍の数・撃破された友軍の数・プレイヤー機の生存）を
    battle_results に持たせる。nullable にし、既存の行はそのまま読める。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "q2e3f4a5b6c7"
down_revision: str | Sequence[str] | None = "p1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add objective_detail to battle_results."""
    op.add_column(
        "battle_results", sa.Column("objective_detail", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    """Drop objective_detail from battle_results."""
    op.drop_column("battle_results", "objective_detail")

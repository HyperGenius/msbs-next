"""add_result_summaries_to_battle_results.

Revision ID: n8b9c0d1e2f3
Revises: m7a8b9c0d1e2
Create Date: 2026-10-17

Note:
    結果画面の武器ごとの命中率と索敵の集計を battle_results に保存する。
    結果画面がログを読まずに集計を表示できるようにするため。
    既存の行はバックフィルしない（フロントがログから集計する）。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n8b9c0d1e2f3"
down_revision: str | Sequence[str] | None = "m7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add weapon_accuracy_summary and detection_summary columns to battle_results."""
    op.add_column(
        "battle_results",
        sa.Column("weapon_accuracy_summary", sa.JSON(), nullable=True),
    )
    op.add_column(
        "battle_results",
        sa.Column("detection_summary", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Drop weapon_accuracy_summary and detection_summary columns from battle_results."""
    op.drop_column("battle_results", "detection_summary")
    op.drop_column("battle_results", "weapon_accuracy_summary")

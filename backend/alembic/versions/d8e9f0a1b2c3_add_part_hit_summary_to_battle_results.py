"""add_part_hit_summary_to_battle_results.

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-09-21

Note:
    部位判定とスロット部位ロールを紐付けたバトルログ集計 (Issue #504, #501 Phase 3) を
    battle_results に保存するためのカラムを追加する。既存の battle_digest_fields
    （Issue #415）と同じ「書き込み時に一度だけ計算し、既存レコードとの互換のため
    nullable にしてバックフィルしない」方針。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8e9f0a1b2c3"
down_revision: str | Sequence[str] | None = "c7d8e9f0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add part_hit_summary column to battle_results."""
    op.add_column(
        "battle_results",
        sa.Column("part_hit_summary", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Drop part_hit_summary column from battle_results."""
    op.drop_column("battle_results", "part_hit_summary")

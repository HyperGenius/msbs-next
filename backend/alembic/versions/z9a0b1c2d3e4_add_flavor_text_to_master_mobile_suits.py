"""add_flavor_text_to_master_mobile_suits.

Revision ID: z9a0b1c2d3e4
Revises: y8z9a0b1c2d3
Create Date: 2026-08-16

Note:
    MS購入画面の演出強化（Issue #483）用に、機体ごとの短いフレーバーテキストを
    保持するカラムを master_mobile_suits に追加する。既存行は NULL のまま許容し、
    表示側で未設定時は非表示にする（master_weapons.flavor_text と同じ方針）。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z9a0b1c2d3e4"
down_revision: str | None = "y8z9a0b1c2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add flavor_text column to master_mobile_suits table."""
    op.add_column(
        "master_mobile_suits",
        sa.Column(
            "flavor_text",
            sa.String(),
            nullable=True,
            comment="購入画面用フレーバーテキスト（1〜2行程度）",
        ),
    )


def downgrade() -> None:
    """Remove flavor_text column from master_mobile_suits table."""
    op.drop_column("master_mobile_suits", "flavor_text")

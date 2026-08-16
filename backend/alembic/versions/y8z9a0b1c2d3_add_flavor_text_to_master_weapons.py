"""add_flavor_text_to_master_weapons.

Revision ID: y8z9a0b1c2d3
Revises: x7y8z9a0b1c2
Create Date: 2026-08-15

Note:
    武器購入画面の演出強化（Issue #480）用に、武器ごとの短いフレーバーテキストを
    保持するカラムを master_weapons に追加する。既存行は NULL のまま許容し、
    表示側で未設定時は非表示にする。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "y8z9a0b1c2d3"
down_revision: str | None = "x7y8z9a0b1c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add flavor_text column to master_weapons table."""
    op.add_column(
        "master_weapons",
        sa.Column(
            "flavor_text",
            sa.String(),
            nullable=True,
            comment="購入画面用フレーバーテキスト（1〜2行程度）",
        ),
    )


def downgrade() -> None:
    """Remove flavor_text column from master_weapons table."""
    op.drop_column("master_weapons", "flavor_text")

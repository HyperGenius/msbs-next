"""add_pilot_status_fields.

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-03-08 05:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j4k5l6m7n8o9"
down_revision: str | None = "i3j4k5l6m7n8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """パイロットテーブルにステータスポイントフィールドを追加する."""
    op.add_column(
        "pilots",
        sa.Column("status_points", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pilots",
        sa.Column("dex", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pilots",
        sa.Column("intel", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pilots",
        sa.Column("ref", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pilots",
        sa.Column("tou", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pilots",
        sa.Column("luk", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pilots",
        sa.Column("awq", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """パイロットテーブルからステータスポイントフィールドを削除する."""
    op.drop_column("pilots", "awq")
    op.drop_column("pilots", "luk")
    op.drop_column("pilots", "tou")
    op.drop_column("pilots", "ref")
    op.drop_column("pilots", "intel")
    op.drop_column("pilots", "dex")
    op.drop_column("pilots", "status_points")

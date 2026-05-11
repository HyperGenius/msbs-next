"""add_master_mobile_suits_and_weapons_tables.

Revision ID: r1s2t3u4v5w6
Revises: q1r2s3t4u5v6
Create Date: 2026-05-11

Note:
    master_mobile_suits / master_weapons テーブルを追加する。
    機体・武器マスターデータをJSONファイルからPostgresへ移行するためのスキーマ。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "r1s2t3u4v5w6"
down_revision: str | None = "q1r2s3t4u5v6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create master_mobile_suits and master_weapons tables."""
    # master_mobile_suits テーブル
    op.create_table(
        "master_mobile_suits",
        sa.Column("id", sa.String(), nullable=False, comment="スネークケースID (例: rx_78_2)"),
        sa.Column("name", sa.String(), nullable=False, comment="機体名"),
        sa.Column("price", sa.Integer(), nullable=False, comment="購入価格"),
        sa.Column("faction", sa.String(), nullable=False, server_default="", comment="勢力"),
        sa.Column("description", sa.String(), nullable=False, comment="機体説明文"),
        sa.Column(
            "specs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="機体スペック (MasterMobileSuitSpec の全フィールド)",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # master_weapons テーブル
    op.create_table(
        "master_weapons",
        sa.Column("id", sa.String(), nullable=False, comment="スネークケースID (例: zaku_mg)"),
        sa.Column("name", sa.String(), nullable=False, comment="武器名"),
        sa.Column("price", sa.Integer(), nullable=False, comment="購入価格"),
        sa.Column("description", sa.String(), nullable=False, comment="武器説明文"),
        sa.Column(
            "weapon",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="武器スペック (Weapon モデルの全フィールド)",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop master_mobile_suits and master_weapons tables."""
    op.drop_table("master_weapons")
    op.drop_table("master_mobile_suits")

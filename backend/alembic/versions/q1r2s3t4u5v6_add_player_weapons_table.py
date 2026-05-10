"""add_player_weapons_table.

Revision ID: q1r2s3t4u5v6
Revises: p0q1r2s3t4u5
Create Date: 2026-05-10

Note:
    player_weapons テーブルを追加する。
    武器インスタンスを UUID で一意識別できるようにし、将来の武器カスタマイズの実装基盤を整える。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "q1r2s3t4u5v6"
down_revision: str | None = "p0q1r2s3t4u5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create player_weapons table."""
    op.create_table(
        "player_weapons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("master_weapon_id", sa.String(), nullable=False),
        sa.Column("base_snapshot", sa.JSON(), nullable=True),
        sa.Column("custom_stats", sa.JSON(), nullable=True),
        sa.Column("equipped_ms_id", sa.Uuid(), nullable=True),
        sa.Column("equipped_slot", sa.Integer(), nullable=True),
        sa.Column("acquired_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["equipped_ms_id"], ["mobile_suits.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("equipped_ms_id", "equipped_slot", name="uq_equipped_slot"),
    )
    op.create_index("ix_player_weapons_user_id", "player_weapons", ["user_id"])
    op.create_index(
        "ix_player_weapons_master_weapon_id", "player_weapons", ["master_weapon_id"]
    )


def downgrade() -> None:
    """Drop player_weapons table."""
    op.drop_index("ix_player_weapons_master_weapon_id", table_name="player_weapons")
    op.drop_index("ix_player_weapons_user_id", table_name="player_weapons")
    op.drop_table("player_weapons")

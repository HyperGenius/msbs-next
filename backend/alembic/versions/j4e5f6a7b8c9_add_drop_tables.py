"""add_drop_tables.

Revision ID: j4e5f6a7b8c9
Revises: i3d4e5f6a7b8
Create Date: 2026-09-26

Note:
    ドロップテーブル (drop_tables) とそのエントリー (drop_table_entries) を追加する。
    battle_results に戦利品の一覧 (loot) を追加する。
    既存のバトル結果の loot は NULL のままにする。導入前のバトルと区別するため。
    初期データは scripts/seed/seed_drop_tables.py で投入する。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "i3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create drop tables and add loot to battle_results."""
    op.create_table(
        "drop_tables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope_type", sa.String(), nullable=False),
        sa.Column("scope_key", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("drop_rate", sa.Float(), nullable=False),
        sa.Column("win_rate_multiplier", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope_type", "scope_key", name="uq_drop_table_scope"),
    )

    op.create_table(
        "drop_table_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("drop_table_id", sa.Integer(), nullable=False),
        sa.Column("blueprint_id", sa.String(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("requires_win", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["drop_table_id"], ["drop_tables.id"]),
        sa.ForeignKeyConstraint(["blueprint_id"], ["master_blueprints.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "drop_table_id", "blueprint_id", name="uq_drop_table_entry_blueprint"
        ),
    )
    op.create_index(
        "ix_drop_table_entries_drop_table_id",
        "drop_table_entries",
        ["drop_table_id"],
    )
    op.create_index(
        "ix_drop_table_entries_blueprint_id", "drop_table_entries", ["blueprint_id"]
    )

    op.add_column("battle_results", sa.Column("loot", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Drop drop tables and loot column."""
    op.drop_column("battle_results", "loot")
    op.drop_index("ix_drop_table_entries_blueprint_id", table_name="drop_table_entries")
    op.drop_index(
        "ix_drop_table_entries_drop_table_id", table_name="drop_table_entries"
    )
    op.drop_table("drop_table_entries")
    op.drop_table("drop_tables")

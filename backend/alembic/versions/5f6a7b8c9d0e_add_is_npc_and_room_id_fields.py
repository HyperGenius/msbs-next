"""add_is_npc_and_room_id_fields.

Revision ID: 5f6a7b8c9d0e
Revises: 4a1b2c3d4e5f
Create Date: 2026-02-05 12:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5f6a7b8c9d0e"
down_revision: str | Sequence[str] | None = "4a1b2c3d4e5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_npc column to battle_entries
    op.add_column(
        "battle_entries",
        sa.Column("is_npc", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(
        op.f("ix_battle_entries_is_npc"), "battle_entries", ["is_npc"], unique=False
    )

    # Alter user_id to be nullable for NPCs
    op.alter_column("battle_entries", "user_id", nullable=True)

    # Add room_id column to battle_results
    op.add_column("battle_results", sa.Column("room_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_battle_results_room_id", "battle_results", "battle_rooms", ["room_id"], ["id"]
    )
    op.create_index(
        op.f("ix_battle_results_room_id"), "battle_results", ["room_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove room_id column from battle_results
    op.drop_index(op.f("ix_battle_results_room_id"), table_name="battle_results")
    op.drop_constraint("fk_battle_results_room_id", "battle_results", type_="foreignkey")
    op.drop_column("battle_results", "room_id")

    # Alter user_id back to not nullable
    op.alter_column("battle_entries", "user_id", nullable=False)

    # Remove is_npc column from battle_entries
    op.drop_index(op.f("ix_battle_entries_is_npc"), table_name="battle_entries")
    op.drop_column("battle_entries", "is_npc")

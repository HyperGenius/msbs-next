"""add_mission_rooms.

Revision ID: p1d2e3f4a5b6
Revises: o9c0d1e2f3a4
Create Date: 2026-10-23

Note:
    作戦を定期バトルのエントリー制で遊べるようにする。
    missions に作戦目標・友軍・配置・有効フラグ、battle_rooms に作戦ID、
    battle_results に作戦の結果を持たせる。
    追加カラムは nullable（有効フラグは false）にし、既存の行はそのまま読める。
    null の作戦目標は殲滅、null の作戦IDはデイリーバトルロイヤルとして扱う。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "p1d2e3f4a5b6"
down_revision: str | Sequence[str] | None = "o9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add mission columns to missions, battle_rooms and battle_results."""
    op.add_column("missions", sa.Column("objective", sa.JSON(), nullable=True))
    op.add_column("missions", sa.Column("allies_config", sa.JSON(), nullable=True))
    op.add_column("missions", sa.Column("layout", sa.JSON(), nullable=True))
    op.add_column(
        "missions",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.add_column("battle_rooms", sa.Column("mission_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_battle_rooms_mission_id"), "battle_rooms", ["mission_id"], unique=False
    )
    op.create_foreign_key(
        "fk_battle_rooms_mission_id",
        "battle_rooms",
        "missions",
        ["mission_id"],
        ["id"],
    )

    op.add_column(
        "battle_results", sa.Column("objective_status", sa.String(), nullable=True)
    )
    op.add_column(
        "battle_results", sa.Column("objective_progress", sa.Integer(), nullable=True)
    )
    op.add_column(
        "battle_results", sa.Column("objective_required", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """Drop mission columns from missions, battle_rooms and battle_results."""
    op.drop_column("battle_results", "objective_required")
    op.drop_column("battle_results", "objective_progress")
    op.drop_column("battle_results", "objective_status")

    op.drop_constraint("fk_battle_rooms_mission_id", "battle_rooms", type_="foreignkey")
    op.drop_index(op.f("ix_battle_rooms_mission_id"), table_name="battle_rooms")
    op.drop_column("battle_rooms", "mission_id")

    op.drop_column("missions", "is_active")
    op.drop_column("missions", "layout")
    op.drop_column("missions", "allies_config")
    op.drop_column("missions", "objective")

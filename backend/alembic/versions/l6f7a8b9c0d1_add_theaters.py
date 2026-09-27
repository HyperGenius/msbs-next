"""add_theaters.

Revision ID: l6f7a8b9c0d1
Revises: k5f6a7b8c9d0
Create Date: 2026-09-27

Note:
    環境タイプ (master_environments) と戦域 (master_theaters) を追加する。
    battle_rooms と battle_results に戦域ID (theater_id) とミノフスキー濃度
    (minovsky_density) を追加する。既存のルームと結果は null のままにする。
    初期データは scripts/seed/seed_master_data.py で投入する。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "l6f7a8b9c0d1"
down_revision: str | Sequence[str] | None = "k5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create theater tables and add theater columns to rooms and results."""
    op.create_table(
        "master_environments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("sensor_range_multiplier", sa.Float(), nullable=False),
        sa.Column("ranged_accuracy_penalty", sa.Float(), nullable=False),
        sa.Column("ranged_penalty_ref_distance", sa.Float(), nullable=False),
        sa.Column("default_obstacle_density", sa.String(), nullable=False),
        sa.Column("default_terrain_grade", sa.String(), nullable=False),
        sa.Column("viewer_preset", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "sensor_range_multiplier > 0 AND sensor_range_multiplier <= 1",
            name="ck_master_environment_sensor_range",
        ),
        sa.CheckConstraint(
            "ranged_accuracy_penalty >= 0 AND ranged_accuracy_penalty <= 1",
            name="ck_master_environment_ranged_penalty",
        ),
        sa.CheckConstraint(
            "ranged_penalty_ref_distance > 0",
            name="ck_master_environment_ranged_ref_distance",
        ),
    )

    op.create_table(
        "master_theaters",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("environment_id", sa.String(), nullable=False),
        sa.Column("base_minovsky", sa.Float(), nullable=False),
        sa.Column("minovsky_variance", sa.Float(), nullable=False),
        sa.Column("obstacle_density", sa.String(), nullable=True),
        sa.Column("hint", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("rotation_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["environment_id"], ["master_environments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "base_minovsky >= 0 AND base_minovsky <= 1",
            name="ck_master_theater_base_minovsky",
        ),
        sa.CheckConstraint(
            "minovsky_variance >= 0 AND minovsky_variance <= 0.5",
            name="ck_master_theater_minovsky_variance",
        ),
    )
    op.create_index(
        "ix_master_theaters_environment_id", "master_theaters", ["environment_id"]
    )

    for table in ("battle_rooms", "battle_results"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column("theater_id", sa.String(), nullable=True))
            batch_op.add_column(
                sa.Column("minovsky_density", sa.Float(), nullable=True)
            )
            batch_op.create_foreign_key(
                f"fk_{table}_theater_id", "master_theaters", ["theater_id"], ["id"]
            )
            batch_op.create_index(f"ix_{table}_theater_id", ["theater_id"])


def downgrade() -> None:
    """Drop theater columns and tables."""
    for table in ("battle_results", "battle_rooms"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_index(f"ix_{table}_theater_id")
            batch_op.drop_constraint(f"fk_{table}_theater_id", type_="foreignkey")
            batch_op.drop_column("minovsky_density")
            batch_op.drop_column("theater_id")

    op.drop_index("ix_master_theaters_environment_id", table_name="master_theaters")
    op.drop_table("master_theaters")
    op.drop_table("master_environments")

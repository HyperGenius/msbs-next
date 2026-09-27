"""add_technologies.

Revision ID: k5f6a7b8c9d0
Revises: j4e5f6a7b8c9
Create Date: 2026-09-27

Note:
    技術マスター (master_technologies)、設計図の必要な技術Lv (blueprint_tech_requirements)、
    プレイヤーの累計断片数 (player_technologies) を追加する。
    drop_table_entries に報酬の種別 (reward_type) と技術ID (tech_id) を追加する。
    既存のエントリーは BLUEPRINT にする。
    導入時点では全プレイヤーの累計断片数を0とするため、player_technologies は空のままにする。
    初期データは scripts/seed/seed_master_data.py で投入する。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "j4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REWARD_CHECK = (
    "(reward_type = 'BLUEPRINT' AND blueprint_id IS NOT NULL AND tech_id IS NULL)"
    " OR (reward_type = 'TECH_FRAGMENT' AND tech_id IS NOT NULL"
    " AND blueprint_id IS NULL)"
)


def upgrade() -> None:
    """Create technology tables and allow tech fragments in drop tables."""
    op.create_table(
        "master_technologies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("level_thresholds", sa.JSON(), nullable=False),
        sa.Column("overflow_credit_value", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "blueprint_tech_requirements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("blueprint_id", sa.String(), nullable=False),
        sa.Column("tech_id", sa.String(), nullable=False),
        sa.Column("required_lv", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["blueprint_id"], ["master_blueprints.id"]),
        sa.ForeignKeyConstraint(["tech_id"], ["master_technologies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "blueprint_id", "tech_id", name="uq_blueprint_tech_requirement"
        ),
    )
    op.create_index(
        "ix_blueprint_tech_requirements_blueprint_id",
        "blueprint_tech_requirements",
        ["blueprint_id"],
    )
    op.create_index(
        "ix_blueprint_tech_requirements_tech_id",
        "blueprint_tech_requirements",
        ["tech_id"],
    )

    op.create_table(
        "player_technologies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("tech_id", sa.String(), nullable=False),
        sa.Column("fragment_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tech_id"], ["master_technologies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "tech_id", name="uq_player_technology"),
    )
    op.create_index(
        "ix_player_technologies_user_id", "player_technologies", ["user_id"]
    )
    op.create_index(
        "ix_player_technologies_tech_id", "player_technologies", ["tech_id"]
    )

    # 既存のエントリーを BLUEPRINT にするため、いったん server_default を付けて追加する。
    with op.batch_alter_table("drop_table_entries") as batch_op:
        batch_op.add_column(
            sa.Column(
                "reward_type",
                sa.String(),
                nullable=False,
                server_default="BLUEPRINT",
            )
        )
        batch_op.add_column(sa.Column("tech_id", sa.String(), nullable=True))
        batch_op.alter_column("blueprint_id", existing_type=sa.String(), nullable=True)
    with op.batch_alter_table("drop_table_entries") as batch_op:
        batch_op.alter_column(
            "reward_type", existing_type=sa.String(), server_default=None
        )
        batch_op.create_foreign_key(
            "fk_drop_table_entries_tech_id",
            "master_technologies",
            ["tech_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uq_drop_table_entry_tech", ["drop_table_id", "tech_id"]
        )
        batch_op.create_check_constraint("ck_drop_table_entry_reward", REWARD_CHECK)
        batch_op.create_index("ix_drop_table_entries_tech_id", ["tech_id"])


def downgrade() -> None:
    """Drop technology tables and tech fragment entries."""
    op.execute("DELETE FROM drop_table_entries WHERE reward_type = 'TECH_FRAGMENT'")
    with op.batch_alter_table("drop_table_entries") as batch_op:
        batch_op.drop_index("ix_drop_table_entries_tech_id")
        batch_op.drop_constraint("ck_drop_table_entry_reward", type_="check")
        batch_op.drop_constraint("uq_drop_table_entry_tech", type_="unique")
        batch_op.drop_constraint("fk_drop_table_entries_tech_id", type_="foreignkey")
        batch_op.alter_column("blueprint_id", existing_type=sa.String(), nullable=False)
        batch_op.drop_column("tech_id")
        batch_op.drop_column("reward_type")

    op.drop_index("ix_player_technologies_tech_id", table_name="player_technologies")
    op.drop_index("ix_player_technologies_user_id", table_name="player_technologies")
    op.drop_table("player_technologies")
    op.drop_index(
        "ix_blueprint_tech_requirements_tech_id",
        table_name="blueprint_tech_requirements",
    )
    op.drop_index(
        "ix_blueprint_tech_requirements_blueprint_id",
        table_name="blueprint_tech_requirements",
    )
    op.drop_table("blueprint_tech_requirements")
    op.drop_table("master_technologies")

"""Add friendship, team and team_member tables.

Revision ID: f1a2b3c4d5e6
Revises: c3d4e5f6g7h8
Create Date: 2026-02-23 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "c3d4e5f6g7h8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade: フレンドシップ・チーム・チームメンバーテーブルを作成."""
    # friendships テーブル
    op.create_table(
        "friendships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("friend_user_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_friendships_user_id"), "friendships", ["user_id"])
    op.create_index(
        op.f("ix_friendships_friend_user_id"), "friendships", ["friend_user_id"]
    )
    op.create_index(op.f("ix_friendships_status"), "friendships", ["status"])

    # teams テーブル
    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="FORMING"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_teams_owner_user_id"), "teams", ["owner_user_id"])
    op.create_index(op.f("ix_teams_status"), "teams", ["status"])

    # team_members テーブル
    op.create_table(
        "team_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("is_ready", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
    )
    op.create_index(op.f("ix_team_members_team_id"), "team_members", ["team_id"])
    op.create_index(op.f("ix_team_members_user_id"), "team_members", ["user_id"])


def downgrade() -> None:
    """Downgrade: フレンドシップ・チーム・チームメンバーテーブルを削除."""
    op.drop_table("team_members")
    op.drop_table("teams")
    op.drop_table("friendships")

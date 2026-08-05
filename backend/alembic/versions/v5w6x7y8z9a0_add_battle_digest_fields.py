"""add_battle_digest_fields.

Revision ID: v5w6x7y8z9a0
Revises: u4v5w6x7y8z9
Create Date: 2026-08-05 00:00:00.000000

Note:
    Battle History 一覧のダイジェスト化 (Issue #415)。
    battle_results にバトル終了時に一度だけ計算する集計値・ダイジェスト
    タグ・一言ログを追加する。既存レコードとの互換のため全カラム nullable
    とし、バックフィルは行わない。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "v5w6x7y8z9a0"
down_revision: str | Sequence[str] | None = "u4v5w6x7y8z9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add battle digest columns to battle_results."""
    op.add_column(
        "battle_results", sa.Column("player_survived", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "battle_results", sa.Column("min_hp_percent", sa.Integer(), nullable=True)
    )
    op.add_column(
        "battle_results", sa.Column("damage_severity", sa.String(), nullable=True)
    )
    op.add_column(
        "battle_results", sa.Column("damage_taken_count", sa.Integer(), nullable=True)
    )
    op.add_column(
        "battle_results", sa.Column("max_hit_damage", sa.Integer(), nullable=True)
    )
    op.add_column(
        "battle_results", sa.Column("dodge_count", sa.Integer(), nullable=True)
    )
    op.add_column(
        "battle_results",
        sa.Column("attacks_received_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "battle_results", sa.Column("pilot_ms_name", sa.String(), nullable=True)
    )
    op.add_column("battle_results", sa.Column("digest_tag", sa.String(), nullable=True))
    op.add_column(
        "battle_results", sa.Column("digest_text", sa.String(), nullable=True)
    )


def downgrade() -> None:
    """Drop battle digest columns from battle_results."""
    op.drop_column("battle_results", "digest_text")
    op.drop_column("battle_results", "digest_tag")
    op.drop_column("battle_results", "pilot_ms_name")
    op.drop_column("battle_results", "attacks_received_count")
    op.drop_column("battle_results", "dodge_count")
    op.drop_column("battle_results", "max_hit_damage")
    op.drop_column("battle_results", "damage_taken_count")
    op.drop_column("battle_results", "damage_severity")
    op.drop_column("battle_results", "min_hp_percent")
    op.drop_column("battle_results", "player_survived")

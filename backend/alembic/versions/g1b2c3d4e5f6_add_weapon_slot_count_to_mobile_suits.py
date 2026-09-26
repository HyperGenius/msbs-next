"""add_weapon_slot_count_to_mobile_suits.

Revision ID: g1b2c3d4e5f6
Revises: f0a1b2c3d4e5
Create Date: 2026-09-26

Note:
    武器スロット数を機体ごとに保持するカラムを追加する (Issue #543)。
    NPC 機は機体名が "{機体マスター名} (NPC)" のため機体マスターから
    スロット数を引けず、装備数と MAX_WEAPON_SLOTS (2) の大きい方が実効値になっていた。

    既存の NPC 機（side = 'ENEMY'）にはその実効値をバックフィルする。
    プレイヤー機は NULL のまま残し、従来どおり機体マスターから解決する。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "f0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# app.engine.constants.MAX_WEAPON_SLOTS の適用時点の値
MAX_WEAPON_SLOTS = 2


def upgrade() -> None:
    """Add mobile_suits.weapon_slot_count and backfill NPC mobile suits."""
    op.add_column(
        "mobile_suits",
        sa.Column("weapon_slot_count", sa.Integer(), nullable=True),
    )
    op.execute(
        f"""
        UPDATE mobile_suits
        SET weapon_slot_count = GREATEST(
            CASE
                WHEN json_typeof(weapons::json) = 'array'
                THEN json_array_length(weapons::json)
                ELSE 0
            END,
            {MAX_WEAPON_SLOTS}
        )
        WHERE side = 'ENEMY'
        """
    )


def downgrade() -> None:
    """Drop mobile_suits.weapon_slot_count."""
    op.drop_column("mobile_suits", "weapon_slot_count")

"""add_model_number_name_ja_slots_beam_lv.

Revision ID: u4v5w6x7y8z9
Revises: t3u4v5w6x7y8
Create Date: 2026-07-19

Note:
    MasterMobileSuit に以下のカラムを追加する (issue #383)。
    - model_number: 型番 (例: RGM-79)
    - name_ja: 日本語表示名
    - weapon_slot_count: 武器スロット数 (1以上)。既存機体は specs.weapons の件数で初期化
    - beam_generator_lv: ビームジェネレータLv (0以上、デフォルト0)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "u4v5w6x7y8z9"
down_revision: str | None = "t3u4v5w6x7y8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add model_number/name_ja/weapon_slot_count/beam_generator_lv columns."""
    op.add_column(
        "master_mobile_suits",
        sa.Column("name_ja", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "master_mobile_suits",
        sa.Column("model_number", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "master_mobile_suits",
        sa.Column(
            "weapon_slot_count", sa.Integer(), nullable=False, server_default="1"
        ),
    )
    op.add_column(
        "master_mobile_suits",
        sa.Column(
            "beam_generator_lv", sa.Integer(), nullable=False, server_default="0"
        ),
    )

    # 既存機体の weapon_slot_count を specs.weapons の件数で初期化する
    bind = op.get_bind()
    master_mobile_suits = sa.table(
        "master_mobile_suits",
        sa.column("id", sa.String),
        sa.column("specs", sa.JSON),
        sa.column("weapon_slot_count", sa.Integer),
    )
    rows = bind.execute(
        sa.select(master_mobile_suits.c.id, master_mobile_suits.c.specs)
    ).fetchall()
    for row in rows:
        specs = row.specs or {}
        weapons = specs.get("weapons", []) if isinstance(specs, dict) else []
        slot_count = max(1, len(weapons))
        bind.execute(
            master_mobile_suits.update()
            .where(master_mobile_suits.c.id == row.id)
            .values(weapon_slot_count=slot_count)
        )


def downgrade() -> None:
    """Remove model_number/name_ja/weapon_slot_count/beam_generator_lv columns."""
    op.drop_column("master_mobile_suits", "beam_generator_lv")
    op.drop_column("master_mobile_suits", "weapon_slot_count")
    op.drop_column("master_mobile_suits", "model_number")
    op.drop_column("master_mobile_suits", "name_ja")

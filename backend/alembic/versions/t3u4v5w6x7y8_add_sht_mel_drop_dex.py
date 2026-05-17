"""add_sht_mel_drop_dex.

Revision ID: t3u4v5w6x7y8
Revises: s2t3u4v5w6x7
Create Date: 2026-05-17 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "t3u4v5w6x7y8"
down_revision: str | None = "a55223748ffb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Pilots テーブルに sht/mel を追加し、dex 値をコピーしてから dex を削除する."""
    op.add_column(
        "pilots",
        sa.Column("sht", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pilots",
        sa.Column("mel", sa.Integer(), nullable=False, server_default="0"),
    )
    # 既存ユーザーの dex 値を sht / mel 両方にコピー
    op.execute("UPDATE pilots SET sht = dex, mel = dex")
    op.drop_column("pilots", "dex")


def downgrade() -> None:
    """sht/mel を削除し dex を復元する（sht の値を dex に使用）."""
    op.add_column(
        "pilots",
        sa.Column("dex", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute("UPDATE pilots SET dex = sht")
    op.drop_column("pilots", "mel")
    op.drop_column("pilots", "sht")

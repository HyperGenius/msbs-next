"""merge_obstacles_and_battle_logs_heads.

Revision ID: a55223748ffb
Revises: c5d6e7f8g9h0, s2t3u4v5w6x7
Create Date: 2026-05-16 10:46:11.452608

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "a55223748ffb"
down_revision: str | Sequence[str] | None = ("c5d6e7f8g9h0", "s2t3u4v5w6x7")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

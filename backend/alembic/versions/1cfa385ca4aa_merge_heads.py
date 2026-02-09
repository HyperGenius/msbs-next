"""merge_heads.

Revision ID: 1cfa385ca4aa
Revises: 46ebed749d6b, a1b2c3d4e5f6
Create Date: 2026-02-09 13:12:51.348046

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "1cfa385ca4aa"
down_revision: str | Sequence[str] | None = ("46ebed749d6b", "a1b2c3d4e5f6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

"""drop_theater_foreign_keys.

Revision ID: m7a8b9c0d1e2
Revises: l6f7a8b9c0d1
Create Date: 2026-09-28

Note:
    battle_rooms と battle_results の theater_id から master_theaters への FK を外す。
    管理画面で戦域を削除しても、過去のルームとバトル結果の theater_id を残すため。
    インデックスは残す。
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m7a8b9c0d1e2"
down_revision: str | Sequence[str] | None = "l6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("battle_rooms", "battle_results")


def upgrade() -> None:
    """Drop foreign keys from theater_id columns."""
    for table in TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(f"fk_{table}_theater_id", type_="foreignkey")


def downgrade() -> None:
    """Recreate foreign keys on theater_id columns.

    削除済みの戦域を参照する行があると失敗する。
    """
    for table in TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.create_foreign_key(
                f"fk_{table}_theater_id", "master_theaters", ["theater_id"], ["id"]
            )

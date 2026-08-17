"""add_gcs_path_to_battle_logs.

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-08-17

Note:
    `battle_logs.gcs_path`（`BattleLogRecord.gcs_path`）を追加する（Issue #493）。
    リプレイログ本体をNeonからCloud Storageへオフロードし、閲覧のたびにNeonの
    課金対象Network Transferが生ログサイズ分そのまま発生する問題を構造的に解消する。

    このマイグレーションはカラム追加のみを行う。既存行のGCSへのバックフィル・
    `logs`列のNULL化は別途 `backend/scripts/maintenance/offload_battle_logs_to_gcs.py`
    で行う（ALTER TABLEと違いバックフィルは1行ずつのUPDATEで進められるため、
    #489のような単一トランザクションでのOOMリスクがなく、マイグレーションに
    含める必要がない）。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6c7d8e9f0a1"
down_revision: str | None = "a5b6c7d8e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable gcs_path column to battle_logs."""
    op.add_column(
        "battle_logs",
        sa.Column("gcs_path", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Drop gcs_path column from battle_logs."""
    op.drop_column("battle_logs", "gcs_path")

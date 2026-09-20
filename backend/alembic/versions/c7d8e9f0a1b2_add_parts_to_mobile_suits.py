"""add_parts_to_mobile_suits.

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-09-20

Note:
    命中後の部位判定レイヤー (Issue #503, #501 Phase 2) 用に、機体の部位別HP/装甲
    状態 (`parts`) と欠損部位定義 (`missing_parts`) を保持するカラムを
    mobile_suits に追加する。既存の max_hp/current_hp/armor は全体値として
    引き続き使用し、parts はそれとは別に並行管理される。

    既存行は parts='{}' のまま許容し、アプリケーション側
    (MobileSuit.normalize_parts()。SQLModelのtable=Trueクラスは
    @model_validator(mode="after") が __init__/model_validate() のいずれでも
    正しく動作しないため、明示的に呼び出すメソッドとして実装している。
    BattleSimulator.__init__() やmatching_service._coerce_suit_json_fields()
    等から呼び出される) で max_hp/armor/missing_parts から都度自動生成するため、
    ここでのバックフィルは行わない（既存レコードとの互換性維持は
    sigmoid-damage-calculation.md 等、他のJSON列追加マイグレーションと同じ方針）。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d8e9f0a1b2"
down_revision: str | Sequence[str] | None = "b6c7d8e9f0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add missing_parts and parts columns to mobile_suits table."""
    op.add_column(
        "mobile_suits",
        sa.Column(
            "missing_parts",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "mobile_suits",
        sa.Column(
            "parts",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    """Remove missing_parts and parts columns from mobile_suits table."""
    op.drop_column("mobile_suits", "parts")
    op.drop_column("mobile_suits", "missing_parts")

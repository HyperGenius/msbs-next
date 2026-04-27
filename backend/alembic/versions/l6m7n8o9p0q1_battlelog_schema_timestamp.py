"""BattleLog スキーマ刷新: turn → timestamp、新フィールド追加

Revision ID: l6m7n8o9p0q1
Revises: k5l6m7n8o9p0
Create Date: 2026-04-27

Note:
    BattleLog は battle_results テーブルの JSON カラム (logs) に格納されており、
    独立したテーブルを持たない。そのため DB テーブル定義への変更はないが、
    JSON スキーマの後方互換性を持たない変更として本マイグレーションを作成する。

    変更内容:
    - BattleLog.turn (int) を廃止し BattleLog.timestamp (float) に置換
    - BattleLog.velocity_snapshot (Vector3 | None) を追加
    - BattleLog.fuzzy_scores (dict | None) を追加
    - BattleLog.strategy_mode (str | None) を追加

    既存の battle_results.logs データは旧スキーマ形式のため、
    本マイグレーション適用後は旧ログを新スキーマで再解釈することはできない。
    後方互換変換レイヤーは実装しない（仕様通り）。
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "l6m7n8o9p0q1"
down_revision = "k5l6m7n8o9p0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # BattleLog は JSON カラムに格納されており DB スキーマ変更は不要。
    # 本マイグレーションはスキーマ変更の記録のみ。
    pass


def downgrade() -> None:
    # ダウングレードは旧 turn フィールドへの変換を必要とするが、
    # 後方互換性は持たないため何もしない。
    pass

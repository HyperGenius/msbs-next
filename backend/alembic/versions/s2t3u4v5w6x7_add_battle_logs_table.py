"""battle_logsテーブル追加・battle_results.logs削除・battle_log_id追加.

Revision ID: s2t3u4v5w6x7
Revises: r1s2t3u4v5w6
Create Date: 2026-05-13

変更内容:
- battle_logs テーブルを新設（バトルセッション単位でログを1件保存）
- battle_results.logs カラムを削除
- battle_results.battle_log_id カラムを追加（FK → battle_logs.id）
- データ移行: 既存 battle_results.logs を battle_logs へ移動し battle_log_id を更新
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "s2t3u4v5w6x7"
down_revision: str | None = "r1s2t3u4v5w6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. battle_logs テーブルを作成
    op.create_table(
        "battle_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.Uuid(), nullable=True),
        sa.Column("mission_id", sa.Integer(), nullable=True),
        sa.Column("logs", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"]),
        sa.ForeignKeyConstraint(["room_id"], ["battle_rooms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_battle_logs_room_id"), "battle_logs", ["room_id"], unique=False
    )
    op.create_index(
        op.f("ix_battle_logs_mission_id"), "battle_logs", ["mission_id"], unique=False
    )

    # 2. battle_results に battle_log_id カラムを追加（NULLABLEで追加）
    op.add_column(
        "battle_results",
        sa.Column("battle_log_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_battle_results_battle_log_id"),
        "battle_results",
        ["battle_log_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_battle_results_battle_log_id",
        "battle_results",
        "battle_logs",
        ["battle_log_id"],
        ["id"],
    )

    # 3. 既存データ移行: battle_results.logs → battle_logs
    #    各 battle_result の logs を battle_logs へ移動し、battle_log_id を更新
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        # SQLite: JSON 関数サポートが限定的のため Python で処理
        import json
        import uuid

        results = bind.execute(
            sa.text(
                "SELECT id, room_id, mission_id, logs, created_at FROM battle_results WHERE logs IS NOT NULL"
            )
        ).fetchall()

        for row in results:
            row_id, room_id, mission_id, logs_raw, created_at = row
            if not logs_raw:
                continue
            # logs_raw は文字列の場合があるのでパース
            if isinstance(logs_raw, str):
                try:
                    logs_data = json.loads(logs_raw)
                except Exception:
                    logs_data = []
            else:
                logs_data = logs_raw

            if not logs_data:
                continue

            new_id = str(uuid.uuid4())
            bind.execute(
                sa.text(
                    "INSERT INTO battle_logs (id, room_id, mission_id, logs, created_at) "
                    "VALUES (:id, :room_id, :mission_id, :logs, :created_at)"
                ),
                {
                    "id": new_id,
                    "room_id": str(room_id) if room_id else None,
                    "mission_id": mission_id,
                    "logs": json.dumps(logs_data)
                    if isinstance(logs_data, list)
                    else logs_data,
                    "created_at": created_at,
                },
            )
            bind.execute(
                sa.text(
                    "UPDATE battle_results SET battle_log_id = :log_id WHERE id = :id"
                ),
                {"log_id": new_id, "id": str(row_id)},
            )
    else:
        # PostgreSQL: gen_random_uuid() と CTE を使って一括移行
        bind.execute(
            sa.text("""
            WITH inserted AS (
                INSERT INTO battle_logs (id, room_id, mission_id, logs, created_at)
                SELECT
                    gen_random_uuid(),
                    room_id,
                    mission_id,
                    COALESCE(logs, '[]'::json),
                    created_at
                FROM battle_results
                WHERE logs IS NOT NULL AND logs::text <> 'null' AND logs::text <> '[]'
                RETURNING id, room_id, mission_id, created_at
            )
            UPDATE battle_results br
            SET battle_log_id = ins.id
            FROM (
                SELECT
                    bl.id,
                    br2.id AS result_id
                FROM battle_logs bl
                JOIN battle_results br2
                    ON (bl.room_id = br2.room_id OR (bl.room_id IS NULL AND br2.room_id IS NULL))
                    AND (bl.mission_id = br2.mission_id OR (bl.mission_id IS NULL AND br2.mission_id IS NULL))
                    AND bl.created_at = br2.created_at
                WHERE br2.battle_log_id IS NULL
            ) ins
            WHERE br.id = ins.result_id
        """)
        )

    # 4. battle_results.logs カラムを削除
    op.drop_column("battle_results", "logs")


def downgrade() -> None:
    """Downgrade schema."""
    # 1. battle_results に logs カラムを再追加
    op.add_column(
        "battle_results",
        sa.Column("logs", sa.JSON(), nullable=True),
    )

    # 2. battle_logs からデータを battle_results.logs へ戻す
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        import json

        log_records = bind.execute(
            sa.text("SELECT id, logs FROM battle_logs")
        ).fetchall()
        for row in log_records:
            log_id, logs_data = row
            if isinstance(logs_data, str):
                try:
                    logs_data = json.loads(logs_data)
                except Exception:
                    logs_data = []
            bind.execute(
                sa.text(
                    "UPDATE battle_results SET logs = :logs WHERE battle_log_id = :log_id"
                ),
                {
                    "logs": json.dumps(logs_data)
                    if isinstance(logs_data, list)
                    else logs_data,
                    "log_id": str(log_id),
                },
            )
    else:
        bind.execute(
            sa.text("""
            UPDATE battle_results br
            SET logs = bl.logs
            FROM battle_logs bl
            WHERE br.battle_log_id = bl.id
        """)
        )

    # 3. battle_results から battle_log_id カラムを削除
    op.drop_constraint(
        "fk_battle_results_battle_log_id", "battle_results", type_="foreignkey"
    )
    op.drop_index(op.f("ix_battle_results_battle_log_id"), table_name="battle_results")
    op.drop_column("battle_results", "battle_log_id")

    # 4. battle_logs テーブルを削除
    op.drop_index(op.f("ix_battle_logs_mission_id"), table_name="battle_logs")
    op.drop_index(op.f("ix_battle_logs_room_id"), table_name="battle_logs")
    op.drop_table("battle_logs")

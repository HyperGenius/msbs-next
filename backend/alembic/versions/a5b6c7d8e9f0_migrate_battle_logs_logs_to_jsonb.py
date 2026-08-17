"""migrate_battle_logs_logs_to_jsonb.

Revision ID: a5b6c7d8e9f0
Revises: z9a0b1c2d3e4
Create Date: 2026-08-17

Note:
    battle_logs.logs（BattleLogRecord.logs）を JSON から JSONB に移行する（Issue #489）。
    JSONB のバイナリ圧縮によるストレージ削減と、将来的なログ内容検索用のGINインデックス
    整備が目的。JSONB はキー順序を保証しないが、バトルログはキー順序に依存していないため
    問題ない。SQLite はJSONB型を持たないため、このマイグレーションはPostgreSQLでのみ
    実行する（sqlite上では型変更なしでスキップし、既存のテストDB構成には影響しない）。

    Neon実DBで検証したところ、最大行（テキスト換算で約86MB、pg_column_size約12.67MB）を
    含んだ状態で `ALTER COLUMN ... TYPE JSONB` を実行すると `OutOfMemory` になった
    （`maintenance_work_mem` をデフォルト64MB→512MBへ引き上げても解消せず、Neonの
    コンピュートサイズ自体が小さいことが原因と判断）。ALTER TABLE ... TYPE は
    テーブル全体を書き換える単一トランザクション・ACCESS EXCLUSIVEロックの操作であり、
    バッチ分割ができないため、巨大な行を1回のキャストで丸ごと処理できるだけのメモリを
    要求する。そのため、ALTERの前に閾値超の巨大行を退避・削除してからキャストする
    2段階構成にした:

    1. `_archive_and_delete_oversized_battle_logs()`: pg_column_size が
       `ARCHIVE_SIZE_THRESHOLD_BYTES`（2MB）を超える行を、生JSONテキストのまま
       ローカルファイル（`backend/scripts/verify/output/battle_logs_jsonb_migration_backup/`,
       .gitignore対象）へバックアップしてから削除する。`battle_results.battle_log_id`
       がこれらの行を参照している場合はNULLに更新してから削除する（FK制約
       `fk_battle_results_battle_log_id` はON DELETEアクションが無いため、参照が
       残ったままだと削除できない）。`BattleResult` 側の集計値（撃破数等）は既に
       非正規化カラムとして保存済みのため、リプレイ用の生ログを失っても一覧表示への
       影響はない。閾値2MBは実データの上位4件（12.67MB/9.41MB/8.09MB/1.94MB）のみを
       対象にし、5件目（1.59MB）以降は残す値として選定した。
    2. 残った行に対して `ALTER COLUMN logs TYPE JSONB USING logs::JSONB` を実行する。

    GINインデックス（`CREATE INDEX ... USING GIN (logs)`）はIssue本文で「任意」とされていたが、
    Neon実DBで作成してみたところインデックスサイズが約20MBとテーブル本体とほぼ同じになった
    （ログ内の全キー・全階層をインデックス化するため）。現時点で具体的な検索ユースケードが
    未定な一方でストレージ削減が目的の一つであるため、本Issueでは作成しない方針とした
    （将来actor/action_type等の検索要件が具体化した時点で別途追加を検討する）。

    ダウングレードでは列型をJSONへ戻すのみで、ステップ1で削除した行の復元は行わない
    （バックアップファイルから手動で復元する運用とする）。
"""

import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a5b6c7d8e9f0"
down_revision: str | None = "z9a0b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# pg_column_size(logs) がこれを超える行は、ALTER COLUMN TYPE 実行前に退避・削除する
# （Neonの小さいコンピュートで単一行キャストのOOMを避けるため）。
ARCHIVE_SIZE_THRESHOLD_BYTES = 2_000_000

_BACKUP_DIR = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "verify"
    / "output"
    / "battle_logs_jsonb_migration_backup"
)


def _archive_and_delete_oversized_battle_logs(bind: sa.Connection) -> None:
    """巨大なbattle_logs行をバックアップファイルへ退避してから削除する."""
    rows = bind.execute(
        sa.text(
            "SELECT id, room_id, mission_id, created_at, logs::text AS logs_text, "
            "pg_column_size(logs) AS logs_size "
            "FROM battle_logs WHERE pg_column_size(logs) > :threshold "
            "ORDER BY pg_column_size(logs) DESC"
        ),
        {"threshold": ARCHIVE_SIZE_THRESHOLD_BYTES},
    ).fetchall()

    if not rows:
        return

    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for log_id, room_id, mission_id, created_at, logs_text, logs_size in rows:
        backup_path = _BACKUP_DIR / f"{log_id}.json"
        backup_path.write_text(logs_text, encoding="utf-8")
        manifest.append(
            {
                "id": str(log_id),
                "room_id": str(room_id) if room_id else None,
                "mission_id": mission_id,
                "created_at": created_at.isoformat(),
                "logs_size_bytes": logs_size,
                "backup_file": backup_path.name,
            }
        )
        bind.execute(
            sa.text(
                "UPDATE battle_results SET battle_log_id = NULL WHERE battle_log_id = :id"
            ),
            {"id": log_id},
        )
        bind.execute(sa.text("DELETE FROM battle_logs WHERE id = :id"), {"id": log_id})

    manifest_path = _BACKUP_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def upgrade() -> None:
    """Migrate battle_logs.logs column from JSON to JSONB (PostgreSQL only)."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    _archive_and_delete_oversized_battle_logs(bind)

    # 巨大行を退避済みでも念のため maintenance_work_mem を引き上げておく。
    op.execute("SET LOCAL maintenance_work_mem = '512MB'")
    op.execute("ALTER TABLE battle_logs ALTER COLUMN logs TYPE JSONB USING logs::JSONB")


def downgrade() -> None:
    """Revert battle_logs.logs column from JSONB back to JSON (PostgreSQL only).

    Note: 退避・削除した巨大行の復元は行わない（バックアップファイルから手動で復元すること）。
    """
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TABLE battle_logs ALTER COLUMN logs TYPE JSON USING logs::JSON")

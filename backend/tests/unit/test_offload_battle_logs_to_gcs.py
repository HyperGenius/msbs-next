"""offload_battle_logs_to_gcs._run_backfill() のユニットテスト（Issue #500）."""

import uuid
from unittest.mock import patch

from sqlmodel import Session

from app.models.models import BattleLogRecord
from scripts.maintenance.offload_battle_logs_to_gcs import _run_backfill


def test_run_backfill_does_not_loop_forever_when_all_uploads_fail(
    session: Session, capsys
) -> None:  # noqa: ANN001
    """全件アップロード失敗時、同一行を無限に再取得せず終了することを確認する.

    修正前は`gcs_path`が更新されないままの行を`WHERE gcs_path IS NULL`が
    毎回返し続け、`--limit`未指定（`limit=None`）だと終了条件を満たさず
    無限ループしていた（実際にローカル環境で発生。原因は`BATTLE_LOG_GCS_BUCKET`
    未設定だったが、根本原因を問わず全件失敗時に無限ループする設計自体が問題）。
    """
    record = BattleLogRecord(logs=[{"a": 1}])
    session.add(record)
    session.commit()

    with patch(
        "scripts.maintenance.offload_battle_logs_to_gcs.offload_battle_log_to_gcs",
        return_value=False,
    ) as mock_offload:
        _run_backfill(dry_run=False, limit=None, skip_confirm=True)

    # 1件しか対象がないので、失敗IDを除外できていれば1回だけ呼ばれて終了する。
    # 除外できていない（＝バグ再発）場合はここに到達する前にテストがタイムアウトする。
    assert mock_offload.call_count == 1

    out = capsys.readouterr().out
    assert "成功 0 件 / 失敗 1 件" in out


def test_run_backfill_excludes_failed_ids_across_pages(session: Session) -> None:  # noqa: ANN001
    """失敗したIDが同一実行内の以降のページ取得で再取得されないことを確認する.

    `offload_battle_log_to_gcs()`本体（gcs_path更新を含む）は実行させたいので、
    その内部で呼ばれる`upload_battle_log()`だけをモックする。ここを
    `offload_battle_log_to_gcs()`ごとモックすると、成功時の実際のgcs_path書き込みが
    スキップされ、成功したはずの行が`WHERE gcs_path IS NULL`に永久に該当し続けて
    無限ループする（このテストを書く過程で実際に踏んだ）。
    """
    failing = BattleLogRecord(logs=[{"a": 1}])
    succeeding = BattleLogRecord(logs=[{"b": 2}])
    session.add(failing)
    session.add(succeeding)
    session.commit()
    session.refresh(failing)
    session.refresh(succeeding)
    failing_id = failing.id

    def fake_upload(log_id: uuid.UUID, logs: list[dict]) -> str:
        if log_id == failing_id:
            raise RuntimeError("boom")
        return f"battle-logs/{log_id}.ndjson"

    with patch(
        "app.services.battle_log_storage_service.upload_battle_log",
        side_effect=fake_upload,
    ):
        _run_backfill(dry_run=False, limit=None, skip_confirm=True)

    session.refresh(failing)
    session.refresh(succeeding)
    assert failing.gcs_path is None
    assert succeeding.gcs_path is not None

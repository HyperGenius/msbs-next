"""battle_log_storage_service のユニットテスト（Issue #493）.

実際のGCSへは接続せず、`google.cloud.storage.Client` をモックして
アップロード・読み出し・オフロードのロジックのみを検証する。
"""

import os
import uuid
from unittest.mock import MagicMock, patch

os.environ.setdefault("BATTLE_LOG_GCS_BUCKET", "test-battle-logs-bucket")

from app.services import battle_log_storage_service as svc  # noqa: E402


def test_object_path_for_uses_battle_log_id() -> None:
    """バケット内相対パスが`battle-logs/{id}.ndjson`になることを確認する."""
    log_id = uuid.uuid4()
    assert svc.object_path_for(log_id) == f"battle-logs/{log_id}.ndjson"


def test_logs_to_ndjson_text_empty() -> None:
    """空リストは空文字列に変換されることを確認する."""
    assert svc.logs_to_ndjson_text([]) == ""


def test_logs_to_ndjson_text_one_entry_per_line() -> None:
    """1エントリ1行のNDJSONテキストに変換されることを確認する."""
    logs = [{"a": 1}, {"b": 2}]
    text = svc.logs_to_ndjson_text(logs)
    lines = text.splitlines()
    assert len(lines) == 2
    assert text.endswith("\n")


def test_upload_battle_log_uploads_ndjson_without_content_encoding() -> None:
    """アップロード時にContent-Encodingを設定していないことを確認する.

    GCS側は非圧縮のプレーンテキストで保存し、圧縮はCloud Run側のGZipMiddlewareに
    任せる設計（Issue #493）。ここでContent-Encoding: gzipを付けてしまうと、
    アップロード時にテキストを実際にgzip圧縮していないため「メタデータ上は圧縮済みを
    謳っているのに中身は生テキスト」という不整合になる。
    """
    log_id = uuid.uuid4()
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    with patch.object(svc, "_client", return_value=mock_client):
        path = svc.upload_battle_log(log_id, [{"msg": "hello"}])

    assert path == f"battle-logs/{log_id}.ndjson"
    mock_blob.upload_from_string.assert_called_once()
    _, kwargs = mock_blob.upload_from_string.call_args
    assert kwargs.get("content_type") == "application/x-ndjson"
    assert "content_encoding" not in kwargs


def test_offload_battle_log_to_gcs_returns_false_on_upload_failure() -> None:
    """GCSアップロード失敗時は例外を投げずFalseを返すことを確認する（write-behind方式）."""
    log_id = uuid.uuid4()
    with patch.object(svc, "upload_battle_log", side_effect=RuntimeError("boom")):
        result = svc.offload_battle_log_to_gcs(log_id, [{"a": 1}])
    assert result is False


def test_offload_battle_log_to_gcs_updates_record_on_success(session) -> None:  # noqa: ANN001
    """成功時にgcs_pathが設定されlogsが空になることを確認する."""
    from app.models.models import BattleLogRecord

    record = BattleLogRecord(logs=[{"a": 1}])
    session.add(record)
    session.commit()
    session.refresh(record)

    with patch.object(svc, "upload_battle_log", return_value="battle-logs/x.ndjson"):
        result = svc.offload_battle_log_to_gcs(record.id, record.logs)

    assert result is True
    session.refresh(record)
    assert record.gcs_path == "battle-logs/x.ndjson"
    assert record.logs == []


def test_offload_battle_log_to_gcs_returns_false_when_record_missing() -> None:
    """対象のBattleLogRecordが存在しない場合はFalseを返すことを確認する."""
    missing_id = uuid.uuid4()
    with patch.object(svc, "upload_battle_log", return_value="battle-logs/x.ndjson"):
        result = svc.offload_battle_log_to_gcs(missing_id, [{"a": 1}])
    assert result is False


def test_stream_battle_log_chunks_yields_all_chunks() -> None:
    """非同期ジェネレータが同期イテレータの全チャンクをそのまま中継することを確認する.

    このプロジェクトにはpytest-asyncio等の非同期テスト基盤がないため、
    `asyncio.run()`で素朴に非同期ジェネレータを消費して検証する。
    """
    import asyncio

    def fake_iter_chunks(gcs_path: str):
        yield b"line1\n"
        yield b"line2\n"

    async def _collect() -> list[bytes]:
        with patch.object(svc, "iter_battle_log_chunks", side_effect=fake_iter_chunks):
            return [
                c async for c in svc.stream_battle_log_chunks("battle-logs/x.ndjson")
            ]

    chunks = asyncio.run(_collect())
    assert chunks == [b"line1\n", b"line2\n"]

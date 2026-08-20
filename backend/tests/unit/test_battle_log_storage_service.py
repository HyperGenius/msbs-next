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


def test_upload_battle_log_streams_ndjson_without_content_encoding() -> None:
    """アップロードがチャンクバッファ書き込みで、Content-Encoding未設定であることを確認する.

    GCS側は非圧縮のプレーンテキストで保存し、圧縮はCloud Run側のGZipMiddlewareに
    任せる設計（Issue #493）。ここでContent-Encoding: gzipを付けてしまうと、
    アップロード時にテキストを実際にgzip圧縮していないため「メタデータ上は圧縮済みを
    謳っているのに中身は生テキスト」という不整合になる。

    また、全件を1個の巨大な文字列に組み立ててから`upload_from_string()`する実装は
    ログサイズ分のメモリが追加で必要になる（Copilotレビュー指摘、PR #495）ため、
    `blob.open("w")`でストリーミング書き込みになっていることも確認する。1行ずつ
    `write()`していた初期実装をやめ、`_STREAM_CHUNK_SIZE`分バッファしてまとめて
    書き込む方式に変更している（write()呼び出し回数削減、Issue #497）。この程度の
    小さいログでは1回のwrite呼び出しに収まる。
    """
    log_id = uuid.uuid4()
    mock_file = MagicMock()
    mock_blob = MagicMock()
    mock_blob.open.return_value.__enter__.return_value = mock_file
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    with patch.object(svc, "_client", return_value=mock_client):
        path = svc.upload_battle_log(log_id, [{"msg": "hello"}, {"msg": "world"}])

    assert path == f"battle-logs/{log_id}.ndjson"
    mock_blob.open.assert_called_once_with("w", content_type="application/x-ndjson")
    written = "".join(call.args[0] for call in mock_file.write.call_args_list)
    assert "hello" in written
    assert "world" in written


def test_upload_battle_log_flushes_write_when_buffer_exceeds_chunk_size() -> None:
    """バッファが`_STREAM_CHUNK_SIZE`を超えたら、全件蓄積を待たず都度flushされることを確認する.

    行単位write()の呼び出し回数削減（Issue #497）が、バッファを無限に蓄積して
    メモリ削減効果を失っていないか（＝PR #495が対策したピークメモリ増加が
    再発していないか）を検証する。
    """
    log_id = uuid.uuid4()
    mock_file = MagicMock()
    mock_blob = MagicMock()
    mock_blob.open.return_value.__enter__.return_value = mock_file
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    # 1エントリあたり約10KB、_STREAM_CHUNK_SIZE(256KB)を跨ぐには30件程度必要。
    logs = [{"msg": "x" * 10_000, "i": i} for i in range(30)]

    with patch.object(svc, "_client", return_value=mock_client):
        svc.upload_battle_log(log_id, logs)

    assert mock_file.write.call_count > 1
    written = "".join(call.args[0] for call in mock_file.write.call_args_list)
    assert written.count("\n") == 30


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


def test_iter_battle_log_chunks_returns_empty_when_object_not_found() -> None:
    """GCSオブジェクトが存在しない場合、例外にせず空として扱うことを確認する.

    バケットのライフサイクルルールによる削除等でオブジェクトが失われていても、
    `/api/battles/{id}/logs`が500にならず空NDJSONを返せるようにするため
    （Copilotレビュー指摘、PR #495）。
    """
    from google.cloud.exceptions import NotFound

    mock_blob = MagicMock()
    mock_blob.open.side_effect = NotFound("not found")
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    with patch.object(svc, "_client", return_value=mock_client):
        chunks = list(svc.iter_battle_log_chunks("battle-logs/missing.ndjson"))

    assert chunks == []


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

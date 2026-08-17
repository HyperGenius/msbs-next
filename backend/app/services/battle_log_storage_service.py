"""バトルログをCloud Storage(GCS)へオフロード・読み出しするサービス（Issue #493）.

`battle_logs.logs`（Neon/Postgres）は閲覧のたびに全量がNeonの課金対象Network Transfer
として転送される（room_size=50/100規模で数十MB）。ログ本体をGCSへオフロードし、
Neonからは`gcs_path`（オブジェクトパス）のみを引く構成にすることで、この転送経路から
ログ本体を完全に外す。

配信は「署名付きURLへリダイレクトしてブラウザから直接GCSを取得させる」方式ではなく、
**Cloud Run自身がGCSオブジェクトをストリーム読み出しして中継する**方式を採る。
リダイレクト方式は IAM Credentials API の `signBlob` 権限、GCSバケットのCORS設定、
署名付きURLの有効期限・漏洩リスクといった追加の考慮点を持ち込むが、プロキシ方式では
そのいずれも不要になる（Cloud Runは自身のランタイムサービスアカウントの
`storage.objects.get`/`storage.objects.create`権限だけでよく、ブラウザは従来通り
Cloud Runの同一オリジンにのみアクセスする）。トレードオフとしてCloud Run自体の
転送量削減効果はないが、本Issueのスコープは「Neonの課金対象Network Transfer」の
削減であり、Cloud Run→ブラウザ間は既にGZipMiddleware（Issue #488）で対策済みのため
許容する。

GCSオブジェクトはプレーンテキストのNDJSON（`Content-Type: application/x-ndjson`）で
保存し、gzip圧縮はしない。圧縮はCloud Run側の`GZipMiddleware`がブラウザへの配信時に
行うため、GCS側でContent-Encodingメタデータを管理する必要がない
（設定を怠ると「配信できているのにブラウザ側で解凍されない」事故になるため、
そもそもその経路自体をなくした）。
"""

import json
import logging
import os
import uuid
from collections.abc import AsyncIterator, Iterator

logger = logging.getLogger(__name__)

_BUCKET_ENV_VAR = "BATTLE_LOG_GCS_BUCKET"
_OBJECT_PREFIX = "battle-logs"

# GCSからの読み出し・書き込みを1回のI/Oで扱うチャンクサイズ。ブラウザへの配信は
# StreamingResponseがこの単位でチャンク送出する。
_STREAM_CHUNK_SIZE = 256 * 1024


def _bucket_name() -> str:
    bucket = os.environ.get(_BUCKET_ENV_VAR)
    if not bucket:
        raise RuntimeError(f"{_BUCKET_ENV_VAR} is not set")
    return bucket


def object_path_for(battle_log_id: uuid.UUID) -> str:
    """バトルログIDからGCSオブジェクトパス（バケット内相対パス）を算出する."""
    return f"{_OBJECT_PREFIX}/{battle_log_id}.ndjson"


def _client():  # type: ignore[no-untyped-def]
    # モジュールトップレベルでimportすると、GCSを使わない開発環境・テスト環境でも
    # google-cloud-storageのインストールが必須になってしまうため遅延importする。
    from google.cloud import storage

    return storage.Client()


def logs_to_ndjson_text(logs: list[dict]) -> str:
    """ログdictの列をNDJSON（1行1エントリ）のテキストに変換する."""
    if not logs:
        return ""
    return "\n".join(json.dumps(entry, ensure_ascii=False) for entry in logs) + "\n"


def upload_battle_log(battle_log_id: uuid.UUID, logs: list[dict]) -> str:
    """バトルログをGCSへNDJSONテキストとしてアップロードする.

    Returns:
        アップロード先のGCSオブジェクトパス（バケット内相対パス）。
    """
    path = object_path_for(battle_log_id)
    body = logs_to_ndjson_text(logs)
    bucket = _client().bucket(_bucket_name())
    blob = bucket.blob(path)
    blob.upload_from_string(body, content_type="application/x-ndjson")
    return path


def upload_ndjson_text(battle_log_id: uuid.UUID, ndjson_text: str) -> str:
    """既にNDJSONテキスト化済みのログをそのままGCSへアップロードする.

    #489のJSONBマイグレーションで退避されたバックアップ（JSON配列テキスト）を
    NDJSONへ変換した上でアップロードする復旧用途など、`list[dict]`を経由せず
    テキストのまま扱いたい場合に使う。
    """
    path = object_path_for(battle_log_id)
    bucket = _client().bucket(_bucket_name())
    blob = bucket.blob(path)
    blob.upload_from_string(ndjson_text, content_type="application/x-ndjson")
    return path


def iter_battle_log_chunks(gcs_path: str) -> Iterator[bytes]:
    """GCSオブジェクトをチャンク単位で読み出す同期ジェネレータ.

    呼び出し側（`stream_battle_log_chunks`）がスレッドプール経由で呼ぶことを
    前提とした同期I/O実装。GCSクライアントライブラリ自体が非同期I/Oに
    対応していないため。
    """
    bucket = _client().bucket(_bucket_name())
    blob = bucket.blob(gcs_path)
    with blob.open("rb") as f:
        while True:
            chunk = f.read(_STREAM_CHUNK_SIZE)
            if not chunk:
                break
            yield chunk


async def stream_battle_log_chunks(gcs_path: str) -> AsyncIterator[bytes]:
    """GCSオブジェクトをチャンク単位で読み出す非同期ジェネレータ.

    `google-cloud-storage`は同期APIのみのため、イベントループをブロックしない
    よう各読み出しをスレッドプールへ逃がす（`main.py`の`StreamingResponse`から
    そのまま渡せる）。
    """
    from starlette.concurrency import run_in_threadpool

    iterator = await run_in_threadpool(lambda: iter(iter_battle_log_chunks(gcs_path)))
    while True:
        chunk = await run_in_threadpool(next, iterator, None)
        if chunk is None:
            break
        yield chunk


def offload_battle_log_to_gcs(battle_log_id: uuid.UUID, logs: list[dict]) -> bool:
    """1件のバトルログをGCSへアップロードし、成功時のみ`gcs_path`を設定してNeon側の`logs`をNULL化する.

    バトル終了時の同期書き込み経路（`battle_logs.logs`への保存、既存の信頼性を
    維持する）とは切り離したベストエフォートの後処理として呼ぶ。GCSアップロード・
    DB更新のいずれかが失敗しても例外を投げず、`gcs_path`はNULLのまま残す
    （write-behind方式）。読み出し側（`get_battle_logs`）は`gcs_path`が未設定の
    場合Neonの`logs`列へ自動フォールバックするため、この関数の失敗はユーザーに
    影響しない。失敗分・未実施分は`scripts/maintenance/offload_battle_logs_to_gcs.py`
    の定期実行が`gcs_path IS NULL`な行を対象に再試行する。

    Returns:
        オフロードが完了した（GCSアップロード・DB更新とも成功した）場合True。
    """
    try:
        gcs_path = upload_battle_log(battle_log_id, logs)
    except Exception:
        logger.exception(
            "Failed to upload battle log %s to GCS; will retry via the backfill job",
            battle_log_id,
        )
        return False

    # 呼び出し元（リクエストのBackgroundTasks等）のセッションは既にクローズ済みの
    # 可能性があるため、この関数専用に新しいセッションを開く。
    from sqlmodel import Session

    from app.db import engine
    from app.models.models import BattleLogRecord

    try:
        with Session(engine) as session:
            record = session.get(BattleLogRecord, battle_log_id)
            if record is None:
                logger.warning(
                    "BattleLogRecord %s not found when finalizing GCS offload",
                    battle_log_id,
                )
                return False
            record.gcs_path = gcs_path
            record.logs = []
            session.add(record)
            session.commit()
    except Exception:
        logger.exception(
            "Uploaded battle log %s to GCS but failed to update gcs_path; "
            "logs remain in Neon and will be retried via the backfill job",
            battle_log_id,
        )
        return False

    return True

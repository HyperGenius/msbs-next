"""GET /api/battles/{battle_id}/logs のGCSオフロード分岐のテスト（Issue #493）."""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.models import BattleLogRecord, BattleResult


def _create_battle_with_log(
    session: Session, *, gcs_path: str | None, logs: list[dict]
) -> BattleResult:
    log_record = BattleLogRecord(logs=logs, gcs_path=gcs_path)
    session.add(log_record)
    session.flush()

    battle = BattleResult(
        battle_log_id=log_record.id,
        win_loss="WIN",
        created_at=datetime.now(UTC),
    )
    session.add(battle)
    session.commit()
    session.refresh(battle)
    return battle


def test_get_battle_logs_falls_back_to_neon_when_gcs_path_unset(
    client: TestClient, session: Session
) -> None:
    """gcs_path未設定の場合は従来通りNeonのlogs列から配信されることを確認する."""
    battle = _create_battle_with_log(
        session, gcs_path=None, logs=[{"msg": "from-neon"}]
    )

    res = client.get(f"/api/battles/{battle.id}/logs")

    assert res.status_code == 200
    lines = [line for line in res.text.splitlines() if line.strip()]
    assert len(lines) == 1
    assert "from-neon" in lines[0]


def test_get_battle_logs_streams_from_gcs_when_gcs_path_set(
    client: TestClient, session: Session
) -> None:
    """gcs_path設定済みの場合はGCSオブジェクトを中継配信することを確認する.

    Neonのlogs列（この場合は空リスト、オフロード完了後の実際の状態を模す）ではなく
    GCS側のバイト列がそのままレスポンスに使われることを検証する。
    """
    battle = _create_battle_with_log(
        session, gcs_path="battle-logs/mocked.ndjson", logs=[]
    )

    def fake_stream(gcs_path: str):
        async def _gen():
            yield b'{"msg": "from-gcs"}\n'

        return _gen()

    with patch("main.stream_battle_log_chunks", side_effect=fake_stream):
        res = client.get(f"/api/battles/{battle.id}/logs")

    assert res.status_code == 200
    lines = [line for line in res.text.splitlines() if line.strip()]
    assert len(lines) == 1
    assert "from-gcs" in lines[0]


def test_get_battle_logs_returns_empty_when_battle_log_id_missing(
    client: TestClient, session: Session
) -> None:
    """battle_log_idが存在しないバトルは空のNDJSONを返すことを確認する（既存挙動の回帰確認）."""
    battle = BattleResult(win_loss="WIN", created_at=datetime.now(UTC))
    session.add(battle)
    session.commit()
    session.refresh(battle)

    res = client.get(f"/api/battles/{battle.id}/logs")

    assert res.status_code == 200
    assert res.text.strip() == ""


def test_get_battle_logs_404_for_unknown_battle(client: TestClient) -> None:
    """存在しないbattle_idは404になることを確認する（既存挙動の回帰確認）."""
    res = client.get(f"/api/battles/{uuid.uuid4()}/logs")
    assert res.status_code == 404

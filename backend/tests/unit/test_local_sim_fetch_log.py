"""ローカルシミュレータの fetch-log（本番の解析用ログの取得）のテスト."""

import gzip
import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from app.models.models import BattleResult
from app.services import battle_log_storage_service as storage
from scripts.simulation.local_sim.analysis import load_report
from scripts.simulation.local_sim.fetch_log import (
    BattleResultNotFoundError,
    build_battle_record,
    find_battle_result,
    save_production_generation,
)
from scripts.simulation.local_sim.generations import (
    list_generations,
    prune_generations,
    read_manifest,
)

_PLAYER = {"id": "p", "name": "Gundam", "pilot_name": "Amuro"}
_ENEMY = {"id": "e", "name": "Zaku II", "pilot_name": None}
_LOGS = [
    {
        "timestamp": 0.1,
        "actor_id": "p",
        "action_type": "ATTACK",
        "target_id": "e",
        "fuzzy_scores": {"attack": 0.8},
        "strategy_mode": "AGGRESSIVE",
    },
    {"timestamp": 0.1, "actor_id": "e", "action_type": "MOVE"},
    {"timestamp": 0.2, "actor_id": "e", "action_type": "DESTROYED", "target_id": "e"},
]


def _result(**kwargs) -> BattleResult:
    fields = {
        "user_id": "user_1",
        "room_id": uuid.uuid4(),
        "battle_log_id": uuid.uuid4(),
        "win_loss": "WIN",
        "environment": "SPACE",
        "theater_id": "southeast_asia_jungle",
        "minovsky_density": 0.3,
        "kills": 1,
        "player_info": _PLAYER,
        "enemies_info": [_ENEMY],
        "obstacles_info": [],
        "map_bounds": [0.0, 2000.0],
    }
    return BattleResult(**(fields | kwargs))


def test_build_battle_record_uses_result_and_logs() -> None:
    """バトル結果の表示用項目と解析用ログから、1戦分の記録を作ること."""
    record = build_battle_record(_result(), _LOGS, "密林", "宇宙", "space")

    assert record.index == 1
    assert record.seed is None
    assert record.win_loss == "WIN"
    assert record.elapsed_time == 0.2
    assert record.steps_used == 2
    assert record.theater_name == "密林"
    assert record.logs[0]["fuzzy_scores"] == {"attack": 0.8}


def test_build_battle_record_rejects_result_without_view_fields() -> None:
    """表示用項目が無い結果は取り込まないこと."""
    with pytest.raises(ValueError, match="表示用項目"):
        build_battle_record(_result(map_bounds=None), _LOGS, None, None, None)


def test_build_battle_record_rejects_draw() -> None:
    """WIN / LOSE 以外の勝敗は取り込まないこと."""
    with pytest.raises(ValueError, match="DRAW"):
        build_battle_record(_result(win_loss="DRAW"), _LOGS, None, None, None)


def test_find_battle_result_by_result_id(session: Session) -> None:
    """バトル結果IDで結果を選べること."""
    result = _result()
    session.add(result)
    session.commit()

    found, count = find_battle_result(session, result_id=result.id)

    assert found.id == result.id
    assert count == 1


def test_find_battle_result_by_room_prefers_user(session: Session) -> None:
    """ルームIDでは、ユーザーIDに合う結果を選び、件数を返すこと."""
    room_id = uuid.uuid4()
    first = _result(room_id=room_id, user_id="user_1")
    second = _result(room_id=room_id, user_id="user_2")
    session.add(first)
    session.add(second)
    session.commit()

    found, count = find_battle_result(session, room_id=room_id, user_id="user_2")
    assert (found.id, count) == (second.id, 1)

    _found, count = find_battle_result(session, room_id=room_id)
    assert count == 2


def test_find_battle_result_not_found(session: Session) -> None:
    """結果が無ければエラーにすること."""
    with pytest.raises(BattleResultNotFoundError):
        find_battle_result(session, result_id=uuid.uuid4())
    with pytest.raises(BattleResultNotFoundError):
        find_battle_result(session, room_id=uuid.uuid4())


def test_find_battle_result_requires_exactly_one_target(session: Session) -> None:
    """バトル結果IDとルームIDは、どちらか1つだけ指定できること."""
    with pytest.raises(ValueError, match="どちらか1つ"):
        find_battle_result(session)
    with pytest.raises(ValueError, match="どちらか1つ"):
        find_battle_result(session, result_id=uuid.uuid4(), room_id=uuid.uuid4())


def test_save_production_generation_writes_viewable_generation(
    session: Session, tmp_path: Path
) -> None:
    """本番の1戦を、/dev/sim が読める1戦だけの世代として保存すること."""
    result = _result()

    path, manifest, removed = save_production_generation(
        result, _LOGS, session, generations_dir=tmp_path
    )

    assert removed == []
    saved = read_manifest(path)
    assert saved.source == "production"
    assert saved.source_battle_result_id == str(result.id)
    assert saved.source_room_id == str(result.room_id)
    assert saved.label == f"prod-{str(result.id)[:8]}"
    assert saved.roster_name is None and saved.seed is None
    assert saved.summary.wins == 1
    assert saved.theater_id == "southeast_asia_jungle"
    battle = json.loads((path / "battle_001.json").read_text(encoding="utf-8"))
    assert battle["theater_name"] == "東南アジア密林"
    assert battle["logs"][0]["fuzzy_scores"] == {"attack": 0.8}
    assert load_report(path, manifest).battles == 1


def test_production_generation_counts_toward_generation_limit(
    session: Session, tmp_path: Path
) -> None:
    """本番の世代も世代管理の対象で、ピン留めすれば残ること."""
    for _ in range(3):
        save_production_generation(
            _result(), _LOGS, session, generations_dir=tmp_path, keep=2
        )

    assert len(list_generations(tmp_path)) == 2
    pinned, _manifest, _removed = save_production_generation(
        _result(), _LOGS, session, pinned=True, generations_dir=tmp_path, keep=1
    )
    assert pinned.exists()
    prune_generations(tmp_path, keep=0)
    assert [p for p, _m in list_generations(tmp_path)] == [pinned]


def test_save_production_generation_rejects_bad_label(
    session: Session, tmp_path: Path
) -> None:
    """不正なラベルでは世代を残さないこと."""
    with pytest.raises(ValueError):
        save_production_generation(
            _result(), _LOGS, session, label="../x", generations_dir=tmp_path
        )
    assert list(tmp_path.iterdir()) == []


def test_download_analysis_log_round_trips_gzip_ndjson(monkeypatch) -> None:
    """解析用ログ（gzip した NDJSON）を、項目を削らずに読めること."""
    monkeypatch.setenv("BATTLE_LOG_GCS_BUCKET", "bucket")
    body = "".join(json.dumps(log) + "\n" for log in _LOGS).encode()
    blob = MagicMock()
    blob.download_as_bytes.return_value = gzip.compress(body)
    client = MagicMock()
    client.bucket.return_value.blob.return_value = blob
    log_id = uuid.uuid4()

    with patch.object(storage, "_client", return_value=client):
        logs = storage.download_analysis_log(log_id)

    assert logs == _LOGS
    client.bucket.return_value.blob.assert_called_once_with(
        f"analysis-logs/{log_id}.ndjson.gz"
    )


def test_download_analysis_log_raises_when_missing(monkeypatch) -> None:
    """解析用ログが無ければ専用のエラーにすること."""
    from google.cloud.exceptions import NotFound

    monkeypatch.setenv("BATTLE_LOG_GCS_BUCKET", "bucket")
    blob = MagicMock()
    blob.download_as_bytes.side_effect = NotFound("gone")
    client = MagicMock()
    client.bucket.return_value.blob.return_value = blob

    with patch.object(storage, "_client", return_value=client):
        with pytest.raises(storage.AnalysisLogNotFoundError):
            storage.download_analysis_log(uuid.uuid4())

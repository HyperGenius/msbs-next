"""配信用ログ（replay）への変換のテスト."""

import json
import uuid
from pathlib import Path

from app.engine.replay_log import (
    REPLAY_LOG_VERSION,
    ReplayLogEntry,
    ReplayLogHeader,
    to_replay_logs,
)
from app.models.models import BattleLog, Vector3
from scripts.simulation.local_sim.replay_fixture import (
    build_replay_fixture,
    read_replay_fixture,
    write_replay_fixture,
)
from scripts.simulation.local_sim.roster import load_roster
from tests.unit.test_local_sim_run import (  # noqa: F401  フィクスチャとして使う
    offline_fixture,
    roster_path_fixture,
)

_A = uuid.UUID(int=1)
_B = uuid.UUID(int=2)
_C = uuid.UUID(int=3)


def _log(action_type: str, actor: uuid.UUID = _A, **kwargs) -> BattleLog:
    fields = {
        "timestamp": 1.0,
        "actor_id": actor,
        "action_type": action_type,
        "message": f"{action_type} のメッセージ",
        "position_snapshot": Vector3(x=1.0, y=0.0, z=2.0),
    }
    return BattleLog(**(fields | kwargs))


def _entries(logs: list[BattleLog]) -> list[dict]:
    return to_replay_logs(logs)[1:]


def test_first_line_is_header_with_version() -> None:
    """先頭行はバージョンだけを持つヘッダーで、ログが無くても出すこと."""
    assert to_replay_logs([]) == [{"replay_version": REPLAY_LOG_VERSION}]
    ReplayLogHeader.model_validate(to_replay_logs([_log("MOVE")])[0])


def test_drops_ai_decision() -> None:
    """AI_DECISION の行を除くこと."""
    entries = _entries([_log("AI_DECISION"), _log("MOVE")])
    assert [e["action_type"] for e in entries] == ["MOVE"]


def test_keeps_target_selection_only_when_target_changes() -> None:
    """TARGET_SELECTION は機体ごとに、相手が前の行と変わった行だけ残すこと."""
    logs = [
        _log("TARGET_SELECTION", _A, target_id=_B, timestamp=0.1),
        _log("TARGET_SELECTION", _A, target_id=_B, timestamp=0.2),
        _log("TARGET_SELECTION", _C, target_id=_B, timestamp=0.2),
        _log("TARGET_SELECTION", _A, target_id=_C, timestamp=0.3),
        _log("TARGET_SELECTION", _A, target_id=None, timestamp=0.4),
        _log("TARGET_SELECTION", _A, target_id=None, timestamp=0.5),
        _log("TARGET_SELECTION", _A, target_id=_C, timestamp=0.6),
    ]
    kept = [(e["actor_id"], e.get("target_id"), e["timestamp"]) for e in _entries(logs)]
    assert kept == [
        (str(_A), str(_B), 0.1),
        (str(_C), str(_B), 0.2),
        (str(_A), str(_C), 0.3),
        (str(_A), None, 0.4),
        (str(_A), str(_C), 0.6),
    ]


def test_omits_null_and_analysis_fields() -> None:
    """値が null の項目と、描画に使わない項目を省くこと。is_crit は true のときだけ持つこと."""
    log = _log(
        "ATTACK",
        target_id=_B,
        damage=120,
        weapon_id="beam_rifle",
        weapon_name="ビームライフル",
        target_max_hp=800,
        fuzzy_scores={"attack": 0.8},
        minovsky_hit_multiplier=0.9,
        strategy_mode="AGGRESSIVE",
        team_id="team-a",
        attack_sector="FRONT",
        hit_part="TORSO",
        weapon_slot_role="RIGHT_ARM",
    )
    (entry,) = _entries([log])
    assert entry == {
        "timestamp": 1.0,
        "actor_id": str(_A),
        "action_type": "ATTACK",
        "target_id": str(_B),
        "damage": 120,
        "message": "ATTACK のメッセージ",
        "position_snapshot": {"x": 1.0, "y": 0.0, "z": 2.0},
        "weapon_id": "beam_rifle",
        "weapon_name": "ビームライフル",
        "target_max_hp": 800,
    }
    (crit,) = _entries([log.model_copy(update={"is_crit": True})])
    assert crit["is_crit"] is True


def test_keeps_viewer_fields() -> None:
    """ビューアと結果画面のログ表示が使う項目を残すこと."""
    log = _log(
        "MELEE_COMBO",
        target_id=_B,
        damage=300,
        velocity_snapshot=Vector3(x=1.0, y=0.0, z=-1.0),
        heading=90.0,
        skill_activated=True,
        combo_count=2,
        combo_message="2Combo 300ダメージ!!",
        chatter="もらった！",
        details={"en": 120, "reason_code": "EN_SHORTAGE"},
    )
    (entry,) = _entries([log])
    for key in (
        "velocity_snapshot",
        "heading",
        "skill_activated",
        "combo_count",
        "combo_message",
        "chatter",
        "details",
    ):
        assert key in entry, key
    assert entry["details"] == {"en": 120, "reason_code": "EN_SHORTAGE"}


def test_omits_message_only_for_move_wait_target_selection() -> None:
    """MOVE・WAIT・TARGET_SELECTION の message を省き、ほかの行は残すこと."""
    logs = [
        _log(action, timestamp=0.1 * i)
        for i, action in enumerate(
            ["MOVE", "WAIT", "TARGET_SELECTION", "MISS", "DETECTION", "DESTROYED"]
        )
    ]
    has_message = {e["action_type"]: "message" in e for e in _entries(logs)}
    assert has_message == {
        "MOVE": False,
        "WAIT": False,
        "TARGET_SELECTION": False,
        "MISS": True,
        "DETECTION": True,
        "DESTROYED": True,
    }


def test_rounds_floats() -> None:
    """座標・速度・向きを小数1桁、時刻を2桁に丸め、-0.0 を 0.0 にすること."""
    log = _log(
        "MOVE",
        timestamp=12.300000000000011,
        position_snapshot=Vector3(x=7476.964744799866, y=-0.04, z=4449.970026064315),
        velocity_snapshot=Vector3(x=-23.660280361184313, y=0.0, z=13.05),
        heading=-100.80000000000001,
    )
    (entry,) = _entries([log])
    assert entry["timestamp"] == 12.3
    assert entry["position_snapshot"] == {"x": 7477.0, "y": 0.0, "z": 4450.0}
    assert entry["velocity_snapshot"] == {"x": -23.7, "y": 0.0, "z": 13.1}
    assert entry["heading"] == -100.8
    assert '"y": 0.0' in json.dumps(entry["position_snapshot"])


def test_destroyed_has_no_velocity_snapshot() -> None:
    """DESTROYED の行は velocity_snapshot を持たないこと（フロントの補間の前提）."""
    (entry,) = _entries([_log("DESTROYED")])
    assert "velocity_snapshot" not in entry


def test_does_not_modify_input() -> None:
    """入力のログを書き換えないこと."""
    log = _log("ATTACK", details={"en": 10}, velocity_snapshot=Vector3(x=0.123))
    before = log.model_dump()
    to_replay_logs([log])
    assert log.model_dump() == before


# --- ローカルシミュレータの戦闘 ---


def test_fixture_matches_current_conversion() -> None:
    """フィクスチャの配信用ログが、今の変換関数の出力と一致すること.

    変換を変えたら replay-fixture でフィクスチャを作り直す。
    旧形式から変換しても、エンジンのログから変換したのと同じ結果になる。
    """
    fixture = read_replay_fixture()
    logs = [BattleLog.model_validate(line) for line in fixture.stored_logs]
    assert to_replay_logs(logs) == fixture.replay_logs


def test_fixture_lines_match_schema_and_are_json() -> None:
    """全行がスキーマに合い、JSON の往復で変わらないこと."""
    fixture = read_replay_fixture()
    header, *entries = fixture.replay_logs
    ReplayLogHeader.model_validate(header)
    for entry in entries:
        ReplayLogEntry.model_validate(entry)
        assert None not in entry.values()
    assert json.loads(json.dumps(fixture.replay_logs)) == fixture.replay_logs


def test_conversion_is_deterministic() -> None:
    """同じ入力なら、同じ JSON になること."""
    fixture = read_replay_fixture()
    logs = [BattleLog.model_validate(line) for line in fixture.stored_logs]
    first = json.dumps(to_replay_logs(logs), ensure_ascii=False)
    assert json.dumps(to_replay_logs(logs), ensure_ascii=False) == first


def test_replay_fixture_is_reproducible(
    roster_path: Path, tmp_path: Path, offline: None
) -> None:
    """同じロスター・同じ seed なら、DB を使わずに同じバイト列を書くこと."""
    roster = load_roster(str(roster_path))
    paths = [tmp_path / "a.json.gz", tmp_path / "b.json.gz"]
    for path in paths:
        write_replay_fixture(build_replay_fixture(roster, seed=7, max_steps=50), path)
    assert paths[0].read_bytes() == paths[1].read_bytes()

    fixture = read_replay_fixture(paths[0])
    assert fixture.max_steps == 50
    assert fixture.player_info["id"] not in {e["id"] for e in fixture.enemies_info}
    logs = [BattleLog.model_validate(line) for line in fixture.stored_logs]
    assert to_replay_logs(logs) == fixture.replay_logs

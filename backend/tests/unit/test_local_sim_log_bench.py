"""ローカルシミュレータの log-bench（ログのサイズと端末負荷の計測）のテスト."""

import inspect
import json
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

import main
from app.models.models import BattleLog, Vector3
from app.services.matching_service import MatchingService
from scripts.simulation.local_sim import log_bench
from scripts.simulation.local_sim.log_bench import (
    LogBenchOptions,
    draft_format,
    draft_no_message_format,
    find_log_bench,
    format_log_bench,
    format_log_comparison,
    gzip_size,
    individual_roster,
    measure_lines,
    run_log_bench,
    stored_format,
)
from scripts.simulation.local_sim.roster import load_roster
from tests.unit.test_local_sim_run import (  # noqa: F401  フィクスチャとして使う
    offline_fixture,
    roster_path_fixture,
)

_SHORT_STEPS = 100
_NOW = datetime(2026, 10, 6, 21, 0, 0).astimezone()
_A = str(uuid.UUID(int=1))
_B = str(uuid.UUID(int=2))
_C = str(uuid.UUID(int=3))


def _log(action_type: str, actor: str = _A, **kwargs) -> BattleLog:
    fields = {
        "timestamp": 1.0,
        "actor_id": actor,
        "action_type": action_type,
        "message": f"{action_type} のメッセージ",
        "position_snapshot": Vector3(x=1.234, y=0.0, z=-5.678),
    }
    return BattleLog(**(fields | kwargs))


# --- 本番の設定との一致 ---


def test_constants_match_production_settings() -> None:
    """圧縮レベルと定員が、本番の GZipMiddleware と MatchingService の既定値と一致すること."""
    gzip_default = inspect.signature(GZipMiddleware).parameters["compresslevel"]
    assert log_bench.GZIP_LEVEL == gzip_default.default
    gzip_options = next(
        m.kwargs for m in main.app.user_middleware if m.cls is GZipMiddleware
    )
    assert "compresslevel" not in gzip_options

    room_size = inspect.signature(MatchingService).parameters["room_size"]
    assert log_bench.PRODUCTION_ROOM_SIZE == room_size.default


def test_gzip_size_matches_streaming_gzip_middleware() -> None:
    """チャンクごとに配信したときの GZipMiddleware の転送量と一致すること."""
    lines = [
        {"i": i, "message": f"メッセージ {i % 37}", "x": i * 0.37} for i in range(30000)
    ]
    data = "".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines)
    body = data.encode("utf-8")
    chunk = log_bench.STREAM_CHUNK_SIZE

    app = FastAPI()
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.get("/logs")
    def logs() -> StreamingResponse:
        chunks = (body[i : i + chunk] for i in range(0, len(body), chunk))
        return StreamingResponse(chunks, media_type="application/x-ndjson")

    with TestClient(app) as client, client.stream("GET", "/logs") as response:
        assert response.headers["content-encoding"] == "gzip"
        assert b"".join(response.iter_bytes()) == body
        transferred = response.num_bytes_downloaded

    assert len(body) > chunk * 2
    assert gzip_size(body) == transferred


# --- ロスター ---


def test_individual_roster_duplicates_entries_with_stable_ids(
    roster_path: Path,
) -> None:
    """先頭から順に複製して機体数を揃え、ID を重ねず、全機を個人戦にすること."""
    roster = load_roster(str(roster_path))
    roster.entries[0].snapshot["team_id"] = "A"
    original_ids = [e.snapshot["id"] for e in roster.entries]

    padded = individual_roster(roster, 10)

    assert len(padded.entries) == 10
    ids = [e.snapshot["id"] for e in padded.entries]
    assert len(set(ids)) == 10
    assert ids[: len(original_ids)] == original_ids
    assert [e.snapshot["name"] for e in padded.entries[len(original_ids) :]] == [
        roster.entries[i % len(original_ids)].snapshot["name"]
        for i in range(10 - len(original_ids))
    ]
    assert all(e.snapshot["team_id"] is None for e in padded.entries)
    assert [e.source.mobile_suit_id for e in padded.entries[4:]] == ids[4:]
    # 元のロスターは書き換えない。
    assert roster.entries[0].snapshot["team_id"] == "A"
    assert len(roster.entries) == len(original_ids)
    assert individual_roster(roster, 10) == padded


def test_individual_roster_rejects_invalid_units(roster_path: Path) -> None:
    """機体数が 2 未満か、ロスターの機体数より少ないとエラーにすること."""
    roster = load_roster(str(roster_path))
    with pytest.raises(ValueError, match="2 以上"):
        individual_roster(roster, 1)
    with pytest.raises(ValueError, match="超えています"):
        individual_roster(roster, len(roster.entries) - 1)


# --- 形式 ---


def test_stored_format_strips_debug_fields() -> None:
    """デバッグ項目だけを消し、null の項目は残すこと."""
    lines = stored_format(
        [_log("AI_DECISION", fuzzy_scores={"a": 1}, minovsky_hit_multiplier=0.5)]
    )
    assert "fuzzy_scores" not in lines[0]
    assert "minovsky_hit_multiplier" not in lines[0]
    assert lines[0]["actor_id"] == _A
    assert lines[0]["chatter"] is None


def test_draft_format_applies_estimated_reductions() -> None:
    """AI_DECISION を除き、相手が変わった TARGET_SELECTION だけ残し、null を省いて丸めること."""
    logs = [
        _log("AI_DECISION"),
        _log("TARGET_SELECTION", target_id=_B),
        _log("TARGET_SELECTION", target_id=_B),
        _log("TARGET_SELECTION", actor=_C, target_id=_B),
        _log("TARGET_SELECTION", target_id=_C),
        _log("TARGET_SELECTION", target_id=_B),
        _log("MOVE", velocity_snapshot=Vector3(x=0.06, y=0.0, z=2.25)),
        _log("ATTACK", target_id=_B, damage=120, heading=12.345),
    ]

    lines = draft_format(logs)

    assert [(line["action_type"], line["actor_id"]) for line in lines] == [
        ("TARGET_SELECTION", _A),
        ("TARGET_SELECTION", _C),
        ("TARGET_SELECTION", _A),
        ("TARGET_SELECTION", _A),
        ("MOVE", _A),
        ("ATTACK", _A),
    ]
    assert all(None not in line.values() for line in lines)
    assert "chatter" not in lines[0]
    assert lines[4]["position_snapshot"] == {"x": 1.2, "y": 0.0, "z": -5.7}
    assert lines[4]["velocity_snapshot"] == {"x": 0.1, "y": 0.0, "z": 2.2}
    assert lines[5]["heading"] == 12.3
    assert lines[5]["damage"] == 120
    assert lines[4]["message"] == "MOVE のメッセージ"

    no_message = draft_no_message_format(logs)
    assert [("message" in line) for line in no_message] == [
        False,
        False,
        False,
        False,
        False,
        True,
    ]


# --- 計測 ---


def test_measure_lines_breaks_down_size_by_action_and_field() -> None:
    """行・項目ごとの内訳の合計が、NDJSON 全体のサイズと一致すること."""
    lines = stored_format(
        [_log("MOVE"), _log("MOVE"), _log("ATTACK", target_id=_B, damage=10)]
    )
    ndjson = "".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines)

    metrics = measure_lines(lines)

    assert metrics.lines == 3
    assert metrics.raw_bytes == len(ndjson.encode("utf-8"))
    assert metrics.gzip_bytes == gzip_size(ndjson.encode("utf-8"))
    assert {k: v.lines for k, v in metrics.actions.items()} == {"MOVE": 2, "ATTACK": 1}
    assert sum(a.bytes for a in metrics.actions.values()) == metrics.raw_bytes
    # 1行あたり、括弧2つと改行から、最後の項目の区切り `, ` を引いた 1 バイト。
    assert metrics.overhead_bytes == metrics.lines
    assert (
        sum(f.bytes for f in metrics.fields.values()) + metrics.overhead_bytes
        == metrics.raw_bytes
    )
    damage = metrics.fields["damage"]
    assert damage.lines == 3
    assert damage.null_bytes == 2 * len('"damage": null, ')
    assert metrics.fields["message"].null_bytes == 0
    sizes = [f.bytes for f in metrics.fields.values()]
    assert sizes == sorted(sizes, reverse=True)


def _bench(roster_path: Path, bench_dir: Path, **kwargs):
    options = LogBenchOptions(
        **({"units": 6, "max_steps": _SHORT_STEPS, "parse": False} | kwargs)
    )
    return run_log_bench(
        load_roster(str(roster_path)),
        options,
        bench_dir=bench_dir,
        now=_NOW,
        progress=lambda _m: None,
    )


def test_log_bench_is_reproducible_with_same_seed(
    roster_path: Path, tmp_path: Path, offline: None
) -> None:
    """同じロスター・同じ seed なら、DB を使わずに同じ値を出すこと."""
    path_a, a = _bench(roster_path, tmp_path, label="a")
    path_b, b = _bench(roster_path, tmp_path, label="b")

    assert path_a == tmp_path / "20261006-210000_a.json"
    assert a.units == 6
    assert a.roster_units == 4
    assert a.steps_used <= _SHORT_STEPS
    assert list(a.formats) == list(log_bench.LOG_FORMATS)
    assert a.formats == b.formats
    stored = a.formats["stored"]
    assert stored.lines > 0
    assert stored.gzip_bytes < stored.raw_bytes
    assert a.formats["draft"].raw_bytes < stored.raw_bytes
    assert all(m.parse is None for m in a.formats.values())

    assert find_log_bench(str(path_a), bench_dir=tmp_path) == a
    assert find_log_bench("20261006-210000_b", bench_dir=tmp_path) == b
    assert find_log_bench("a", bench_dir=tmp_path) == a
    with pytest.raises(ValueError, match="複数"):
        find_log_bench("2026", bench_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        find_log_bench("missing", bench_dir=tmp_path)

    _path_c, c = _bench(roster_path, tmp_path, label="a", seed=700)
    assert c.bench_id == "20261006-210000_a-2"
    assert c.formats != a.formats


def test_log_bench_rejects_unknown_format(roster_path: Path, tmp_path: Path) -> None:
    """無い形式を指定すると、戦闘を回す前にエラーにすること."""
    with pytest.raises(ValueError, match="replay"):
        _bench(roster_path, tmp_path, formats=["stored", "replay"])
    assert not tmp_path.joinpath("20261006-210000_run_test.json").exists()


@pytest.mark.skipif(log_bench.node_path() is None, reason="node が無い")
def test_log_bench_measures_parse_with_node(roster_path: Path, tmp_path: Path) -> None:
    """Node でパースした行数がログの行数と一致し、時間とヒープを記録すること."""
    _path, result = _bench(
        roster_path,
        tmp_path,
        formats=["stored"],
        parse=True,
        parse_runs=2,
        ndjson_dir=tmp_path / "ndjson",
    )
    parse = result.formats["stored"].parse
    assert parse is not None
    assert parse.node_version.startswith("v")
    assert len(parse.parse_ms) == 2
    assert parse.heap_bytes > 0
    ndjson = tmp_path / "ndjson" / "stored.ndjson"
    assert ndjson.stat().st_size == result.formats["stored"].raw_bytes


def test_text_output_lists_formats_and_comparison(
    roster_path: Path, tmp_path: Path
) -> None:
    """計測結果の表と、形式ごとの比較を表示すること."""
    _path_a, a = _bench(roster_path, tmp_path, label="a", formats=["stored"])
    _path_b, b = _bench(roster_path, tmp_path, label="b", seed=700)

    text = format_log_bench(b)
    assert "=== ログの計測: 20261006-210000_b ===" in text
    assert "Slow 4G の転送" in text
    assert "項目ごとのサイズ（draft_no_message）" in text

    comparison = format_log_comparison(a, b)
    assert "[stored]" in comparison
    assert "B / A" in comparison
    assert "[draft]\n  A にはありません" in comparison
    assert "seed・最大ステップ数が違います" in comparison

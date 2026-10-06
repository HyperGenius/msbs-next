"""バトルログのサイズと端末の負荷を、保存形式ごとに計測する（log-bench / log-compare）.

ロスターの機体で1戦を回し、同じログを形式ごとに変換して測る。
結果は `log_bench/<日時>_<ラベル>.json` に保存し、2つの結果を並べて比べられる。
このモジュールは `app` を import する。DB には接続しない。
"""

import copy
import json
import platform
import shutil
import subprocess
import tempfile
import uuid
import zlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_core import to_jsonable_python

from app.engine.battle_utils import strip_debug_fields
from app.engine.constants import FUZZY_RULES_DIR
from app.models.models import BattleLog
from app.services.battle_execution import (
    DEFAULT_MAX_STEPS,
    prepare_battle_units,
    run_battle,
    seed_battle_rngs,
)
from app.services.battle_log_storage_service import (
    _STREAM_CHUNK_SIZE as STREAM_CHUNK_SIZE,
)
from app.services.battle_log_storage_service import logs_to_ndjson_text
from scripts.simulation.local_sim.analysis import _table
from scripts.simulation.local_sim.generations import (
    GENERATION_TIME_FORMAT,
    GitInfo,
    directory_hash,
    git_info,
    validate_label,
)
from scripts.simulation.local_sim.roster import LOCAL_SIM_DIR, Roster
from scripts.simulation.local_sim.run import (
    player_entry_index,
    roster_battle_state,
    roster_to_conditions,
)

LOG_BENCH_SCHEMA_VERSION = 1
LOG_BENCH_DIR = LOCAL_SIM_DIR / "log_bench"
# MatchingService の room_size の既定値（本番の定員）。
PRODUCTION_ROOM_SIZE = 50
DEFAULT_SEED = 632
# GZipMiddleware の compresslevel の既定値。main.py は既定値のまま使う。
GZIP_LEVEL = 9
# Lighthouse の Slow 4G（throughputKbps = 1.6 * 1024）と CPU のスロットリング倍率。
SLOW_4G_BITS_PER_SEC = 1.6 * 1024 * 1024
MOBILE_CPU_SLOWDOWN = 4
DEFAULT_PARSE_RUNS = 5
PARSE_BENCH_SCRIPT = Path(__file__).with_name("parse_bench.mjs")
# 複製した機体の ID を、元の ID と複製の番号から決めるための名前空間。
_DUPLICATE_ID_NAMESPACE = uuid.UUID("6f1d3b1e-6320-4c5a-9a6e-632000000632")

LogConverter = Callable[[list[BattleLog]], list[dict[str, Any]]]


# --- ロスター ---


def individual_roster(roster: Roster, units: int) -> Roster:
    """全機を個人戦にし、機体を先頭から順に複製して units 機にする.

    複製した機体の ID は元の ID と複製の番号から決める。同じロスターなら同じ ID になる。

    Raises:
        ValueError: units が 2 未満か、ロスターの機体数が units を超える場合
    """
    if units < 2:
        raise ValueError("--units は 2 以上で指定してください。")
    if len(roster.entries) > units:
        raise ValueError(
            f"ロスターの機体数（{len(roster.entries)}）が --units（{units}）を超えています。"
        )
    entries = [entry.model_copy(deep=True) for entry in roster.entries]
    originals = list(entries)
    for n in range(units - len(entries)):
        source = originals[n % len(originals)]
        copy_no = n // len(originals) + 1
        entry = source.model_copy(deep=True)
        new_id = str(
            uuid.uuid5(
                _DUPLICATE_ID_NAMESPACE, f"{source.snapshot.get('id')}:{copy_no}"
            )
        )
        entry.snapshot["id"] = new_id
        entry.source.mobile_suit_id = new_id
        entries.append(entry)
    for entry in entries:
        entry.snapshot["team_id"] = None
    return roster.model_copy(update={"entries": entries})


@dataclass
class BenchBattle:
    """計測に使う1戦の結果."""

    logs: list[BattleLog]
    elapsed_time: float
    steps_used: int
    timed_out: bool


def run_bench_battle(roster: Roster, seed: int, max_steps: int) -> BenchBattle:
    """ロスターの機体で1戦を実行する。プレイヤー機の選び方は `run` と同じ."""
    conditions = roster_to_conditions(roster.conditions)
    player_index = player_entry_index(roster)
    snapshots = [copy.deepcopy(entry.snapshot) for entry in roster.entries]
    player_snapshot = snapshots.pop(player_index)
    with roster_battle_state(roster):
        seed_battle_rngs(seed)
        player_unit, enemy_units = prepare_battle_units(player_snapshot, snapshots)
        outcome = run_battle(player_unit, enemy_units, conditions, max_steps=max_steps)
    simulator = outcome.simulator
    return BenchBattle(
        logs=simulator.logs,
        elapsed_time=simulator.elapsed_time,
        steps_used=outcome.steps_used,
        timed_out=not simulator.is_finished,
    )


# --- 形式 ---


def stored_format(logs: list[BattleLog]) -> list[dict[str, Any]]:
    """本番が保存・配信している形式（`strip_debug_fields()` の出力）."""
    return to_jsonable_python(strip_debug_fields(logs))


# 試算の形式で消す行と、message を消す行。
_DRAFT_DROPPED_ACTIONS = frozenset({"AI_DECISION"})
_DRAFT_MESSAGE_DROPPED_ACTIONS = frozenset({"MOVE", "WAIT", "TARGET_SELECTION"})
_DRAFT_FLOAT_DIGITS = 1


def _round_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, _DRAFT_FLOAT_DIGITS)
    if isinstance(value, dict):
        return {k: _round_floats(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_round_floats(v) for v in value]
    return value


def _draft_format(logs: list[BattleLog], drop_messages: bool) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    last_targets: dict[str, str | None] = {}
    for line in stored_format(logs):
        action = line["action_type"]
        if action in _DRAFT_DROPPED_ACTIONS:
            continue
        if action == "TARGET_SELECTION":
            actor, target = line["actor_id"], line.get("target_id")
            if actor in last_targets and last_targets[actor] == target:
                continue
            last_targets[actor] = target
        if drop_messages and action in _DRAFT_MESSAGE_DROPPED_ACTIONS:
            line.pop("message", None)
        lines.append({k: _round_floats(v) for k, v in line.items() if v is not None})
    return lines


def draft_format(logs: list[BattleLog]) -> list[dict[str, Any]]:
    """目標値を決めるための試算の形式.

    `AI_DECISION` を除く。`TARGET_SELECTION` は機体ごとに相手が変わった行だけ残す。
    null の項目を省き、小数を1桁に丸める。
    """
    return _draft_format(logs, drop_messages=False)


def draft_no_message_format(logs: list[BattleLog]) -> list[dict[str, Any]]:
    """`draft_format()` から、MOVE・WAIT・TARGET_SELECTION の message も省く."""
    return _draft_format(logs, drop_messages=True)


# 配信用の形式（replay）を足すと、同じ戦闘で並べて測れる。
LOG_FORMATS: dict[str, LogConverter] = {
    "stored": stored_format,
    "draft": draft_format,
    "draft_no_message": draft_no_message_format,
}


# --- 計測 ---


class ActionStats(BaseModel):
    """action_type ごとの行数と展開後のサイズ."""

    lines: int
    bytes: int


class FieldStats(BaseModel):
    """項目ごとの展開後のサイズ.

    1つの項目は `"key": value, ` の分。区切りの `, ` も含める。
    """

    lines: int = Field(description="この項目を持つ行の数")
    bytes: int
    null_bytes: int = Field(description="値が null の分")


class ParseStats(BaseModel):
    """Node でのパース時間と、パースしたログが保持するヒープ."""

    node_version: str
    parse_ms: list[float] = Field(description="各回のパース時間（ミリ秒）")
    parse_ms_median: float
    heap_bytes: int


class FormatMetrics(BaseModel):
    """1つの形式の計測結果."""

    lines: int
    raw_bytes: int = Field(description="NDJSON の展開後のサイズ")
    gzip_bytes: int = Field(description="GZipMiddleware と同じ圧縮をした後のサイズ")
    overhead_bytes: int = Field(description="項目以外の分（括弧・改行）")
    actions: dict[str, ActionStats]
    fields: dict[str, FieldStats]
    parse: ParseStats | None = Field(
        default=None, description="Node が無いか --no-parse のとき null"
    )


class MachineInfo(BaseModel):
    """計測した環境。パース時間とヒープはこれに左右される."""

    system: str
    machine: str
    python: str


class LogBenchResult(BaseModel):
    """1回の計測結果（`log_bench/<ID>.json`）."""

    schema_version: int = LOG_BENCH_SCHEMA_VERSION
    bench_id: str
    label: str
    created_at: datetime
    roster_name: str
    roster_units: int = Field(description="複製する前のロスターの機体数")
    units: int
    seed: int
    max_steps: int
    elapsed_time: float
    steps_used: int
    timed_out: bool
    git: GitInfo
    fuzzy_rules_hash: str
    machine: MachineInfo
    formats: dict[str, FormatMetrics]


def _json_bytes(value: Any) -> int:
    # logs_to_ndjson_text() と同じく ensure_ascii=False で書く。
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def gzip_size(data: bytes, chunk_size: int = STREAM_CHUNK_SIZE) -> int:
    """GZipMiddleware がストリーミングで返すときの圧縮後のサイズ.

    GZipMiddleware はチャンクごとに `Z_SYNC_FLUSH` する（Starlette 0.50 はしない）。
    一度に圧縮した値とは少し違う。
    """
    compressor = zlib.compressobj(GZIP_LEVEL, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
    size = 0
    for offset in range(0, len(data), chunk_size):
        size += len(compressor.compress(data[offset : offset + chunk_size]))
        size += len(compressor.flush(zlib.Z_SYNC_FLUSH))
    return size + len(compressor.flush())


def measure_lines(lines: list[dict[str, Any]]) -> FormatMetrics:
    """行の一覧を NDJSON にしてサイズを測る。パースは測らない."""
    data = logs_to_ndjson_text(lines).encode("utf-8")
    actions: dict[str, list[int]] = {}
    fields: dict[str, list[int]] = {}
    for line in lines:
        line_bytes = _json_bytes(line) + 1
        action = actions.setdefault(str(line.get("action_type")), [0, 0])
        action[0] += 1
        action[1] += line_bytes
        for key, value in line.items():
            # `"key": value` に区切りの `, ` を足した分。
            size = _json_bytes(key) + 2 + _json_bytes(value) + 2
            field = fields.setdefault(key, [0, 0, 0])
            field[0] += 1
            field[1] += size
            if value is None:
                field[2] += size
    field_total = sum(f[1] for f in fields.values())
    return FormatMetrics(
        lines=len(lines),
        raw_bytes=len(data),
        gzip_bytes=gzip_size(data),
        overhead_bytes=len(data) - field_total,
        actions={
            name: ActionStats(lines=v[0], bytes=v[1])
            for name, v in sorted(actions.items(), key=lambda kv: (-kv[1][1], kv[0]))
        },
        fields={
            name: FieldStats(lines=v[0], bytes=v[1], null_bytes=v[2])
            for name, v in sorted(fields.items(), key=lambda kv: (-kv[1][1], kv[0]))
        },
    )


class ParseBenchError(RuntimeError):
    """Node でのパースの計測に失敗したことを表す."""


def node_path() -> str | None:
    """Node の実行ファイル。無ければ None."""
    return shutil.which("node")


def measure_parse(ndjson: Path, lines: int, runs: int, node: str) -> ParseStats:
    """NDJSON ファイルを Node でパースし、時間とヒープを測る.

    Raises:
        ParseBenchError: Node が失敗したか、パースした行数が lines と違う場合
    """
    proc = subprocess.run(
        [node, "--expose-gc", str(PARSE_BENCH_SCRIPT), str(ndjson), str(runs)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ParseBenchError(f"parse_bench.mjs が失敗しました: {proc.stderr.strip()}")
    output = json.loads(proc.stdout)
    if output["lines"] != lines:
        raise ParseBenchError(
            f"Node がパースした行数（{output['lines']}）がログの行数（{lines}）と違います。"
        )
    return ParseStats(
        node_version=output["node_version"],
        parse_ms=[round(ms, 1) for ms in output["parse_ms"]],
        parse_ms_median=round(output["parse_ms_median"], 1),
        heap_bytes=output["heap_bytes"],
    )


@dataclass
class LogBenchOptions:
    """`log-bench` の実行条件."""

    units: int = PRODUCTION_ROOM_SIZE
    seed: int = DEFAULT_SEED
    max_steps: int = DEFAULT_MAX_STEPS
    # None ならロスター名。
    label: str | None = None
    formats: list[str] | None = None
    parse_runs: int = DEFAULT_PARSE_RUNS
    parse: bool = True
    # 指定すると、形式ごとの NDJSON をこのディレクトリに残す。
    ndjson_dir: Path | None = None


def _machine_info() -> MachineInfo:
    return MachineInfo(
        system=platform.system(),
        machine=platform.machine(),
        python=platform.python_version(),
    )


def _bench_id(label: str, created_at: datetime, bench_dir: Path) -> str:
    base = f"{created_at.strftime(GENERATION_TIME_FORMAT)}_{label}"
    candidate, suffix = base, 2
    while (bench_dir / f"{candidate}.json").exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def run_log_bench(
    roster: Roster,
    options: LogBenchOptions,
    bench_dir: Path = LOG_BENCH_DIR,
    now: datetime | None = None,
    progress: Callable[[str], None] = print,
) -> tuple[Path, LogBenchResult]:
    """ロスターで1戦を回し、ログを形式ごとに測って保存する.

    Raises:
        ValueError: 機体数・最大ステップ数・ラベル・形式の名前が不正な場合
        ParseBenchError: Node でのパースの計測に失敗した場合
    """
    if options.max_steps < 1:
        raise ValueError("--steps は 1 以上で指定してください。")
    if options.parse_runs < 1:
        raise ValueError("--runs は 1 以上で指定してください。")
    formats = options.formats or list(LOG_FORMATS)
    unknown = [name for name in formats if name not in LOG_FORMATS]
    if unknown:
        raise ValueError(
            f"形式 {', '.join(unknown)} はありません（{', '.join(LOG_FORMATS)}）。"
        )
    label = validate_label(options.label or roster.name)
    node = node_path() if options.parse else None
    if options.parse and node is None:
        progress("  node が見つからないため、パースの計測を省きます")

    bench_roster = individual_roster(roster, options.units)
    progress(
        f"  {options.units} 機（ロスター {len(roster.entries)} 機）・seed {options.seed} で戦闘を実行します"
    )
    battle = run_bench_battle(bench_roster, options.seed, options.max_steps)
    progress(
        f"  {battle.elapsed_time:.1f} 秒（{battle.steps_used} ステップ）・{len(battle.logs)} 行"
    )

    metrics: dict[str, FormatMetrics] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name in formats:
            lines = LOG_FORMATS[name](battle.logs)
            result = measure_lines(lines)
            ndjson = Path(tmp) / f"{name}.ndjson"
            ndjson.write_text(
                logs_to_ndjson_text(lines), encoding="utf-8", newline="\n"
            )
            if node is not None:
                result.parse = measure_parse(
                    ndjson, result.lines, options.parse_runs, node
                )
            if options.ndjson_dir is not None:
                options.ndjson_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ndjson, options.ndjson_dir / ndjson.name)
            metrics[name] = result
            progress(f"  [{name}] {result.lines} 行 / gzip {_mb(result.gzip_bytes)}")

    created_at = now or datetime.now().astimezone()
    bench_id = _bench_id(label, created_at, bench_dir)
    result = LogBenchResult(
        bench_id=bench_id,
        label=label,
        created_at=created_at,
        roster_name=roster.name,
        roster_units=len(roster.entries),
        units=options.units,
        seed=options.seed,
        max_steps=options.max_steps,
        elapsed_time=battle.elapsed_time,
        steps_used=battle.steps_used,
        timed_out=battle.timed_out,
        git=git_info(),
        fuzzy_rules_hash=directory_hash(FUZZY_RULES_DIR),
        machine=_machine_info(),
        formats=metrics,
    )
    bench_dir.mkdir(parents=True, exist_ok=True)
    path = bench_dir / f"{bench_id}.json"
    path.write_text(
        result.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return path, result


def find_log_bench(name: str, bench_dir: Path = LOG_BENCH_DIR) -> LogBenchResult:
    """計測結果をファイルのパス・ID・その前方一致・ラベルで探す.

    Raises:
        FileNotFoundError: 該当する結果が無い場合
        ValueError: 複数の結果に該当する場合
    """
    path = Path(name)
    if path.suffix == ".json" and path.is_file():
        return _read_result(path)
    candidates = sorted(bench_dir.glob("*.json")) if bench_dir.is_dir() else []
    exact = [p for p in candidates if p.stem == name]
    if exact:
        return _read_result(exact[0])
    results = [_read_result(p) for p in candidates]
    matches = [r for r in results if r.bench_id.startswith(name) or r.label == name]
    if not matches:
        raise FileNotFoundError(f"計測結果 '{name}' が見つかりません（{bench_dir}）。")
    if len(matches) > 1:
        ids = ", ".join(r.bench_id for r in matches)
        raise ValueError(f"'{name}' は複数の計測結果に該当します: {ids}")
    return matches[0]


def _read_result(path: Path) -> LogBenchResult:
    return LogBenchResult.model_validate_json(path.read_text(encoding="utf-8"))


# --- テキスト表示 ---


def _mb(size: int) -> str:
    if size < 1_000_000:
        return f"{size / 1_000:.1f} KB"
    return f"{size / 1_000_000:.2f} MB"


def _lines(count: int) -> str:
    return f"{count:,}"


def slow_4g_seconds(gzip_bytes: int) -> float:
    """Slow 4G で、gzip 後のサイズを転送する秒数."""
    return gzip_bytes * 8 / SLOW_4G_BITS_PER_SEC


def _summary_cells(metrics: FormatMetrics) -> dict[str, str]:
    parse = metrics.parse
    return {
        "行数": _lines(metrics.lines),
        "展開後": _mb(metrics.raw_bytes),
        "gzip": _mb(metrics.gzip_bytes),
        "Slow 4G の転送": f"{slow_4g_seconds(metrics.gzip_bytes):.1f} s",
        "パース（中央値）": f"{parse.parse_ms_median:.0f} ms" if parse else "-",
        f"パース × CPU {MOBILE_CPU_SLOWDOWN}倍": (
            f"{parse.parse_ms_median * MOBILE_CPU_SLOWDOWN:.0f} ms" if parse else "-"
        ),
        "ヒープ（保持分）": _mb(parse.heap_bytes) if parse else "-",
    }


def _header(result: LogBenchResult) -> list[str]:
    git = result.git
    commit = (git.commit or "-")[:7] + (" (dirty)" if git.dirty else "")
    node = next((m.parse.node_version for m in result.formats.values() if m.parse), "-")
    return [
        f"  ロスター: {result.roster_name}（{result.roster_units} 機 → {result.units} 機・個人戦）"
        f" / seed {result.seed}",
        f"  戦闘: {result.elapsed_time:.1f} 秒（{result.steps_used} ステップ"
        + ("・打ち切り" if result.timed_out else "")
        + "）",
        f"  コミット: {commit} / 環境: {result.machine.system} {result.machine.machine}"
        f" / Node {node}",
    ]


def _union(groups: Iterable[Iterable[str]]) -> list[str]:
    keys: list[str] = []
    for group in groups:
        keys.extend(k for k in group if k not in keys)
    return keys


def format_log_bench(result: LogBenchResult) -> str:
    """計測結果を表にする."""
    names = list(result.formats)
    out = [f"=== ログの計測: {result.bench_id} ===", *_header(result), ""]

    cells = {name: _summary_cells(m) for name, m in result.formats.items()}
    rows = [["", *names]]
    rows += [[key, *(cells[n][key] for n in names)] for key in cells[names[0]]]
    out += _table(rows)

    out += ["", "action_type ごとの行数:"]
    actions = _union(m.actions for m in result.formats.values())
    rows = [["", *names]]
    for action in actions:
        row = [action]
        for name in names:
            stats = result.formats[name].actions.get(action)
            row.append(_lines(stats.lines) if stats else "-")
        rows.append(row)
    out += _table(rows)

    for name, metrics in result.formats.items():
        out += ["", f"項目ごとのサイズ（{name}）:"]
        rows = [["項目", "サイズ", "割合", "うち null"]]
        for key, stats in metrics.fields.items():
            rows.append(
                [
                    key,
                    _mb(stats.bytes),
                    f"{stats.bytes / metrics.raw_bytes:.1%}",
                    _mb(stats.null_bytes) if stats.null_bytes else "-",
                ]
            )
        rows.append(
            [
                "(括弧・改行)",
                _mb(metrics.overhead_bytes),
                f"{metrics.overhead_bytes / metrics.raw_bytes:.1%}",
                "-",
            ]
        )
        out += _table(rows)
    return "\n".join(out) + "\n"


def _ratio(a: float, b: float) -> str:
    return f"{b / a:.2f}x" if a else "-"


def format_log_comparison(a: LogBenchResult, b: LogBenchResult) -> str:
    """2つの計測結果を形式ごとに並べ、B / A を出す."""
    out = [
        "=== ログの計測の比較 ===",
        f"  A: {a.bench_id}",
        *_header(a),
        f"  B: {b.bench_id}",
        *_header(b),
    ]
    if (a.roster_name, a.units, a.seed, a.max_steps) != (
        b.roster_name,
        b.units,
        b.seed,
        b.max_steps,
    ):
        out.append("  ⚠️  ロスター・機体数・seed・最大ステップ数が違います")
    if a.machine != b.machine:
        out.append("  ⚠️  計測した環境が違います。パース時間とヒープは比べられません")

    for name in _union([a.formats, b.formats]):
        ma, mb = a.formats.get(name), b.formats.get(name)
        out += ["", f"[{name}]"]
        if ma is None or mb is None:
            out.append(f"  {'A' if ma is None else 'B'} にはありません")
            continue
        ca, cb = _summary_cells(ma), _summary_cells(mb)
        values = {
            "行数": (ma.lines, mb.lines),
            "展開後": (ma.raw_bytes, mb.raw_bytes),
            "gzip": (ma.gzip_bytes, mb.gzip_bytes),
        }
        if ma.parse and mb.parse:
            values["パース（中央値）"] = (
                ma.parse.parse_ms_median,
                mb.parse.parse_ms_median,
            )
            values["ヒープ（保持分）"] = (ma.parse.heap_bytes, mb.parse.heap_bytes)
        rows = [["", "A", "B", "B / A"]]
        for key in ca:
            pair = values.get(key)
            rows.append([key, ca[key], cb[key], _ratio(*pair) if pair else ""])
        out += _table(rows)

        rows = [["action_type", "A", "B", "B / A"]]
        for action in _union([ma.actions, mb.actions]):
            la = ma.actions[action].lines if action in ma.actions else 0
            lb = mb.actions[action].lines if action in mb.actions else 0
            rows.append([action, _lines(la), _lines(lb), _ratio(la, lb)])
        out += [""] + _table(rows)
    return "\n".join(out) + "\n"

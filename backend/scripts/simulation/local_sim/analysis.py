"""世代の集計（report）と、2つの世代の比較（compare）.

行動分布・戦略遷移・武器の使用回数は `sim_report.ReportGenerator`、
警告は `sim_bench.balance_warnings()` で、ミッション戦の report / bench と同じ基準で出す。
集計値は世代ディレクトリの `report.json` に保存し、`/dev/sim` の比較画面が読む。
"""

import json
import unicodedata
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from scripts.simulation.local_sim.generations import (
    BattleRecord,
    Manifest,
)
from scripts.simulation.sim_bench import balance_warnings
from scripts.simulation.sim_report import Report, ReportGenerator

REPORT_FILE = "report.json"
# 集計の項目や計算を変えたら上げる。古い report.json は読み直さずに作り直す。
REPORT_SCHEMA_VERSION = 1
# 警告文で、判定する機体が負けた戦闘の勝者をまとめて呼ぶ名前。
_OPPONENTS_LABEL = "相手側"
_COMMIT_DIGITS = 7
_HASH_DIGITS = 8


class DurationStats(BaseModel):
    """戦闘の経過時間（秒）."""

    avg: float
    min: float
    max: float


class UnitStats(BaseModel):
    """1機の撃墜数と被撃墜数（世代の全戦闘の合計）."""

    unit_id: str
    name: str
    pilot_name: str | None = None
    is_player: bool = Field(description="勝敗と撃墜数を判定する機体か")
    battles: int
    kills: int
    deaths: int


class GenerationReport(BaseModel):
    """世代の集計値（`report.json`）."""

    schema_version: int = REPORT_SCHEMA_VERSION
    generation_id: str
    battles: int
    wins: int
    losses: int
    timeouts: int = Field(description="最大ステップ数で打ち切った戦闘の数")
    elapsed_time: DurationStats
    player_kills: int = Field(description="判定する機体の撃墜数の合計")
    action_counts: dict[str, int]
    strategy_transitions: dict[str, int] = Field(
        description="`前 → 後` ごとの STRATEGY_CHANGED の回数"
    )
    weapon_usage: dict[str, int] = Field(description="武器名ごとの ATTACK の回数")
    units: list[UnitStats] = Field(description="ロスターの順。判定する機体が先頭")
    warnings: list[str]

    @property
    def win_rate(self) -> float:
        """判定する機体の勝率."""
        return self.wins / self.battles if self.battles else 0.0

    @property
    def timeout_rate(self) -> float:
        """打ち切った戦闘の割合."""
        return self.timeouts / self.battles if self.battles else 0.0

    @property
    def action_total(self) -> int:
        """集計した行動の総数."""
        return sum(self.action_counts.values())

    def action_ratio(self, action_type: str) -> float:
        """行動の総数に占める割合を返す."""
        total = self.action_total
        return self.action_counts.get(action_type, 0) / total if total else 0.0


def attribute_kills(logs: list[dict[str, Any]]) -> list[tuple[str | None, str]]:
    """撃墜を (撃墜した機体, 撃墜された機体) の ID の組で返す.

    判定は `battle_digest.compute_unit_kills()` と同じ。直前のログが同じ対象への
    ATTACK / MELEE_COMBO でない撃墜は、撃墜した機体を None にする。
    """
    kills: list[tuple[str | None, str]] = []
    for i, log in enumerate(logs):
        if log.get("action_type") != "DESTROYED":
            continue
        victim = str(log["actor_id"])
        prev = logs[i - 1] if i > 0 else None
        killer = (
            str(prev["actor_id"])
            if prev
            and prev.get("action_type") in ("ATTACK", "MELEE_COMBO")
            and str(prev.get("target_id")) == victim
            else None
        )
        kills.append((killer, victim))
    return kills


class GenerationAnalyzer:
    """1戦ずつ結果を受け取り、世代の集計値を作る.

    1戦のログは数 MB あるため、戦闘を全部持たずに積算する。
    """

    def __init__(self) -> None:
        """空の集計を作る."""
        self._generator = ReportGenerator()
        self._log_report = Report(file_count=0, total_rounds=0)
        self._durations: list[float] = []
        self._wins = 0
        self._timeouts = 0
        self._player_kills = 0
        self._units: dict[str, UnitStats] = {}

    def add(self, record: BattleRecord) -> None:
        """1戦分を積算する."""
        self._generator.add_result(
            {"win_loss": record.win_loss, "logs": record.logs}, self._log_report
        )
        self._durations.append(record.elapsed_time)
        self._wins += record.win_loss == "WIN"
        self._timeouts += record.timed_out
        self._player_kills += record.kills

        player_id = str(record.player_info.get("id"))
        for info in [record.player_info, *record.enemies_info]:
            unit_id = str(info.get("id"))
            stats = self._units.get(unit_id)
            if stats is None:
                stats = self._units[unit_id] = UnitStats(
                    unit_id=unit_id,
                    name=str(info.get("name") or unit_id),
                    pilot_name=info.get("pilot_name"),
                    is_player=unit_id == player_id,
                    battles=0,
                    kills=0,
                    deaths=0,
                )
            stats.battles += 1
        for killer, victim in attribute_kills(record.logs):
            if killer in self._units:
                self._units[killer].kills += 1
            if victim in self._units:
                self._units[victim].deaths += 1

    def result(self, generation_id: str) -> GenerationReport:
        """積算した値から集計値を作る."""
        battles = len(self._durations)
        losses = battles - self._wins
        avg = sum(self._durations) / battles if battles else 0.0
        return GenerationReport(
            generation_id=generation_id,
            battles=battles,
            wins=self._wins,
            losses=losses,
            timeouts=self._timeouts,
            elapsed_time=DurationStats(
                avg=avg,
                min=min(self._durations, default=0.0),
                max=max(self._durations, default=0.0),
            ),
            player_kills=self._player_kills,
            action_counts=dict(sorted(self._log_report.action_distribution.items())),
            strategy_transitions=dict(
                sorted(self._log_report.strategy_transitions.items())
            ),
            weapon_usage=dict(
                sorted(self._log_report.weapon_usage.items(), key=lambda x: -x[1])
            ),
            units=list(self._units.values()),
            # 打ち切りを bench の引き分け（最大ステップ到達）と同じ扱いにする。
            warnings=balance_warnings(
                rounds=battles,
                draw_count=self._timeouts,
                win_counts={"判定する機体": self._wins, _OPPONENTS_LABEL: losses},
                avg_duration=avg,
                draw_label="打ち切り",
            ),
        )


def build_report(generation_dir: Path, manifest: Manifest) -> GenerationReport:
    """世代の `battle_NNN.json` を全部読んで集計値を作る."""
    analyzer = GenerationAnalyzer()
    for battle in manifest.battles:
        analyzer.add(
            BattleRecord.model_validate_json(
                (generation_dir / battle.file).read_text(encoding="utf-8")
            )
        )
    return analyzer.result(manifest.generation_id)


def write_report(generation_dir: Path, report: GenerationReport) -> Path:
    """集計値を `report.json` に保存する."""
    path = generation_dir / REPORT_FILE
    path.write_text(
        report.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return path


def load_report(generation_dir: Path, manifest: Manifest) -> GenerationReport:
    """`report.json` を読む。無いか古い形式なら、集計し直して保存する."""
    path = generation_dir / REPORT_FILE
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") == REPORT_SCHEMA_VERSION:
            return GenerationReport.model_validate(data)
    report = build_report(generation_dir, manifest)
    write_report(generation_dir, report)
    return report


# --- テキスト表示 ---


def _width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _ljust(text: str, width: int) -> str:
    return text + " " * max(width - _width(text), 0)


def _rjust(text: str, width: int) -> str:
    return " " * max(width - _width(text), 0) + text


def _table(rows: list[list[str]], left_columns: int = 1) -> list[str]:
    """先頭の left_columns 列を左寄せ、残りを右寄せにして列をそろえる."""
    widths = [max(_width(row[i]) for row in rows) for i in range(len(rows[0]))]
    return [
        "  "
        + "  ".join(
            _ljust(cell, widths[i]) if i < left_columns else _rjust(cell, widths[i])
            for i, cell in enumerate(row)
        ).rstrip()
        for row in rows
    ]


def _pct(value: float) -> str:
    return f"{value:.1%}"


def _per_battle(count: int, battles: int) -> float:
    return count / battles if battles else 0.0


def unit_label(unit: UnitStats) -> str:
    """機体名とパイロット名。判定する機体には `*` を付ける."""
    pilot = f" ({unit.pilot_name})" if unit.pilot_name else ""
    return f"{'*' if unit.is_player else ' '}{unit.name}{pilot}"


def _conditions(manifest: Manifest) -> dict[str, str]:
    commit = manifest.git.commit[:_COMMIT_DIGITS] if manifest.git.commit else "-"
    return {
        "ロスター": manifest.roster_name,
        "判定する機体": manifest.player_name or "-",
        "seed": str(manifest.seed),
        "最大ステップ数": str(manifest.max_steps),
        "コミット": commit + (" (dirty)" if manifest.git.dirty else ""),
        "ファジィルール": manifest.fuzzy_rules_hash[:_HASH_DIGITS],
        "戦域": f"{manifest.theater_id or 'なし'} / {manifest.environment}"
        f" / ミノフスキー {manifest.minovsky_density}",
    }


def format_report(manifest: Manifest, report: GenerationReport) -> str:
    """1世代の集計値をテキストにする."""
    n = report.battles
    lines = [
        f"=== 世代レポート: {manifest.generation_id} ({n} 戦) ===",
        "",
        *_table([[k, v] for k, v in _conditions(manifest).items()], left_columns=2),
        "",
        "勝敗:",
        *_table(
            [
                ["勝ち", f"{report.wins} 回", _pct(report.win_rate)],
                ["負け", f"{report.losses} 回", _pct(_per_battle(report.losses, n))],
                ["打ち切り", f"{report.timeouts} 回", _pct(report.timeout_rate)],
            ]
        ),
        "",
        f"平均戦闘時間: {report.elapsed_time.avg:.1f}s"
        f" (最短 {report.elapsed_time.min:.1f}s / 最長 {report.elapsed_time.max:.1f}s)",
        f"判定する機体の撃墜数: {_per_battle(report.player_kills, n):.2f} / 戦",
        "",
    ]
    if report.action_counts:
        lines += [
            "行動分布（全ユニット合計）:",
            *_table(
                [
                    [a, f"{c} 回", _pct(report.action_ratio(a))]
                    for a, c in report.action_counts.items()
                ]
            ),
            "",
        ]
    if report.strategy_transitions:
        lines += [
            "戦略遷移（STRATEGY_CHANGED）:",
            *_table(
                [
                    [t, f"{c} 回", f"{_per_battle(c, n):.2f} / 戦"]
                    for t, c in report.strategy_transitions.items()
                ]
            ),
            "",
        ]
    if report.units:
        lines += [
            "機体ごとの撃墜数 / 被撃墜数（* は判定する機体）:",
            *_table(
                [["機体", "撃墜", "撃墜/戦", "被撃墜", "被撃墜率"]]
                + [
                    [
                        unit_label(u),
                        str(u.kills),
                        f"{_per_battle(u.kills, u.battles):.2f}",
                        str(u.deaths),
                        _pct(_per_battle(u.deaths, u.battles)),
                    ]
                    for u in report.units
                ]
            ),
            "",
        ]
    lines += [f"⚠️  {w}" for w in report.warnings]
    return "\n".join(lines).rstrip() + "\n"


def _diff_row(
    name: str,
    a: float,
    b: float,
    fmt: Callable[[float], str],
    diff_fmt: Callable[[float], str],
) -> list[str]:
    return [name, fmt(a), fmt(b), diff_fmt(b - a)]


def _signed_pt(value: float) -> str:
    return f"{value * 100:+.1f}pt"


def _union(keys: Iterable[str], other: Iterable[str]) -> list[str]:
    return sorted(set(keys) | set(other))


def _unit_diff_cells(
    ua: UnitStats | None,
    ub: UnitStats | None,
    value: Callable[[UnitStats], float],
    fmt: Callable[[float], str],
    diff_fmt: Callable[[float], str],
) -> list[str]:
    """A・B の値と差の3列。片方の世代にいない機体は値を `-`、差を空にする."""
    va = value(ua) if ua else None
    vb = value(ub) if ub else None
    return [
        fmt(va) if va is not None else "-",
        fmt(vb) if vb is not None else "-",
        diff_fmt(vb - va) if va is not None and vb is not None else "",
    ]


def format_comparison(
    a: tuple[Manifest, GenerationReport], b: tuple[Manifest, GenerationReport]
) -> str:
    """2つの世代の集計値を並べ、差（B − A）を付けてテキストにする.

    戦闘数が違っても比べられるよう、回数は1戦あたりか割合で並べる。
    """
    (ma, ra), (mb, rb) = a, b
    cond_a, cond_b = _conditions(ma), _conditions(mb)
    lines = [
        "=== 世代比較 ===",
        f"  A: {ma.generation_id} ({ra.battles} 戦)",
        f"  B: {mb.generation_id} ({rb.battles} 戦)",
        "",
        "条件（≠ は A と B で違う項目）:",
        *_table(
            [["", "A", "B", ""]]
            + [
                [k, cond_a[k], cond_b[k], "" if cond_a[k] == cond_b[k] else "≠"]
                for k in cond_a
            ],
            left_columns=4,
        ),
        "",
    ]

    rows = [
        ["", "A", "B", "差 (B-A)"],
        _diff_row("勝率", ra.win_rate, rb.win_rate, _pct, _signed_pt),
        _diff_row("打ち切り率", ra.timeout_rate, rb.timeout_rate, _pct, _signed_pt),
        _diff_row(
            "平均戦闘時間",
            ra.elapsed_time.avg,
            rb.elapsed_time.avg,
            lambda v: f"{v:.1f}s",
            lambda v: f"{v:+.1f}s",
        ),
        _diff_row(
            "撃墜数/戦",
            _per_battle(ra.player_kills, ra.battles),
            _per_battle(rb.player_kills, rb.battles),
            lambda v: f"{v:.2f}",
            lambda v: f"{v:+.2f}",
        ),
    ]
    rows += [
        _diff_row(
            f"行動: {action}",
            ra.action_ratio(action),
            rb.action_ratio(action),
            _pct,
            _signed_pt,
        )
        for action in _union(ra.action_counts, rb.action_counts)
    ]
    rows += [
        _diff_row(
            f"遷移: {t}",
            _per_battle(ra.strategy_transitions.get(t, 0), ra.battles),
            _per_battle(rb.strategy_transitions.get(t, 0), rb.battles),
            lambda v: f"{v:.2f}/戦",
            lambda v: f"{v:+.2f}",
        )
        for t in _union(ra.strategy_transitions, rb.strategy_transitions)
    ]
    lines += ["集計値:", *_table(rows), ""]

    units_a = {u.unit_id: u for u in ra.units}
    units_b = {u.unit_id: u for u in rb.units}
    unit_rows = [["機体", "撃墜/戦 A", "B", "差", "被撃墜率 A", "B", "差"]]
    for unit_id in [*units_a, *(u for u in units_b if u not in units_a)]:
        ua, ub = units_a.get(unit_id), units_b.get(unit_id)
        unit = ua or ub
        assert unit is not None
        unit_rows.append(
            [
                unit_label(unit),
                *_unit_diff_cells(
                    ua,
                    ub,
                    lambda u: _per_battle(u.kills, u.battles),
                    lambda v: f"{v:.2f}",
                    lambda v: f"{v:+.2f}",
                ),
                *_unit_diff_cells(
                    ua,
                    ub,
                    lambda u: _per_battle(u.deaths, u.battles),
                    _pct,
                    _signed_pt,
                ),
            ]
        )
    lines += [
        "機体ごとの撃墜数 / 被撃墜率（* は判定する機体。片方にしかいない機体は -）:",
        *_table(unit_rows),
        "",
    ]

    for name, report in (("A", ra), ("B", rb)):
        lines += [f"⚠️  [{name}] {w}" for w in report.warnings]
    return "\n".join(lines).rstrip() + "\n"

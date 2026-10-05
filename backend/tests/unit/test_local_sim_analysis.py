"""ローカルシミュレータの report / compare（世代の集計と比較）のテスト."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.simulation.local_sim.analysis import (
    REPORT_FILE,
    REPORT_SCHEMA_VERSION,
    GenerationAnalyzer,
    GenerationReport,
    attribute_kills,
    build_report,
    format_comparison,
    format_report,
    load_report,
)
from scripts.simulation.local_sim.generations import (
    BattleRecord,
    GenerationSummary,
    GitInfo,
    Manifest,
    read_manifest,
)
from scripts.simulation.sim_bench import balance_warnings
from tests.unit.test_local_sim_run import (  # noqa: F401
    _run,
    generations_dir_fixture,
    roster_path_fixture,
)

_PLAYER = {"id": "p", "name": "Gundam", "pilot_name": "Amuro"}
_ENEMY = {"id": "e", "name": "Zaku II", "pilot_name": None}


def _log(action_type: str, actor: str, target: str | None = None, **kwargs) -> dict:
    return {"action_type": action_type, "actor_id": actor, "target_id": target} | kwargs


def _record(
    index: int,
    win_loss: str,
    logs: list[dict[str, Any]],
    elapsed_time: float = 60.0,
    timed_out: bool = False,
    enemies: list[dict[str, Any]] | None = None,
) -> BattleRecord:
    return BattleRecord(
        index=index,
        seed=index,
        win_loss=win_loss,  # type: ignore[arg-type]
        kills=sum(1 for killer, _ in attribute_kills(logs) if killer == "p"),
        elapsed_time=elapsed_time,
        steps_used=int(elapsed_time * 10),
        timed_out=timed_out,
        environment="SPACE",
        minovsky_density=0.0,
        player_info=_PLAYER,
        enemies_info=enemies if enemies is not None else [_ENEMY],
        obstacles_info=[],
        map_bounds=[0.0, 1000.0],
        logs=logs,
    )


def _report(*records: BattleRecord) -> GenerationReport:
    analyzer = GenerationAnalyzer()
    for record in records:
        analyzer.add(record)
    return analyzer.result("gen")


# --- 撃墜の判定 ---


def test_attribute_kills_uses_attack_just_before_destroyed() -> None:
    """撃墜した機体は、DESTROYED の直前にある同じ対象への攻撃の機体にすること."""
    logs = [
        _log("ATTACK", "p", "e"),
        _log("DESTROYED", "e"),
        _log("MELEE_COMBO", "e", "p"),
        _log("DESTROYED", "p"),
        # 直前の攻撃が別の対象なら、撃墜した機体は分からない。
        _log("ATTACK", "p", "x"),
        _log("DESTROYED", "y"),
    ]

    assert attribute_kills(logs) == [("p", "e"), ("e", "p"), (None, "y")]


# --- 集計 ---


def test_analyzer_aggregates_battles() -> None:
    """勝敗・打ち切り・戦闘時間・行動分布・機体ごとの撃墜数を集計すること."""
    report = _report(
        _record(
            1,
            "WIN",
            [
                _log("MOVE", "p"),
                _log("ATTACK", "p", "e", weapon_name="Beam Rifle"),
                _log("DESTROYED", "e"),
            ],
            elapsed_time=30.0,
        ),
        _record(
            2,
            "LOSE",
            [
                _log(
                    "STRATEGY_CHANGED",
                    "p",
                    details={
                        "previous_strategy": "AGGRESSIVE",
                        "new_strategy": "DEFENSIVE",
                    },
                ),
                _log("ATTACK", "e", "p", weapon_name="Zaku Machine Gun"),
                _log("DESTROYED", "p"),
            ],
            elapsed_time=90.0,
            timed_out=True,
        ),
    )

    assert (report.battles, report.wins, report.losses) == (2, 1, 1)
    assert report.timeouts == 1
    assert report.win_rate == 0.5
    assert report.timeout_rate == 0.5
    assert report.elapsed_time.model_dump() == {"avg": 60.0, "min": 30.0, "max": 90.0}
    assert report.player_kills == 1
    assert report.action_counts == {"ATTACK": 2, "DESTROYED": 2, "MOVE": 1}
    assert report.action_ratio("ATTACK") == 0.4
    assert report.strategy_transitions == {"AGGRESSIVE → DEFENSIVE": 1}
    assert report.weapon_usage == {"Beam Rifle": 1, "Zaku Machine Gun": 1}
    assert [
        (u.unit_id, u.is_player, u.battles, u.kills, u.deaths) for u in report.units
    ] == [("p", True, 2, 1, 1), ("e", False, 2, 1, 1)]
    assert report.units[0].pilot_name == "Amuro"


def test_warnings_follow_bench_thresholds() -> None:
    """打ち切り率と勝率の偏りを、bench と同じ閾値で警告すること."""
    report = _report(
        *(_record(i, "WIN", [], timed_out=i == 1) for i in range(1, 5)),
    )

    assert report.warnings == balance_warnings(
        rounds=4,
        draw_count=1,
        win_counts={"判定する機体": 4, "相手側": 0},
        avg_duration=60.0,
        draw_label="打ち切り",
    )
    assert any(w.startswith("打ち切り率が高すぎます") for w in report.warnings)
    assert any(w.startswith("判定する機体 の勝率が高すぎます") for w in report.warnings)


def test_balance_warnings_default_label_matches_bench() -> None:
    """draw_label を省略すると、bench と同じ「引き分け率」の警告になること."""
    warnings = balance_warnings(
        rounds=10, draw_count=3, win_counts={"PLAYER_TEAM": 7}, avg_duration=10.0
    )

    assert warnings == [
        "引き分け率が高すぎます (30.0% > 20%): 戦闘が長期化しすぎている可能性があります"
    ]


def test_empty_generation_has_no_warnings() -> None:
    """戦闘が無いときは 0 で埋め、警告しないこと."""
    report = _report()

    assert report.battles == 0
    assert report.win_rate == 0.0
    assert report.warnings == []


# --- report.json ---


def test_run_saves_report_matching_battle_files(
    roster_path: Path, generations_dir: Path
) -> None:
    """保存した report.json は、battle_NNN.json を読み直した集計と一致すること."""
    result = _run(roster_path, generations_dir, rounds=2, seed=611, label="a")

    saved = json.loads((result.path / REPORT_FILE).read_text(encoding="utf-8"))
    rebuilt = build_report(result.path, result.manifest)
    assert saved == rebuilt.model_dump(mode="json")
    assert rebuilt.generation_id == result.manifest.generation_id
    assert rebuilt.battles == 2
    assert rebuilt.units[0].is_player
    assert len(rebuilt.units) == 4


def test_load_report_rebuilds_missing_or_outdated_file(
    roster_path: Path, generations_dir: Path
) -> None:
    """report.json が無いか形式が古ければ、集計し直して保存すること."""
    result = _run(roster_path, generations_dir, seed=611, label="a")
    path = result.path / REPORT_FILE
    expected = path.read_text(encoding="utf-8")

    path.unlink()
    assert load_report(result.path, result.manifest).battles == 1
    assert path.read_text(encoding="utf-8") == expected

    path.write_text(
        json.dumps({"schema_version": REPORT_SCHEMA_VERSION - 1}), encoding="utf-8"
    )
    assert load_report(result.path, result.manifest).battles == 1
    assert path.read_text(encoding="utf-8") == expected


# --- テキスト表示 ---


def test_format_report_and_comparison(roster_path: Path, generations_dir: Path) -> None:
    """レポートは集計値と警告を、比較は条件の違いと差を表示すること."""
    a = _run(roster_path, generations_dir, rounds=2, seed=611, label="before")
    b = _run(roster_path, generations_dir, minutes=1, seed=700, label="after")
    report_a = load_report(a.path, a.manifest)
    report_b = load_report(b.path, b.manifest)

    text = format_report(a.manifest, report_a)
    assert "=== 世代レポート: 20261005-213000_before (2 戦) ===" in text
    assert "平均戦闘時間:" in text
    assert "*Zaku II" in text
    for warning in report_a.warnings:
        assert warning in text

    comparison = format_comparison(
        (read_manifest(a.path), report_a), (b.manifest, report_b)
    )
    assert "A: 20261005-213000_before (2 戦)" in comparison
    assert "B: 20261005-213100_after (1 戦)" in comparison
    seed_row = next(line for line in comparison.splitlines() if "seed" in line)
    assert seed_row.split()[1:] == ["611", "700", "≠"]
    assert "差 (B-A)" in comparison
    assert "勝率" in comparison


def test_comparison_marks_units_only_in_one_generation() -> None:
    """片方の世代にしかいない機体は、値を - にすること."""
    other = {"id": "o", "name": "Gelgoog", "pilot_name": None}
    report_a = _report(_record(1, "WIN", []))
    report_b = _report(_record(1, "WIN", [], enemies=[other]))
    manifest_stub = _manifest_stub()

    comparison = format_comparison((manifest_stub, report_a), (manifest_stub, report_b))

    zaku = next(line for line in comparison.splitlines() if "Zaku II" in line)
    gelgoog = next(line for line in comparison.splitlines() if "Gelgoog" in line)
    assert zaku.split()[2:] == ["0.00", "-", "0.0%", "-"]
    assert gelgoog.split()[1:] == ["-", "0.00", "-", "0.0%"]


def _manifest_stub() -> Manifest:
    return Manifest(
        generation_id="gen",
        label="gen",
        created_at=datetime(2026, 10, 5).astimezone(),
        roster_name="r",
        player_entry_index=0,
        seed=1,
        rounds=1,
        max_steps=10,
        git=GitInfo(),
        fuzzy_rules_hash="0" * 64,
        environment="SPACE",
        minovsky_density=0.0,
        summary=GenerationSummary(
            battles=1, wins=1, losses=0, timeouts=0, total_kills=0
        ),
        battles=[],
    )

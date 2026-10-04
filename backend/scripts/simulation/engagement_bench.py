#!/usr/bin/env python3
# backend/scripts/simulation/engagement_bench.py
"""交戦距離と膠着の指標を 1対1 のシミュレーションで計測する.

DB を使わず、`data/master/` の機体・武器の JSON から戦闘を組み立てる。
`run` で計測結果を表と JSON に出力し、`diff` で 2 つの結果 JSON を比べる。

Usage:
    python scripts/simulation/engagement_bench.py run --output results/before.json
    python scripts/simulation/engagement_bench.py run --scenarios melee_duel --rounds 4
    python scripts/simulation/engagement_bench.py diff results/before.json results/after.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import uuid
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# プロセスごとに numpy がスレッドを増やすと、並列実行でかえって遅くなる。
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from app.engine import combat  # noqa: E402
from app.engine.calculator import PilotStats  # noqa: E402
from app.engine.constants import MELEE_RANGE  # noqa: E402
from app.engine.simulation import BattleSimulator  # noqa: E402
from app.models.models import MobileSuit, Vector3, Weapon  # noqa: E402

_MASTER_DIR = Path(__file__).resolve().parents[2] / "data" / "master"
# 定期バトルの 3000 ではなく、エンジン上限まで回す。時間切れ自体を指標として見るため。
_DEFAULT_MAX_STEPS = 5000
_DT = 0.1
_CLOSE_RANGE = 150.0
_STRATEGIES: tuple[str, ...] = ("AGGRESSIVE", "DEFENSIVE", "SNIPER", "ASSAULT")
_SECTORS: tuple[str, ...] = ("FRONT", "FRONT_SIDE", "REAR_SIDE", "REAR")
# 両機の能力差がパイロットから生じないよう、PLAYER 側も NPC と同じ値にそろえる。
_PILOT_STATS = PilotStats(sht=1, mel=1, intel=1, ref=1, tou=1, luk=1)
_UNIT_A_ID = uuid.UUID(int=1)
_UNIT_B_ID = uuid.UUID(int=2)


@dataclass(frozen=True)
class Loadout:
    """機体マスターと装備する武器の組."""

    label: str
    master_id: str
    weapon_ids: tuple[str, ...]


@dataclass(frozen=True)
class Scenario:
    """計測シナリオ.

    `range_pairs` は A・B に設定する `tactics.range` の組の一覧。
    """

    key: str
    title: str
    a: Loadout
    b: Loadout
    start_distance: float
    range_pairs: tuple[tuple[str, str], ...]


_GUNDAM_MELEE = Loadout(
    "ガンダム[サーベル+ライフル]", "gundam", ("beam_saber", "beam_rifle")
)
_GOUF_MELEE = Loadout("グフ[ヒートロッド+MG]", "gouf", ("heat_rod", "zaku_mg"))
_GUNDAM_RANGED = Loadout("ガンダム[ライフル]", "gundam", ("beam_rifle",))
_ZAKU_RANGED = Loadout("ザクII[MG]", "zaku_ii", ("zaku_mg",))
_GELGOOG_RANGED = Loadout("ゲルググ[ライフル]", "gelgoog", ("beam_rifle_gelgoog",))

SCENARIOS: dict[str, Scenario] = {
    s.key: s
    for s in (
        Scenario(
            "melee_duel",
            "格闘機同士",
            _GUNDAM_MELEE,
            _GOUF_MELEE,
            300.0,
            (("BALANCED", "BALANCED"), ("MELEE", "MELEE")),
        ),
        Scenario(
            "ranged_gundam_zaku",
            "射撃機同士",
            _GUNDAM_RANGED,
            _ZAKU_RANGED,
            1000.0,
            (("BALANCED", "BALANCED"), ("RANGED", "RANGED")),
        ),
        Scenario(
            "ranged_gelgoog_gundam",
            "射撃機同士",
            _GELGOOG_RANGED,
            _GUNDAM_RANGED,
            1000.0,
            (("BALANCED", "BALANCED"), ("RANGED", "RANGED")),
        ),
        Scenario(
            "melee_vs_ranged",
            "格闘機 vs 射撃機",
            _GOUF_MELEE,
            _GUNDAM_RANGED,
            1000.0,
            (("BALANCED", "BALANCED"), ("MELEE", "RANGED")),
        ),
    )
}


@dataclass(frozen=True)
class Condition:
    """シナリオ内の 1 条件。両機に同じ戦略モードを設定する."""

    strategy: str
    range_a: str
    range_b: str

    @property
    def key(self) -> str:
        """結果 JSON と diff で条件を突き合わせるキー."""
        return f"{self.strategy}/{self.range_a}x{self.range_b}"


@dataclass
class AttackRecord:
    """攻撃 1 回分の記録。命中判定を行った攻撃だけを数える."""

    unit: str
    time: float
    distance: float
    optimal_range: float
    is_melee: bool
    sector: str
    is_hit: bool = False


@dataclass
class BattleMetrics:
    """1 戦分の計測値."""

    seed: int
    duration: float
    timed_out: bool
    winner: str  # "A" / "B" / ""（引き分け）
    engaged_distances: list[float]
    melee_ratios: list[float]
    ranged_ratios: list[float]
    sector_counts: dict[str, int]
    weapon_switches: int
    longest_melee_miss_sec: float
    longest_melee_miss_count: int


# ---------------------------------------------------------------------------
# 戦闘の組み立て
# ---------------------------------------------------------------------------


def _load_json(name: str) -> list[dict]:
    return json.loads((_MASTER_DIR / name).read_text(encoding="utf-8"))


def _build_weapon(weapon_id: str, suit_weapons: dict[str, dict]) -> Weapon:
    """機体マスターの武器を優先し、無ければ武器マスターから組み立てる."""
    if weapon_id in suit_weapons:
        return Weapon(**suit_weapons[weapon_id])
    master = {w["id"]: w for w in _load_json("weapons.json")}[weapon_id]
    return Weapon(id=weapon_id, name=master["name"], **master["weapon"])


def _build_unit(
    loadout: Loadout,
    unit_id: uuid.UUID,
    side: str,
    position: Vector3,
    strategy: str,
    tactics_range: str,
) -> MobileSuit:
    master = {m["id"]: m for m in _load_json("mobile_suits.json")}[loadout.master_id]
    specs = master["specs"]
    suit_weapons = {w["id"]: w for w in specs["weapons"]}
    return MobileSuit(
        id=unit_id,
        name=loadout.label,
        max_hp=specs["max_hp"],
        current_hp=specs["max_hp"],
        armor=specs["armor"],
        mobility=specs["mobility"],
        sensor_range=specs.get("sensor_range", 500.0),
        beam_resistance=specs.get("beam_resistance", 0.0),
        physical_resistance=specs.get("physical_resistance", 0.0),
        melee_aptitude=specs.get("melee_aptitude", 1.0),
        shooting_aptitude=specs.get("shooting_aptitude", 1.0),
        accuracy_bonus=specs.get("accuracy_bonus", 0.0),
        evasion_bonus=specs.get("evasion_bonus", 0.0),
        acceleration_bonus=specs.get("acceleration_bonus", 1.0),
        turning_bonus=specs.get("turning_bonus", 1.0),
        weapons=[_build_weapon(w, suit_weapons) for w in loadout.weapon_ids],
        terrain_adaptability=specs.get("terrain_adaptability", {}),
        position=position,
        side=side,
        team_id=f"{side}_TEAM",
        strategy_mode=strategy,
        tactics={"priority": "CLOSEST", "range": tactics_range},
    )


def _seed_all(seed: int) -> None:
    """エンジンが使う乱数をすべて固定する.

    部位選択は `random` とは別の RNG を使うため、個別に固定する。
    """
    random.seed(seed)
    np.random.seed(seed)
    combat._part_hit_rng.seed(seed)


def _record_attacks(sim: BattleSimulator, records: list[AttackRecord]) -> None:
    """命中率計算を包み、攻撃時の距離とセクタを記録する.

    MISS ログには攻撃セクタが載らない。距離も移動後の位置からは復元できない。
    乱数を消費しないため、戦闘結果は変わらない。
    """
    original = sim._calculate_hit_chance

    def wrapped(
        actor: MobileSuit, target: MobileSuit, weapon: Weapon, distance: float
    ) -> tuple[float, float, str]:
        result = original(actor, target, weapon, distance)
        records.append(
            AttackRecord(
                unit=str(actor.id),
                time=sim.elapsed_time,
                distance=distance,
                optimal_range=weapon.optimal_range,
                is_melee=weapon.weapon_type == "MELEE" or weapon.is_melee,
                sector=result[2],
            )
        )
        return result

    sim._calculate_hit_chance = wrapped  # type: ignore[method-assign]


def _longest_melee_miss(records: list[AttackRecord]) -> tuple[float, int]:
    """格闘 MISS の最長連続を (秒, 回数) で返す.

    連続は同じユニットの命中で途切れる。命中した武器の種別は問わない。
    """
    best_sec, best_count = 0.0, 0
    streaks: dict[str, tuple[float, int]] = {}
    for r in records:
        if r.is_hit:
            streaks.pop(r.unit, None)
            continue
        if not r.is_melee:
            continue
        start, count = streaks.get(r.unit, (r.time, 0))
        streaks[r.unit] = (start, count + 1)
        if count + 1 > best_count or (
            count + 1 == best_count and r.time - start > best_sec
        ):
            best_sec, best_count = r.time - start, count + 1
    return best_sec, best_count


def run_battle(
    scenario_key: str, condition: Condition, seed: int, max_steps: int
) -> BattleMetrics:
    """1 戦して計測値を返す.

    seed が奇数のときは B を PLAYER 側にする。行動順の偏りを打ち消すため。
    """
    scenario = SCENARIOS[scenario_key]
    _seed_all(seed)
    half = scenario.start_distance / 2.0
    a_is_player = seed % 2 == 0
    unit_a = _build_unit(
        scenario.a,
        _UNIT_A_ID,
        "PLAYER" if a_is_player else "ENEMY",
        Vector3(x=1000.0 - half, y=0, z=1000.0),
        condition.strategy,
        condition.range_a,
    )
    unit_b = _build_unit(
        scenario.b,
        _UNIT_B_ID,
        "ENEMY" if a_is_player else "PLAYER",
        Vector3(x=1000.0 + half, y=0, z=1000.0),
        condition.strategy,
        condition.range_b,
    )
    player, enemy = (unit_a, unit_b) if a_is_player else (unit_b, unit_a)
    sim = BattleSimulator(
        player,
        [enemy],
        player_pilot_stats=_PILOT_STATS,
        npc_pilot_stats={str(enemy.id): _PILOT_STATS},
    )
    records: list[AttackRecord] = []
    _record_attacks(sim, records)

    distances: list[float] = []
    log_cursor = 0
    record_cursor = 0
    weapon_switches = 0
    steps = 0
    while not sim.is_finished and steps < max_steps:
        sim.step(_DT)
        steps += 1
        new_logs = sim.logs[log_cursor:]
        log_cursor = len(sim.logs)
        # ATTACK / MISS ログは命中率計算 1 回につき 1 件、同じ順で出る。
        outcomes = [log for log in new_logs if log.action_type in ("ATTACK", "MISS")]
        for record, log in zip(records[record_cursor:], outcomes, strict=True):
            record.is_hit = log.action_type == "ATTACK"
        record_cursor = len(records)
        weapon_switches += sum(
            1 for log in new_logs if log.action_type == "WEAPON_SWITCH_START"
        )
        if records and unit_a.current_hp > 0 and unit_b.current_hp > 0:
            distances.append(
                float(
                    np.linalg.norm(
                        unit_a.position.to_numpy() - unit_b.position.to_numpy()
                    )
                )
            )

    a_alive, b_alive = unit_a.current_hp > 0, unit_b.current_hp > 0
    winner = "A" if a_alive and not b_alive else "B" if b_alive and not a_alive else ""
    sectors = {s: 0 for s in _SECTORS}
    for r in records:
        sectors[r.sector] += 1
    miss_sec, miss_count = _longest_melee_miss(records)
    return BattleMetrics(
        seed=seed,
        duration=sim.elapsed_time,
        timed_out=a_alive and b_alive,
        winner=winner,
        engaged_distances=distances,
        melee_ratios=[r.distance / r.optimal_range for r in records if r.is_melee],
        ranged_ratios=[r.distance / r.optimal_range for r in records if not r.is_melee],
        sector_counts=sectors,
        weapon_switches=weapon_switches,
        longest_melee_miss_sec=miss_sec,
        longest_melee_miss_count=miss_count,
    )


# ---------------------------------------------------------------------------
# 集計
# ---------------------------------------------------------------------------


def _percentiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p10": None, "p50": None, "p90": None}
    p10, p50, p90 = np.percentile(values, [10, 50, 90])
    return {"p10": float(p10), "p50": float(p50), "p90": float(p90)}


def summarize(battles: list[BattleMetrics]) -> dict[str, Any]:
    """1 条件の全試行を集計する.

    距離はステップごとの標本を全試行分まとめて扱う。長い戦闘ほど重みが大きい。
    """
    distances = [d for b in battles for d in b.engaged_distances]
    sector_total = {s: sum(b.sector_counts[s] for b in battles) for s in _SECTORS}
    attack_total = sum(sector_total.values())
    durations = [b.duration for b in battles]
    total_minutes = sum(durations) / 60.0
    rounds = len(battles)
    longest = max(battles, key=lambda b: (b.longest_melee_miss_sec, b.seed))
    return {
        "rounds": rounds,
        "distance": _percentiles(distances),
        "melee_optimal_ratio": _percentiles(
            [x for b in battles for x in b.melee_ratios]
        ),
        "ranged_optimal_ratio": _percentiles(
            [x for b in battles for x in b.ranged_ratios]
        ),
        "under_melee_range_rate": (
            sum(d < MELEE_RANGE for d in distances) / len(distances)
            if distances
            else None
        ),
        "under_close_range_rate": (
            sum(d < _CLOSE_RANGE for d in distances) / len(distances)
            if distances
            else None
        ),
        "longest_melee_miss_sec": longest.longest_melee_miss_sec,
        "longest_melee_miss_count": longest.longest_melee_miss_count,
        "longest_melee_miss_seed": longest.seed,
        # 両機の合計を 1 機あたりに直す。
        "weapon_switches_per_min": (
            sum(b.weapon_switches for b in battles) / total_minutes / 2.0
            if total_minutes
            else 0.0
        ),
        "attacks": attack_total,
        "sector_rates": {
            s: (sector_total[s] / attack_total if attack_total else 0.0)
            for s in _SECTORS
        },
        "duration": {
            "p50": float(np.median(durations)),
            "mean": float(np.mean(durations)),
        },
        "timeout_rate": sum(b.timed_out for b in battles) / rounds,
        "a_win_rate": sum(b.winner == "A" for b in battles) / rounds,
        "b_win_rate": sum(b.winner == "B" for b in battles) / rounds,
        "battles": [
            {
                "seed": b.seed,
                "duration": b.duration,
                "winner": b.winner,
                "longest_melee_miss_sec": b.longest_melee_miss_sec,
                "longest_melee_miss_count": b.longest_melee_miss_count,
            }
            for b in battles
        ],
    }


# ---------------------------------------------------------------------------
# 表示
# ---------------------------------------------------------------------------


def _fmt(value: float | None, spec: str) -> str:
    return "-" if value is None else format(value, spec)


def _distance_cell(dist: dict[str, float | None]) -> str:
    return "/".join(_fmt(dist[k], ".0f") for k in ("p10", "p50", "p90"))


def _sector_cell(rates: dict[str, float]) -> str:
    return "/".join(f"{rates[s] * 100:.0f}" for s in _SECTORS)


def print_scenario_table(scenario: Scenario, results: dict[str, dict]) -> None:
    """1 シナリオの結果を Markdown の表で出力する."""
    print(
        f"\n### {scenario.title}: {scenario.a.label} (A) vs {scenario.b.label} (B)"
        f"・{scenario.start_distance:.0f}m 開始\n"
    )
    print(
        "| 条件 | 攻撃数 | 距離 p10/p50/p90 | <50m | <150m | 最適比 格闘/射撃 p50 "
        "| 格闘ミス最長 | 持ち替え/分 | セクタ F/FS/RS/R % "
        "| 戦闘時間 p50 | 時間切れ | A 勝率 | B 勝率 |"
    )
    print("|---" * 13 + "|")
    for key, r in results.items():
        print(
            f"| {key} | {r['attacks']} | {_distance_cell(r['distance'])} "
            f"| {_fmt(r['under_melee_range_rate'], '.0%')} "
            f"| {_fmt(r['under_close_range_rate'], '.0%')} "
            f"| {_fmt(r['melee_optimal_ratio']['p50'], '.2f')}"
            f"/{_fmt(r['ranged_optimal_ratio']['p50'], '.2f')} "
            f"| {r['longest_melee_miss_sec']:.1f}s ({r['longest_melee_miss_count']}回) "
            f"| {r['weapon_switches_per_min']:.1f} "
            f"| {_sector_cell(r['sector_rates'])} "
            f"| {r['duration']['p50']:.0f}s "
            f"| {r['timeout_rate']:.0%} "
            f"| {r['a_win_rate']:.0%} | {r['b_win_rate']:.0%} |"
        )


# 差分表に載せる指標。(列名, 値を取り出す関数, 書式)
_DIFF_METRICS: tuple[tuple[str, Any, str], ...] = (
    ("距離 p50", lambda r: r["distance"]["p50"], ".0f"),
    ("<50m", lambda r: r["under_melee_range_rate"], ".0%"),
    ("<150m", lambda r: r["under_close_range_rate"], ".0%"),
    ("最適比 格闘", lambda r: r["melee_optimal_ratio"]["p50"], ".2f"),
    ("最適比 射撃", lambda r: r["ranged_optimal_ratio"]["p50"], ".2f"),
    ("格闘ミス最長(s)", lambda r: r["longest_melee_miss_sec"], ".1f"),
    ("持ち替え/分", lambda r: r["weapon_switches_per_min"], ".1f"),
    ("FRONT", lambda r: r["sector_rates"]["FRONT"], ".0%"),
    ("戦闘時間 p50", lambda r: r["duration"]["p50"], ".0f"),
    ("時間切れ", lambda r: r["timeout_rate"], ".0%"),
    ("A 勝率", lambda r: r["a_win_rate"], ".0%"),
)


def _diff_cell(before: float | None, after: float | None, spec: str) -> str:
    if before is None or after is None:
        return f"{_fmt(before, spec)} → {_fmt(after, spec)}"
    delta = after - before
    sign = "+" if delta >= 0 else "-"
    # 割合は差もパーセントポイントで表す。
    delta_text = format(abs(delta), spec).replace("%", "pt")
    return f"{format(before, spec)} → {format(after, spec)} ({sign}{delta_text})"


def print_diff(before: dict, after: dict) -> None:
    """2 つの結果 JSON の差分を Markdown の表で出力する."""
    print(f"before: {before['meta']['created_at']} ({before['meta']['git_rev']})")
    print(f"after : {after['meta']['created_at']} ({after['meta']['git_rev']})")
    for scenario_key, after_results in after["results"].items():
        before_results = before["results"].get(scenario_key)
        if before_results is None:
            print(f"\n### {scenario_key}: before に無いため省略")
            continue
        print(f"\n### {scenario_key}\n")
        print("| 条件 | " + " | ".join(name for name, _, _ in _DIFF_METRICS) + " |")
        print("|---" * (len(_DIFF_METRICS) + 1) + "|")
        for key, a in after_results.items():
            b = before_results.get(key)
            if b is None:
                continue
            cells = [_diff_cell(get(b), get(a), spec) for _, get, spec in _DIFF_METRICS]
            print(f"| {key} | " + " | ".join(cells) + " |")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _git_rev() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _conditions(scenario: Scenario, strategies: list[str], ranges: list[str] | None):
    pairs = [(r, r) for r in ranges] if ranges else list(scenario.range_pairs)
    return [Condition(s, ra, rb) for s in strategies for ra, rb in pairs]


def _split(value: str | None) -> list[str] | None:
    return [v.strip().upper() for v in value.split(",")] if value else None


def cmd_run(args: argparse.Namespace) -> None:
    """全シナリオ・全条件を計測し、表と JSON を出力する."""
    scenario_keys = [k.lower() for k in _split(args.scenarios) or SCENARIOS]
    unknown = [k for k in scenario_keys if k not in SCENARIOS]
    if unknown:
        sys.exit(f"不明なシナリオ: {unknown}（候補: {list(SCENARIOS)}）")
    strategies = _split(args.strategies) or list(_STRATEGIES)
    ranges = _split(args.ranges)

    jobs = {
        (key, cond): [args.seed + i for i in range(args.rounds)]
        for key in scenario_keys
        for cond in _conditions(SCENARIOS[key], strategies, ranges)
    }
    results: dict[str, dict[str, dict]] = {}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            job: [pool.submit(run_battle, *job, seed, args.max_steps) for seed in seeds]
            for job, seeds in jobs.items()
        }
        for (key, cond), fs in futures.items():
            results.setdefault(key, {})[cond.key] = summarize([f.result() for f in fs])
            print(f"done: {key} {cond.key}", file=sys.stderr)

    for key in scenario_keys:
        print_scenario_table(SCENARIOS[key], results[key])

    if args.output:
        payload = {
            "meta": {
                "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "git_rev": _git_rev(),
                "seed": args.seed,
                "rounds": args.rounds,
                "max_steps": args.max_steps,
                "scenarios": {
                    k: {
                        **asdict(SCENARIOS[k]),
                        "range_pairs": [list(p) for p in SCENARIOS[k].range_pairs],
                    }
                    for k in scenario_keys
                },
            },
            "results": results,
        }
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
        print(f"\n結果を保存しました: {out}", file=sys.stderr)


def cmd_diff(args: argparse.Namespace) -> None:
    """2 つの結果 JSON を比べる."""
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    if before["meta"]["seed"] != after["meta"]["seed"] or (
        before["meta"]["rounds"] != after["meta"]["rounds"]
    ):
        print("⚠️  seed または rounds が異なります。差は乱数の違いを含みます。")
    print_diff(before, after)


def main() -> None:
    """サブコマンドを振り分ける."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="計測して表と JSON を出力する")
    run.add_argument("--rounds", type=int, default=10, help="1 条件あたりの試行回数")
    run.add_argument("--seed", type=int, default=595, help="1 試行目のシード")
    run.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    run.add_argument("--max-steps", type=int, default=_DEFAULT_MAX_STEPS)
    run.add_argument(
        "--scenarios", help=f"カンマ区切り。既定は全シナリオ（{', '.join(SCENARIOS)}）"
    )
    run.add_argument(
        "--strategies", help=f"カンマ区切り。既定は {', '.join(_STRATEGIES)}"
    )
    run.add_argument(
        "--ranges",
        help="両機に同じ tactics.range を設定する（カンマ区切り）。"
        "既定はシナリオごとの組",
    )
    run.add_argument("--output", help="結果 JSON の保存先")
    run.set_defaults(func=cmd_run)

    diff = sub.add_parser("diff", help="2 つの結果 JSON を比べる")
    diff.add_argument("before")
    diff.add_argument("after")
    diff.set_defaults(func=cmd_diff)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# backend/scripts/simulation/terrain_balance_bench.py
"""地形適正と環境タイプの効果のバランスを 1対1 のモンテカルロで確認する.

DB を使わず、`data/master/` の機体・環境タイプの JSON から戦闘を組み立てる。

- 同一機体: ザク II の性能で地形適正ランクだけを変え、ランク差の影響を見る。
- 機体マスター: 地形適正が A 以外の機体を汎用機と戦わせ、環境ごとの勝率を見る。

Usage:
    python scripts/simulation/terrain_balance_bench.py
    python scripts/simulation/terrain_balance_bench.py --rounds 200 --workers 4
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

# プロセスごとに numpy がスレッドを増やすと、並列実行でかえって遅くなる。
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from app.engine.environment import EnvironmentProfile  # noqa: E402
from app.engine.simulation import BattleSimulator  # noqa: E402
from app.models.models import BattleField, MobileSuit, Vector3, Weapon  # noqa: E402

_MASTER_DIR = Path(__file__).resolve().parents[2] / "data" / "master"
_MAX_STEPS = 3000
# 同一機体の比較に使う機体。性能が平均的な汎用機にする。
_BASE_SUIT_ID = "zaku_ii"
# (環境タイプID, ミノフスキー濃度)
_CONDITIONS: list[tuple[str, float]] = [("FOREST", 0.6), ("SPACE", 0.3)]
# 機体マスターの比較で、地形に特化した機体の相手にする汎用機。
_GENERIC_IDS: tuple[str, ...] = ("zaku_ii", "gm")


@dataclass(frozen=True)
class Contestant:
    """対戦に出す機体."""

    label: str
    master_id: str
    terrain_adaptability: dict[str, str]


@dataclass(frozen=True)
class MatchResult:
    """1 組の対戦を rounds 回行った結果."""

    a: str
    b: str
    a_wins: int
    b_wins: int
    draws: int

    @property
    def a_win_rate(self) -> float:
        """引き分けを除いた a の勝率."""
        decided = self.a_wins + self.b_wins
        return self.a_wins / decided if decided else 0.0


def _load_json(name: str) -> list[dict]:
    return json.loads((_MASTER_DIR / name).read_text(encoding="utf-8"))


def _load_masters() -> dict[str, dict]:
    return {m["id"]: m for m in _load_json("mobile_suits.json")}


def _load_profiles() -> dict[str, EnvironmentProfile]:
    return {
        e["id"]: EnvironmentProfile(
            environment_id=e["id"],
            sensor_range_multiplier=e["sensor_range_multiplier"],
            ranged_accuracy_penalty=e["ranged_accuracy_penalty"],
            ranged_penalty_ref_distance=e["ranged_penalty_ref_distance"],
            default_obstacle_density=e["default_obstacle_density"],
            default_terrain_grade=e["default_terrain_grade"],
        )
        for e in _load_json("environments.json")
    }


def _build_unit(master: dict, contestant: Contestant, side: str) -> MobileSuit:
    specs = master["specs"]
    return MobileSuit(
        name=contestant.label,
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
        weapons=[Weapon(**w) for w in specs["weapons"]],
        missing_parts=specs.get("missing_parts", []),
        terrain_adaptability=contestant.terrain_adaptability,
        position=Vector3(x=0, y=0, z=0),
        side=side,
        team_id=f"{side}_TEAM",
    )


def _run_one(
    a: Contestant,
    b: Contestant,
    environment_id: str,
    minovsky: float,
    seed: int,
) -> str:
    """1 戦して勝者の label を返す。引き分けは空文字を返す.

    定期バトルと同じ最大ステップで決着しないときは、残り HP の割合が高い方を勝ちとする。
    """
    random.seed(seed)
    np.random.seed(seed)
    masters = _load_masters()
    profile = _load_profiles()[environment_id]
    # スポーン位置の偏りを打ち消すため、PLAYER 側を試行ごとに入れ替える。
    first, second = (a, b) if seed % 2 == 0 else (b, a)
    player = _build_unit(masters[first.master_id], first, "PLAYER")
    enemy = _build_unit(masters[second.master_id], second, "ENEMY")
    sim = BattleSimulator(
        player,
        [enemy],
        battlefield=BattleField(),
        minovsky_density=minovsky,
        environment_profile=profile,
    )
    for _ in range(_MAX_STEPS):
        if sim.is_finished:
            break
        sim.step()
    ratios = {u.name: u.current_hp / u.max_hp for u in sim.units}
    if ratios[a.label] == ratios[b.label]:
        return ""
    return max(ratios, key=lambda name: ratios[name])


def _run_match(
    pool: ProcessPoolExecutor,
    a: Contestant,
    b: Contestant,
    environment_id: str,
    minovsky: float,
    rounds: int,
    seed: int,
) -> MatchResult:
    futures = [
        pool.submit(_run_one, a, b, environment_id, minovsky, seed + i)
        for i in range(rounds)
    ]
    winners = [f.result() for f in futures]
    return MatchResult(
        a=a.label,
        b=b.label,
        a_wins=winners.count(a.label),
        b_wins=winners.count(b.label),
        draws=winners.count(""),
    )


def _print_results(title: str, results: list[MatchResult]) -> None:
    print(f"\n### {title}\n")
    print("| A | B | A 勝 | B 勝 | 引分 | A 勝率 |")
    print("|---|---|---|---|---|---|")
    for r in results:
        print(
            f"| {r.a} | {r.b} | {r.a_wins} | {r.b_wins} | {r.draws} "
            f"| {r.a_win_rate:.1%} |"
        )


def _grade_contestants(environment_id: str) -> list[Contestant]:
    return [
        Contestant(
            label=f"{_BASE_SUIT_ID}[{grade}]",
            master_id=_BASE_SUIT_ID,
            terrain_adaptability={environment_id: grade},
        )
        for grade in ("S", "A", "C")
    ]


def _master_pairs(masters: dict[str, dict]) -> list[tuple[Contestant, Contestant]]:
    """地形適正が A 以外の機体と汎用機の組を返す."""
    contestants = {
        master_id: Contestant(
            label=master_id,
            master_id=master_id,
            terrain_adaptability=master["specs"].get("terrain_adaptability", {}),
        )
        for master_id, master in masters.items()
    }
    specialists = [
        c
        for c in contestants.values()
        if c.master_id not in _GENERIC_IDS
        and any(c.terrain_adaptability.get(env, "A") != "A" for env, _ in _CONDITIONS)
    ]
    return [
        (specialist, contestants[generic_id])
        for specialist in specialists
        for generic_id in _GENERIC_IDS
    ]


def main() -> None:
    """条件ごとに対戦を行い、結果を Markdown の表で出力する."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=100, help="1 組あたりの試行回数")
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--seed", type=int, default=576)
    parser.add_argument(
        "--skip-masters", action="store_true", help="機体マスターの比較を省く"
    )
    args = parser.parse_args()

    masters = _load_masters()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for environment_id, minovsky in _CONDITIONS:
            condition = f"{environment_id}・ミノフスキー {minovsky}"
            grades = _grade_contestants(environment_id)
            _print_results(
                f"同一機体のランク差（{condition}）",
                [
                    _run_match(
                        pool, a, b, environment_id, minovsky, args.rounds, args.seed
                    )
                    for a, b in itertools.combinations(grades, 2)
                ],
            )
            if args.skip_masters:
                continue
            _print_results(
                f"特化機と汎用機（{condition}）",
                [
                    _run_match(
                        pool, a, b, environment_id, minovsky, args.rounds, args.seed
                    )
                    for a, b in _master_pairs(masters)
                ],
            )


if __name__ == "__main__":
    main()

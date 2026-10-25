#!/usr/bin/env python3
# backend/scripts/simulation/retreat_support_bench.py
"""撤退支援と殲滅戦で、ビルドごとの成功率と時間切れの割合を比べる（Issue #686）.

DB に繋がない。作戦の機体が参照する機体マスターは `--master-dir` の JSON から読む
（既定はテスト用の固定データ。本番の値は `export_master_data.py` で書き出して渡す）。
プレイヤー機は合成したビルド（同程度の戦力）で出す。値の大きさは機体マスターに揃える。

* annihilator: 高 HP・高火力・低機動。敵を倒して勝つ「殲滅向け」
* mobile: 低 HP・高機動・長い索敵。友軍の近くで敵を引きつける「機動・索敵寄り」
* balanced: 中間
* escort: 中間より少し軽く、長い射程で撤退機を狙う敵を優先して撃つ（`PROTECT`）「足止め・護衛」
* absent: 出撃なし（開始時に HP 0）。何もしなければ失敗する難易度かを確かめる。撤退支援だけで回す

殲滅戦は同じ友軍・敵小隊で、撤退ポイントなし・友軍も戦う・殲滅目標で戦う。
成功率の括弧内は 95% 信頼区間（Wilson）。
射撃の制圧は、どちらの目標でも `--suppression` の係数で有効にする（既定は作戦と同じ）。

Usage:
    cd backend
    uv run python scripts/simulation/retreat_support_bench.py --rounds 60
    uv run python scripts/simulation/retreat_support_bench.py --suppression off
    uv run python scripts/simulation/retreat_support_bench.py --suppression penalty=0.3,dirs=all
    uv run python scripts/simulation/retreat_support_bench.py \
        --master-dir scripts/maintenance/output/master_data
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import uuid
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import cache
from pathlib import Path

# プロセスごとに numpy がスレッドを増やすと、並列実行でかえって遅くなる。
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from app.engine.constants import TACTICS_PRIORITY_PROTECT  # noqa: E402
from app.engine.objectives import AnnihilationObjective  # noqa: E402
from app.engine.suppression import SuppressionConfig  # noqa: E402
from app.models.models import MobileSuit, Vector3, Weapon  # noqa: E402
from app.services.battle_execution import (  # noqa: E402
    run_battle,
    seed_battle_rngs,
)
from app.services.mission_battle import (  # noqa: E402
    MissionMasters,
    build_mission_battle,
    build_mission_unit,
)
from app.services.retreat_support_mission import (  # noqa: E402
    build_retreat_support_mission,
)
from app.services.theater_service import BattleConditions  # noqa: E402
from scripts.master_data import (  # noqa: E402
    FIXTURE_DIR,
    mission_masters_from_data,
    read_master_dir,
)
from scripts.simulation.suppression_args import parse_suppression  # noqa: E402

MAX_STEPS = 3000


@dataclass(frozen=True)
class Build:
    """プレイヤー機のビルド."""

    label: str
    max_hp: int
    armor: int
    mobility: float
    sensor_range: float
    power: int
    weapon_range: float
    accuracy: float
    optimal_range: float = 300.0
    priority: str = "CLOSEST"
    absent: bool = False


BUILDS = [
    Build("annihilator", 1200, 90, 0.9, 500, 240, 450, 75),
    Build("balanced", 950, 65, 1.2, 600, 180, 450, 72),
    Build("mobile", 750, 45, 1.6, 800, 120, 400, 68),
    Build("escort", 850, 55, 1.3, 700, 150, 600, 70, 450.0, TACTICS_PRIORITY_PROTECT),
    Build("absent", 950, 65, 1.2, 600, 180, 450, 72, absent=True),
]


@cache
def mission_masters(master_dir: Path) -> MissionMasters:
    """撤退支援の機体が参照するマスターを読む. プロセスごとに 1 回だけ読む."""
    return mission_masters_from_data(
        read_master_dir(master_dir), build_retreat_support_mission()
    )


def make_player(build: Build, team_id: str) -> MobileSuit:
    """ビルドからプレイヤー機を作る."""
    unit = MobileSuit(
        id=uuid.uuid4(),
        name=build.label,
        max_hp=build.max_hp,
        current_hp=build.max_hp,
        armor=build.armor,
        mobility=build.mobility,
        sensor_range=build.sensor_range,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="bench_rifle",
                name="Rifle",
                power=build.power,
                range=build.weapon_range,
                accuracy=build.accuracy,
                optimal_range=build.optimal_range,
            )
        ],
        side="PLAYER",
        team_id=team_id,
        tactics={"priority": build.priority, "range": "BALANCED"},
    )
    unit.normalize_parts()
    return unit


def run_retreat_support(
    build: Build, seed: int, suppression: SuppressionConfig | None, master_dir: Path
) -> dict:
    """撤退支援を 1 戦する."""
    seed_battle_rngs(seed)
    mission = build_retreat_support_mission()
    player = make_player(build, "player-team")
    if build.absent:
        player.current_hp = 0
    setup = build_mission_battle(
        mission, [player], BattleConditions(), masters=mission_masters(master_dir)
    )
    outcome = run_battle(
        player,
        setup.mission_units,
        setup.conditions,
        max_steps=MAX_STEPS,
        objective=setup.objective,
        retreat_points=setup.retreat_points,
        unit_assignments=setup.unit_assignments,
        suppression=suppression,
    )
    result = outcome.objective_result
    assert result is not None
    return {
        "success": result.is_success,
        "escaped": result.progress,
        "lost": result.lost,
        "timeout": not outcome.simulator.is_finished,
        "player_survived": bool(result.player_survived),
        "elapsed": outcome.simulator.elapsed_time,
    }


def run_annihilation(
    build: Build, seed: int, suppression: SuppressionConfig | None, master_dir: Path
) -> dict:
    """同じ友軍・敵小隊との殲滅戦を 1 戦する（撤退ポイントなし、友軍は戦う）."""
    seed_battle_rngs(seed)
    mission = build_retreat_support_mission()
    masters = mission_masters(master_dir)
    player = make_player(build, "player-team")
    allies = []
    for config in mission.ally_unit_configs():
        ally = build_mission_unit(config, "PLAYER", masters=masters)
        ally.team_id = "player-team"
        allies.append(ally)
    enemies = []
    for config in mission.enemy_unit_configs():
        enemy = build_mission_unit(config, "ENEMY", masters=masters)
        enemy.team_id = "enemy-team"
        enemies.append(enemy)
    outcome = run_battle(
        player,
        [*allies, *enemies],
        BattleConditions(),
        max_steps=MAX_STEPS,
        objective=AnnihilationObjective(),
        suppression=suppression,
    )
    return {
        "success": outcome.player_win,
        "escaped": 0,
        "lost": sum(ally.current_hp <= 0 for ally in allies),
        "timeout": not outcome.simulator.is_finished,
        "player_survived": player.current_hp > 0,
        "elapsed": outcome.simulator.elapsed_time,
    }


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """成功率の信頼区間（Wilson）を返す. 既定は 95%."""
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def main() -> None:
    """ビルドごとに集計して表示する."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--rounds", type=int, default=100)
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    parser.add_argument(
        "--suppression",
        default="on",
        help="射撃の制圧。off / on / 係数の上書き（例: penalty=0.3,dirs=all）",
    )
    parser.add_argument(
        "--master-dir",
        type=Path,
        default=FIXTURE_DIR,
        help="機体マスター・エースを読む JSON ディレクトリ（既定: テスト用の固定データ）",
    )
    args = parser.parse_args()
    try:
        suppression = parse_suppression(args.suppression)
    except ValueError as e:
        sys.exit(str(e))

    print(
        f"rounds={args.rounds} suppression={suppression} master_dir={args.master_dir}"
    )
    print(
        f"{'mode':<16}{'build':<13}{'success (95% CI)':>20}{'timeout':>9}"
        f"{'avg_escaped':>13}{'avg_lost':>10}{'player_alive':>14}{'avg_sec':>9}"
    )
    runners = (
        ("retreat_support", run_retreat_support),
        ("annihilation", run_annihilation),
    )
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            (mode, build.label): [
                pool.submit(runner, build, seed, suppression, args.master_dir)
                for seed in range(1, args.rounds + 1)
            ]
            for mode, runner in runners
            for build in BUILDS
            if not (build.absent and mode == "annihilation")
        }
        for (mode, label), fs in futures.items():
            results = [f.result() for f in fs]
            n = len(results)
            successes = sum(r["success"] for r in results)
            low, high = wilson_interval(successes, n)
            success = f"{successes / n:.0%} ({low:.0%}-{high:.0%})"
            print(
                f"{mode:<16}{label:<13}{success:>20}"
                f"{sum(r['timeout'] for r in results) / n:>9.0%}"
                f"{sum(r['escaped'] for r in results) / n:>13.2f}"
                f"{sum(r['lost'] for r in results) / n:>10.2f}"
                f"{sum(r['player_survived'] for r in results) / n:>14.0%}"
                f"{sum(r['elapsed'] for r in results) / n:>9.1f}"
            )


if __name__ == "__main__":
    main()

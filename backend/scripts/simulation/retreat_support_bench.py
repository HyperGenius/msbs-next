#!/usr/bin/env python3
# backend/scripts/simulation/retreat_support_bench.py
"""撤退支援と殲滅戦で、ビルドごとの成功率と時間切れの割合を比べる（Issue #686）.

DB に繋がない。プレイヤー機は合成した 3 種のビルド（同程度の戦力）で出す。

* annihilator: 高 HP・高火力・低機動。敵を倒して勝つ「殲滅向け」
* mobile: 低 HP・高機動・長い索敵。友軍の近くで敵を引きつける「機動・索敵寄り」
* balanced: 中間

殲滅戦は同じ友軍・敵小隊で、撤退ポイントなし・友軍も戦う・殲滅目標で戦う。

Usage:
    cd backend
    uv run python scripts/simulation/retreat_support_bench.py --rounds 60
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from dataclasses import dataclass

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from app.engine.objectives import AnnihilationObjective  # noqa: E402
from app.models.models import MobileSuit, Vector3, Weapon  # noqa: E402
from app.services.battle_execution import (  # noqa: E402
    run_battle,
    seed_battle_rngs,
)
from app.services.mission_battle import (  # noqa: E402
    build_mission_battle,
    build_mission_unit,
)
from app.services.retreat_support_mission import (  # noqa: E402
    build_retreat_support_mission,
)
from app.services.theater_service import BattleConditions  # noqa: E402

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


BUILDS = [
    Build("annihilator", 160, 10, 0.9, 500, 30, 450, 75),
    Build("balanced", 120, 7, 1.2, 600, 22, 450, 72),
    Build("mobile", 90, 5, 1.6, 800, 14, 400, 68),
]


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
            )
        ],
        side="PLAYER",
        team_id=team_id,
    )
    unit.normalize_parts()
    return unit


def run_retreat_support(build: Build, seed: int) -> dict:
    """撤退支援を 1 戦する."""
    seed_battle_rngs(seed)
    mission = build_retreat_support_mission()
    player = make_player(build, "player-team")
    setup = build_mission_battle(mission, [player], BattleConditions())
    outcome = run_battle(
        player,
        setup.mission_units,
        setup.conditions,
        max_steps=MAX_STEPS,
        objective=setup.objective,
        retreat_points=setup.retreat_points,
        unit_assignments=setup.unit_assignments,
    )
    result = outcome.objective_result
    assert result is not None
    return {
        "success": result.is_success,
        "escaped": result.progress,
        "timeout": not outcome.simulator.is_finished,
        "player_survived": bool(result.player_survived),
    }


def run_annihilation(build: Build, seed: int) -> dict:
    """同じ友軍・敵小隊との殲滅戦を 1 戦する（撤退ポイントなし、友軍は戦う）."""
    seed_battle_rngs(seed)
    mission = build_retreat_support_mission()
    player = make_player(build, "player-team")
    allies = []
    for config in mission.ally_unit_configs():
        ally = build_mission_unit(config, "PLAYER")
        ally.team_id = "player-team"
        allies.append(ally)
    enemies = []
    for config in mission.enemy_unit_configs():
        enemy = build_mission_unit(config, "ENEMY")
        enemy.team_id = "enemy-team"
        enemies.append(enemy)
    outcome = run_battle(
        player,
        [*allies, *enemies],
        BattleConditions(),
        max_steps=MAX_STEPS,
        objective=AnnihilationObjective(),
    )
    return {
        "success": outcome.player_win,
        "escaped": 0,
        "timeout": not outcome.simulator.is_finished,
        "player_survived": player.current_hp > 0,
    }


def main() -> None:
    """ビルドごとに集計して表示する."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=60)
    args = parser.parse_args()

    print(f"rounds={args.rounds}")
    print(
        f"{'mode':<16}{'build':<13}{'success':>8}{'timeout':>9}"
        f"{'avg_escaped':>13}{'player_alive':>14}"
    )
    for mode, runner in (
        ("retreat_support", run_retreat_support),
        ("annihilation", run_annihilation),
    ):
        for build in BUILDS:
            results = [runner(build, seed) for seed in range(1, args.rounds + 1)]
            n = len(results)
            print(
                f"{mode:<16}{build.label:<13}"
                f"{sum(r['success'] for r in results) / n:>8.0%}"
                f"{sum(r['timeout'] for r in results) / n:>9.0%}"
                f"{sum(r['escaped'] for r in results) / n:>13.2f}"
                f"{sum(r['player_survived'] for r in results) / n:>14.0%}"
            )


if __name__ == "__main__":
    main()

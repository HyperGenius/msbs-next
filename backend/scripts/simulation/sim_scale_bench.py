#!/usr/bin/env python3
# backend/scripts/simulation/sim_scale_bench.py
"""ユニット数スケーリングベンチマーク（Issue #446）.

索敵・ターゲット選定処理の最適化（グリッド分割によるO(N^2)解消）の効果を
確認するため、DBを使わず合成ユニットで 8/50/100 機構成のバトルを生成し、
`BattleSimulator.step()` 1回あたりの平均処理時間を計測する。

Usage:
    python scripts/simulation/sim_scale_bench.py
    python scripts/simulation/sim_scale_bench.py --sizes 8,50,100 --steps 100
"""

from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


def _make_unit(index: int, team_id: str, side: str, x: float, z: float) -> MobileSuit:
    return MobileSuit(
        name=f"{team_id}-{index}",
        max_hp=100,
        current_hp=100,
        armor=5,
        mobility=1.0,
        position=Vector3(x=x, y=0.0, z=z),
        sensor_range=500.0,
        side=side,
        team_id=team_id,
        weapons=[
            Weapon(
                id=f"weapon_{team_id}_{index}",
                name="Beam Rifle",
                power=25,
                range=800,
                accuracy=80.0,
            )
        ],
    )


def _build_units(room_size: int) -> tuple[MobileSuit, list[MobileSuit]]:
    """room_size 機（2チームへできる限り均等割り）のユニット群を生成する.

    room_size が奇数の場合は PLAYER_TEAM 側に1機多く割り当て、生成される
    総ユニット数が常に room_size と一致するようにする。ユニットはフィールド
    全体にランダム分散させ、極端に狭いクラスタで密集し過ぎない現実的な配置
    にする。

    Raises:
        ValueError: room_size が2未満の場合（両チーム最低1機ずつ必要なため）
    """
    if room_size < 2:
        raise ValueError(f"room_size は2以上である必要があります: {room_size}")

    player_team_size = math.ceil(room_size / 2)
    enemy_team_size = room_size - player_team_size
    rng = random.Random(42)
    field_extent = 3000.0

    player_units = [
        _make_unit(
            i,
            "PLAYER_TEAM",
            "PLAYER",
            rng.uniform(-field_extent, field_extent),
            rng.uniform(-field_extent, field_extent),
        )
        for i in range(player_team_size)
    ]
    enemy_units = [
        _make_unit(
            i,
            "ENEMY_TEAM",
            "ENEMY",
            rng.uniform(-field_extent, field_extent),
            rng.uniform(-field_extent, field_extent),
        )
        for i in range(enemy_team_size)
    ]

    player = player_units[0]
    enemies = player_units[1:] + enemy_units
    return player, enemies


def bench_room_size(room_size: int, steps: int) -> tuple[float, int]:
    """指定ユニット数でのシミュレーションを実行し、(1ステップあたりの平均秒数, 総ユニット数) を返す."""
    player, enemies = _build_units(room_size)
    total_units = 1 + len(enemies)
    sim = BattleSimulator(player, enemies)

    start = time.perf_counter()
    executed = 0
    for _ in range(steps):
        if sim.is_finished:
            break
        sim.step()
        executed += 1
    elapsed = time.perf_counter() - start

    avg_sec = elapsed / executed if executed else float("nan")
    return avg_sec, total_units


def main() -> None:
    """CLI エントリポイント: 引数を解析しベンチマークを実行して結果を表示する."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes",
        type=str,
        default="8,50,100",
        help="カンマ区切りの room_size 一覧（デフォルト: 8,50,100）",
    )
    parser.add_argument(
        "--steps", type=int, default=50, help="各構成での最大計測ステップ数"
    )
    args = parser.parse_args()

    sizes = [int(s.strip()) for s in args.sizes.split(",") if s.strip()]

    print(f"{'room_size':>10} | {'avg sec/step':>14} | {'units':>6}")
    print("-" * 38)
    for size in sizes:
        avg_sec, total_units = bench_room_size(size, args.steps)
        print(f"{size:>10} | {avg_sec:>14.6f} | {total_units:>6}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# backend/scripts/simulation/spawn_scale_bench.py
"""スポーン配置スケーリングベンチマーク（Issue #447）.

`_sample_position_in_zone()` の近傍探索最適化（グリッド分割による準O(N^2)解消）
の効果を確認するため、DBを使わず合成ユニットで 8/50/100 機構成の `BattleSimulator`
初期化（障害物生成 + スポーン領域決定 + スポーン配置）を繰り返し実行し、
1回あたりの平均処理時間を計測する。障害物密度による影響も確認できるよう
`--obstacle-density` で密度を切り替えられる。

Usage:
    python scripts/simulation/spawn_scale_bench.py
    python scripts/simulation/spawn_scale_bench.py --sizes 8,50,100 --repeats 20
    python scripts/simulation/spawn_scale_bench.py --obstacle-density DENSE
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from app.engine.simulation import BattleSimulator
from app.models.models import BattleField, MobileSuit, Vector3, Weapon

# ベンチマーク対象の合成配置は障害物密度によっては意図的にスポーン中心の
# 回避探索が失敗しうる（既存仕様の警告ログ）。計測結果の可読性のため抑制する。
logging.getLogger("app.engine.simulation").setLevel(logging.ERROR)


def _make_unit(index: int, team_id: str, side: str) -> MobileSuit:
    return MobileSuit(
        name=f"{team_id}-{index}",
        max_hp=100,
        current_hp=100,
        armor=5,
        mobility=1.0,
        # 配置前の初期座標は _apply_spawn_zones が上書きするため任意の値でよい
        position=Vector3(x=0.0, y=0.0, z=0.0),
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

    2チームに集中配置することで、単一スポーンゾーン内の配置密度を上げ、
    `_sample_position_in_zone` のリサンプリング回数が最も増えやすい条件で計測する。

    Raises:
        ValueError: room_size が2未満の場合（両チーム最低1機ずつ必要なため）
    """
    if room_size < 2:
        raise ValueError(f"room_size は2以上である必要があります: {room_size}")

    player_team_size = (room_size + 1) // 2
    enemy_team_size = room_size - player_team_size

    player_units = [
        _make_unit(i, "PLAYER_TEAM", "PLAYER") for i in range(player_team_size)
    ]
    enemy_units = [_make_unit(i, "ENEMY_TEAM", "ENEMY") for i in range(enemy_team_size)]

    player = player_units[0]
    enemies = player_units[1:] + enemy_units
    return player, enemies


def bench_room_size(
    room_size: int, repeats: int, obstacle_density: str
) -> tuple[float, int]:
    """指定ユニット数でスポーン処理（BattleSimulator初期化）を繰り返し実行する.

    Returns:
        (1回あたりの平均秒数, 総ユニット数)
    """
    total_units = room_size
    elapsed = 0.0
    for _ in range(repeats):
        player, enemies = _build_units(room_size)
        battlefield = BattleField(obstacle_density=obstacle_density)
        start = time.perf_counter()
        BattleSimulator(player, enemies, battlefield=battlefield)
        elapsed += time.perf_counter() - start

    avg_sec = elapsed / repeats if repeats else float("nan")
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
        "--repeats", type=int, default=20, help="各構成での計測繰り返し回数"
    )
    parser.add_argument(
        "--obstacle-density",
        type=str,
        default="MEDIUM",
        choices=["NONE", "LOW", "MEDIUM", "DENSE"],
        help="障害物密度（デフォルト: MEDIUM）。リトライ回数への影響を見たい場合は DENSE を指定",
    )
    args = parser.parse_args()

    sizes = [int(s.strip()) for s in args.sizes.split(",") if s.strip()]

    print(f"obstacle_density={args.obstacle_density}, repeats={args.repeats}")
    print(f"{'room_size':>10} | {'avg sec/spawn':>14} | {'units':>6}")
    print("-" * 40)
    for size in sizes:
        avg_sec, total_units = bench_room_size(
            size, args.repeats, args.obstacle_density
        )
        print(f"{size:>10} | {avg_sec:>14.6f} | {total_units:>6}")


if __name__ == "__main__":
    main()

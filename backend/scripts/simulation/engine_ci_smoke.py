#!/usr/bin/env python3
# backend/scripts/simulation/engine_ci_smoke.py
"""バトルエンジン変更時のCIスモークテスト（DB不要）.

`app/engine/**` を変更したPRでmainへのマージ前に、実際に
`BattleSimulator` を複数サイズ・複数ラウンドで完走させ、例外なく
決着するかを確認する。Neon/Cloud Runなど外部インフラには一切
接続せず、合成ユニット（`sim_scale_bench.py` と同じビルダー）で
完結する。

注意: このエンジンは戦闘処理（命中判定・ターゲット選定など）に
`random`/`np.random.default_rng()` を非シード化のまま使っており、
現状シード固定による再現性は無い。そのため本スクリプトは「同一
構成をNラウンド繰り返す」ことで揺らぎを吸収する方式を取る
（ユニット配置のみ `_build_units()` 内部で固定シード=42）。

失敗条件（exit code 1）:
- いずれかのラウンドで例外が発生した場合
- 全ラウンドが `--max-steps` に到達し、1件も決着しなかった場合
  （個別の引き分け・大規模構成での長期化は正常systemなので、
  全滅した場合のみ「エンジンが根本的に壊れている」signalとして扱う）

Usage:
    python scripts/simulation/engine_ci_smoke.py
    python scripts/simulation/engine_ci_smoke.py --sizes 2,8,20 --rounds 3
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import traceback

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from app.engine.simulation import BattleSimulator
from scripts.simulation.sim_scale_bench import _build_units


def _determine_win_team(sim: BattleSimulator) -> str:
    """チームごとの生存状況から決着チームIDを返す（複数チーム対応）."""
    alive_team_ids = {u.team_id for u in sim.units if u.current_hp > 0}
    if len(alive_team_ids) == 1:
        return next(iter(alive_team_ids))
    return "DRAW"


def _run_one(room_size: int, max_steps: int, dt: float) -> dict:
    """1回分のバトルを完走させ、結果を辞書で返す（例外はそのまま伝播させる）."""
    player, enemies = _build_units(room_size)
    sim = BattleSimulator(player, enemies)

    start = time.perf_counter()
    step_count = 0
    for _ in range(max_steps):
        if sim.is_finished:
            break
        sim.step(dt=dt)
        step_count += 1
    wall_clock = time.perf_counter() - start

    finished = sim.is_finished and step_count < max_steps
    return {
        "room_size": room_size,
        "step_count": step_count,
        "sim_elapsed_sec": round(step_count * dt, 1),
        "wall_clock_sec": round(wall_clock, 2),
        "finished": finished,
        "win_team": _determine_win_team(sim) if finished else "TIMEOUT",
    }


def main() -> int:
    """CLI引数を解釈し、全構成のスモークテストを実行してexit codeを返す."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes",
        type=str,
        default="2,8,20",
        help="カンマ区切りの room_size 一覧（デフォルト: 2,8,20）",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="サイズごとの繰り返し回数（デフォルト: 3。戦闘処理は非シード化のため"
        "ラウンドごとに結果が揺らぐ）",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=2000,
        help="1ラウンドあたりの最大ステップ数（デフォルト: 2000 = 200秒相当）",
    )
    parser.add_argument("--dt", type=float, default=0.1, help="時間ステップ幅（秒）")
    args = parser.parse_args()

    sizes = [int(s) for s in args.sizes.split(",")]

    results: list[dict] = []
    crashed = False

    print(
        f"{'room_size':>9} {'round':>6} {'steps':>7} {'sim_sec':>8} {'wall_sec':>9} {'result':>10}"
    )
    for room_size in sizes:
        for round_idx in range(args.rounds):
            try:
                result = _run_one(room_size, args.max_steps, args.dt)
            except Exception:
                crashed = True
                print(f"{room_size:>9} {round_idx:>6}  CRASHED")
                traceback.print_exc()
                continue

            results.append(result)
            outcome = result["win_team"] if result["finished"] else "TIMEOUT"
            print(
                f"{result['room_size']:>9} {round_idx:>6} "
                f"{result['step_count']:>7} {result['sim_elapsed_sec']:>8} "
                f"{result['wall_clock_sec']:>9} {outcome:>10}"
            )

    if crashed:
        print("\nNG: シミュレーション実行中に例外が発生しました。")
        return 1

    if results and not any(r["finished"] for r in results):
        print(
            f"\nNG: 全 {len(results)} ラウンドが max_steps={args.max_steps} に到達し、"
            "1件も決着しませんでした（エンジンの根本的な不具合の可能性）。"
        )
        return 1

    timeouts = [r for r in results if not r["finished"]]
    if timeouts:
        print(
            f"\n注意: {len(timeouts)}/{len(results)} ラウンドが max_steps 未決着でした"
            "（個別の長期化は許容範囲内）。"
        )

    print(f"\nOK: {len(results)} ラウンド完走（例外なし）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

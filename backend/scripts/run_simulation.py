#!/usr/bin/env python3
# backend/scripts/run_simulation.py
"""ローカル実行スクリプト: ミッションシミュレーション（サブコマンド構成）.

本番DBにReadOnlyで接続し、指定ミッションのデータを取得して
BattleSimulatorを実行し、結果ログをJSONファイルとして出力する。
DBへの書き込みは一切行わない。

Usage:
    # 単一シミュレーション実行（従来通り）
    python scripts/run_simulation.py run --mission-id 1
    python scripts/run_simulation.py run --mission-id 2 --output results/mission2.json
    python scripts/run_simulation.py run --mission-id 1 --steps 500 --output result.json

    # 複数回シミュレーションを実行してサマリーを集計
    python scripts/run_simulation.py bench --mission-id 1 --rounds 20

    # 2つの戦略を比較対照するA/Bテスト
    python scripts/run_simulation.py compare \\
        --mission-id 1 --strategy-a AGGRESSIVE --strategy-b DEFENSIVE --rounds 20

    # シミュレーション結果JSONからレポートを生成
    python scripts/run_simulation.py report --input data/sim_results/result_*.json

後方互換:
    python scripts/run_simulation.py --mission-id 1  （サブコマンドなし → run と同等）
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlmodel import Session, select

from app.db import engine
from app.engine.simulation import BattleSimulator
from app.models.models import Mission, MobileSuit, Vector3, Weapon


def _build_enemies_from_config(enemy_configs: list[dict]) -> list[MobileSuit]:
    """ミッション設定から敵ユニットリストを生成する.

    Args:
        enemy_configs: ミッションの enemy_config["enemies"] リスト

    Returns:
        生成した MobileSuit リスト
    """
    enemies = []
    for enemy_config in enemy_configs:
        pos_dict = enemy_config.get("position", {"x": 500, "y": 0, "z": 0})
        weapon_dict = enemy_config.get("weapon", {})
        terrain_adapt = enemy_config.get(
            "terrain_adaptability",
            {"SPACE": "A", "GROUND": "A", "COLONY": "A", "UNDERWATER": "C"},
        )
        enemy = MobileSuit(
            name=enemy_config.get("name", "ザクII"),
            max_hp=enemy_config.get("max_hp", 80),
            current_hp=enemy_config.get("max_hp", 80),
            armor=enemy_config.get("armor", 5),
            mobility=enemy_config.get("mobility", 1.2),
            position=Vector3(**pos_dict),
            terrain_adaptability=terrain_adapt,
            weapons=[
                Weapon(
                    id=weapon_dict.get("id", "weapon"),
                    name=weapon_dict.get("name", "Weapon"),
                    power=weapon_dict.get("power", 15),
                    range=weapon_dict.get("range", 400),
                    accuracy=weapon_dict.get("accuracy", 70),
                    type=weapon_dict.get("type", "PHYSICAL"),
                    optimal_range=weapon_dict.get("optimal_range", 300.0),
                    decay_rate=weapon_dict.get("decay_rate", 0.05),
                    max_ammo=weapon_dict.get("max_ammo"),
                    en_cost=weapon_dict.get("en_cost", 0),
                    cool_down_turn=weapon_dict.get("cool_down_turn", 0),
                )
            ],
            side="ENEMY",
            team_id="ENEMY_TEAM",
        )
        enemies.append(enemy)
    return enemies


def _serialize_log_entry(log_entry) -> dict:
    """BattleLog をJSONシリアライズ可能なdictに変換する.

    Args:
        log_entry: BattleLog インスタンスまたは dict

    Returns:
        JSON シリアライズ可能な dict
    """
    if hasattr(log_entry, "model_dump"):
        data = log_entry.model_dump()
    else:
        data = dict(log_entry)

    # UUID を文字列に変換
    for key, value in data.items():
        if isinstance(value, uuid.UUID):
            data[key] = str(value)

    # Vector3 を dict に変換
    for key in ("position_snapshot", "velocity_snapshot"):
        val = data.get(key)
        if val is not None and hasattr(val, "model_dump"):
            data[key] = val.model_dump()

    return data


def run(
    mission_id: int,
    max_steps: int = 5000,
    output_path: str | None = None,
    strategy: str | None = None,
    enable_hot_reload: bool = False,
) -> None:
    """シミュレーションを実行して結果を JSON に出力する.

    Args:
        mission_id: 実行するミッションID
        max_steps: 最大ステップ数（デフォルト 5000）
        output_path: 出力先 JSON ファイルパス。None の場合は自動生成。
        strategy: プレイヤー機体の戦略モード (AGGRESSIVE/DEFENSIVE/SNIPER 等)。None の場合は未設定。
        enable_hot_reload: True の場合、ファジィルール JSON の変更を自動検出して再ロードする（ローカル開発用）。
    """
    print("=" * 60)
    print(f"ミッション {mission_id} のシミュレーションを開始")
    print("=" * 60)

    # ReadOnly セッションでデータ取得（書き込みは行わない）
    with Session(engine) as session:
        # ミッションデータ取得
        mission = session.get(Mission, mission_id)
        if not mission:
            print(
                f"エラー: ミッション ID={mission_id} が見つかりません", file=sys.stderr
            )
            sys.exit(1)

        print(f"ミッション名: {mission.name}")
        print(f"難易度: {mission.difficulty}")
        print(f"環境: {mission.environment}")
        print(f"特殊効果: {mission.special_effects or '（なし）'}")

        # プレイヤー機体を取得（最初の1機）
        player_statement = select(MobileSuit).limit(1)
        player_results = list(session.exec(player_statement).all())

        if not player_results:
            print(
                "エラー: DBにモビルスーツが登録されていません。シードを実行してください。",
                file=sys.stderr,
            )
            sys.exit(1)

        # プレイヤー機体を準備（DBには書き込まない）
        player_raw = player_results[0]
        player = MobileSuit.model_validate(player_raw.model_dump())
        player.current_hp = player.max_hp
        player.position = Vector3(x=0, y=0, z=0)
        player.side = "PLAYER"
        player.team_id = "PLAYER_TEAM"
        if strategy is not None:
            player.strategy_mode = strategy.upper()

        print(f"プレイヤー機体: {player.name} (HP: {player.max_hp})")

        # 敵機体を生成（DBから取得したミッション設定を元に構築）
        enemy_configs = mission.enemy_config.get("enemies", [])
        enemies = _build_enemies_from_config(enemy_configs)

        print(f"敵機数: {len(enemies)}")
        for enemy in enemies:
            print(f"  - {enemy.name} (HP: {enemy.max_hp})")

        # セッションはここで閉じる（以降DBアクセスなし）

    print("\nシミュレーション実行中...")

    # BattleSimulator 実行
    sim = BattleSimulator(
        player=player,
        enemies=enemies,
        environment=mission.environment,
        special_effects=mission.special_effects or [],
        enable_hot_reload=enable_hot_reload,
    )

    step_count = 0
    for _ in range(max_steps):
        if sim.is_finished:
            break
        sim.step()
        step_count += 1

    print(
        f"シミュレーション完了 (ステップ数: {step_count}, 経過時間: {sim.elapsed_time:.1f}s)"
    )

    # 勝敗判定
    alive_team_ids = {u.team_id for u in sim.units if u.current_hp > 0}
    if player.team_id in alive_team_ids:
        win_loss = "WIN"
    elif not alive_team_ids:
        win_loss = "DRAW"
    else:
        win_loss = "LOSE"

    result_labels = {
        "WIN": "プレイヤー勝利",
        "LOSE": "プレイヤー敗北",
        "DRAW": "引き分け",
    }
    print(f"結果: {result_labels[win_loss]}")

    kills = sum(1 for e in enemies if e.current_hp <= 0)
    print(f"撃墜数: {kills} / {len(enemies)}")
    print(f"総ログ数: {len(sim.logs)}")

    # JSON 出力
    result = {
        "mission_id": mission_id,
        "mission_name": mission.name,
        "environment": mission.environment,
        "win_loss": win_loss,
        "elapsed_time": sim.elapsed_time,
        "step_count": step_count,
        "kills": kills,
        "player": {
            "name": player.name,
            "final_hp": player.current_hp,
            "max_hp": player.max_hp,
        },
        "enemies": [
            {
                "name": e.name,
                "final_hp": e.current_hp,
                "max_hp": e.max_hp,
            }
            for e in enemies
        ],
        "logs": [_serialize_log_entry(log) for log in sim.logs],
    }

    # 出力先を決定
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"simulation_mission{mission_id}_{timestamp}.json"

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n結果を保存しました: {output_file.resolve()}")


def parse_args() -> argparse.Namespace:
    """CLI 引数をパースする（サブコマンド構成 + 後方互換）."""
    # ---- 後方互換チェック: --mission-id が先頭にある場合は run サブコマンドとして扱う ----
    if len(sys.argv) > 1 and sys.argv[1].startswith("--"):
        # サブコマンドなし → sys.argv に "run" を挿入して後方互換を維持
        sys.argv.insert(1, "run")

    parser = argparse.ArgumentParser(
        description="ミッションシミュレーションをローカル実行するCLIツール。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
サブコマンド:
  run     単一シミュレーションを実行して結果JSONを出力する
  bench   複数回シミュレーションを実行してサマリーを集計する
  compare 2つの戦略モードを対戦させて比較する
  report  既存のシミュレーション結果JSONからレポートを生成する

使用例:
  python scripts/run_simulation.py run --mission-id 1
  python scripts/run_simulation.py bench --mission-id 1 --rounds 20
  python scripts/run_simulation.py compare --mission-id 1 --strategy-a AGGRESSIVE --strategy-b DEFENSIVE --rounds 20
  python scripts/run_simulation.py report --input data/sim_results/result_*.json
        """,
    )

    subparsers = parser.add_subparsers(dest="subcommand")

    # ---- run サブコマンド（既存機能） ----
    run_parser = subparsers.add_parser(
        "run",
        help="単一シミュレーションを実行して結果JSONを出力する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/run_simulation.py run --mission-id 1
  python scripts/run_simulation.py run --mission-id 2 --output results/mission2.json
  python scripts/run_simulation.py run --mission-id 1 --steps 500 --strategy AGGRESSIVE
        """,
    )
    _add_run_args(run_parser)

    # ---- bench サブコマンド ----
    bench_parser = subparsers.add_parser(
        "bench",
        help="複数回シミュレーションを実行してサマリーを集計する",
    )
    bench_parser.add_argument("--mission-id", type=int, required=True, metavar="ID")
    bench_parser.add_argument("--rounds", type=int, default=10, metavar="N", help="実行回数（デフォルト: 10）")
    bench_parser.add_argument(
        "--strategy",
        type=str,
        default="AGGRESSIVE",
        choices=["AGGRESSIVE", "DEFENSIVE", "SNIPER", "ASSAULT", "RETREAT"],
        metavar="MODE",
        help="全チームに適用する初期戦略モード（デフォルト: AGGRESSIVE）",
    )
    bench_parser.add_argument("--output", type=str, default=None, metavar="FILE", help="出力先ファイルパス")
    bench_parser.add_argument("--format", type=str, default="text", choices=["text", "json"], help="出力フォーマット")
    bench_parser.add_argument("--steps", type=int, default=5000, metavar="N", help="最大ステップ数")
    bench_parser.add_argument("--hot-reload", action="store_true", default=False)

    # ---- compare サブコマンド ----
    compare_parser = subparsers.add_parser(
        "compare",
        help="2つの戦略モードを対戦させて比較する",
    )
    compare_parser.add_argument("--mission-id", type=int, required=True, metavar="ID")
    compare_parser.add_argument("--rounds", type=int, default=10, metavar="N", help="実行回数（デフォルト: 10）")
    compare_parser.add_argument(
        "--strategy-a",
        type=str,
        default="AGGRESSIVE",
        choices=["AGGRESSIVE", "DEFENSIVE", "SNIPER", "ASSAULT", "RETREAT"],
        metavar="MODE",
        help="プレイヤーチームの戦略モード",
    )
    compare_parser.add_argument(
        "--strategy-b",
        type=str,
        default="DEFENSIVE",
        choices=["AGGRESSIVE", "DEFENSIVE", "SNIPER", "ASSAULT", "RETREAT"],
        metavar="MODE",
        help="敵チームの戦略モード",
    )
    compare_parser.add_argument("--output", type=str, default=None, metavar="FILE")
    compare_parser.add_argument("--format", type=str, default="text", choices=["text", "json"])
    compare_parser.add_argument("--steps", type=int, default=5000, metavar="N")
    compare_parser.add_argument("--hot-reload", action="store_true", default=False)

    # ---- report サブコマンド ----
    report_parser = subparsers.add_parser(
        "report",
        help="既存のシミュレーション結果JSONからレポートを生成する",
    )
    report_parser.add_argument(
        "--input",
        type=str,
        nargs="+",
        required=True,
        metavar="FILE",
        help="入力JSONファイルパス（ワイルドカード対応）",
    )
    report_parser.add_argument("--output", type=str, default=None, metavar="FILE")
    report_parser.add_argument("--format", type=str, default="text", choices=["text", "json"])

    return parser.parse_args()


def _add_run_args(parser: argparse.ArgumentParser) -> None:
    """run サブコマンドの共通引数を追加する."""
    parser.add_argument(
        "--mission-id",
        type=int,
        required=True,
        metavar="ID",
        help="実行するミッションのID",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="FILE",
        help="結果JSONの出力先ファイルパス（省略時は自動生成）",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=5000,
        metavar="N",
        help="最大ステップ数（デフォルト: 5000）",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default=None,
        choices=["AGGRESSIVE", "DEFENSIVE", "SNIPER", "ASSAULT", "RETREAT"],
        metavar="MODE",
        help="プレイヤー機体の戦略モード (AGGRESSIVE/DEFENSIVE/SNIPER/ASSAULT/RETREAT)。省略時はAGGRESSIVE。",
    )
    parser.add_argument(
        "--hot-reload",
        action="store_true",
        default=False,
        help="ファジィルール JSON の変更をシミュレーション実行ごとに自動反映する（ローカル開発用）",
    )


if __name__ == "__main__":
    args = parse_args()

    if args.subcommand == "run" or args.subcommand is None:
        run(
            mission_id=args.mission_id,
            max_steps=args.steps,
            output_path=args.output,
            strategy=args.strategy,
            enable_hot_reload=args.hot_reload,
        )
    elif args.subcommand == "bench":
        from scripts.sim_bench import run_bench_command

        run_bench_command(args)
    elif args.subcommand == "compare":
        from scripts.sim_compare import run_compare_command

        run_compare_command(args)
    elif args.subcommand == "report":
        from scripts.sim_report import run_report_command

        run_report_command(args)
    else:
        print(f"不明なサブコマンド: {args.subcommand}", file=sys.stderr)
        sys.exit(1)

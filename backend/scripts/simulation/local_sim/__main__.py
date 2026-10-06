"""ローカルバトルシミュレータの CLI.

backend/ で実行する:
    python -m scripts.simulation.local_sim fetch --pilot <パイロットID> --npc 7
    python -m scripts.simulation.local_sim run --roster <ロスター名> --rounds 20
    python -m scripts.simulation.local_sim list
    python -m scripts.simulation.local_sim report <世代>
    python -m scripts.simulation.local_sim compare <世代A> <世代B>
    python -m scripts.simulation.local_sim log-bench --roster <ロスター名>
    python -m scripts.simulation.local_sim log-compare <計測A> <計測B>
    python -m scripts.simulation.local_sim check-readonly
"""

import argparse
import contextlib
import json
import sys
from pathlib import Path

from sqlalchemy import Engine

# python scripts/simulation/local_sim のようにディレクトリを指定して実行したときも import できるようにする。
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.simulation.local_sim.generations import (  # noqa: E402
    GENERATIONS_DIR,
    KEEP_UNPINNED_GENERATIONS,
    Manifest,
    find_generation,
    list_generations,
    set_pinned,
)
from scripts.simulation.local_sim.readonly_db import (  # noqa: E402
    ReadOnlyConfigError,
    assert_read_only_session,
    check_writes_rejected,
    use_readonly_database,
)
from scripts.simulation.local_sim.roster import (  # noqa: E402
    ROSTERS_DIR,
    load_roster,
    resolve_roster_path,
    save_roster,
)


def _connect_readonly() -> Engine:
    """Read Only の接続でエンジンを作り、トランザクションが Read Only か確かめる."""
    use_readonly_database()
    from app.db import engine

    assert_read_only_session(engine)
    return engine


def _cmd_fetch(args: argparse.Namespace) -> int:
    engine = _connect_readonly()

    from sqlmodel import Session

    from scripts.simulation.local_sim.fetch import (
        FetchOptions,
        build_roster,
        default_roster_name,
        parse_unit_spec,
    )

    options = FetchOptions(
        mobile_suits=[parse_unit_spec(v) for v in args.ms],
        pilots=[parse_unit_spec(v) for v in args.pilot],
        npc_count=args.npc,
        ace_count=args.ace,
        theater_id=args.theater,
        minovsky_density=args.minovsky,
    )
    name = args.name or default_roster_name()
    print(f"本番DBから参加機体を取得します（ロスター: {name}）")
    # 取得した ORM オブジェクトを書き換えるため、autoflush で UPDATE が飛ばないようにする。
    with Session(engine, autoflush=False) as session:
        roster = build_roster(session, options, name)
        session.rollback()

    path = save_roster(roster, overwrite=args.force)
    conditions = roster.conditions
    print(
        f"  戦域: {conditions.theater_id or 'なし'} / 環境: {conditions.environment}"
        f" / ミノフスキー濃度: {conditions.minovsky_density}"
    )
    for entry in roster.entries:
        source = entry.source
        team = entry.snapshot.get("team_id") or "個人"
        print(
            f"  [{source.kind}] {entry.snapshot.get('name')}"
            f" / {source.pilot_name or '-'} / チーム: {team}"
        )
    print(f"{len(roster.entries)} 機を保存しました: {path}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    roster = load_roster(args.roster)
    roster_path = resolve_roster_path(args.roster)

    from scripts.simulation.local_sim.run import RunOptions, forbid_database

    forbid_database()
    from scripts.simulation.local_sim.run import run_generation

    options = RunOptions(
        rounds=args.rounds,
        seed=args.seed,
        label=args.label,
        pinned=args.pin,
    )
    if args.steps is not None:
        options.max_steps = args.steps
    print(
        f"ロスター {roster.name} で {args.rounds} 戦を実行します（{len(roster.entries)} 機）"
    )
    result = run_generation(roster, roster_path, options)
    manifest = result.manifest
    summary = manifest.summary
    print(
        f"{summary.wins} 勝 {summary.losses} 敗（打ち切り {summary.timeouts}）"
        f" / 判定する機体: {manifest.player_name} / seed: {manifest.seed}"
    )
    print(f"保存しました: {result.path}")
    for path in result.removed:
        print(f"  古い世代を削除しました: {path.name}")
    return 0


def _format_generation(manifest: Manifest) -> str:
    summary = manifest.summary
    return (
        f"{'*' if manifest.pinned else ' '} {manifest.generation_id:<40}"
        f" {manifest.created_at:%Y-%m-%d %H:%M:%S}"
        f" {manifest.label:<20} {summary.battles:>4} 戦"
        f" {summary.wins:>3} 勝 {summary.losses:>3} 敗"
    )


def _cmd_list(_args: argparse.Namespace) -> int:
    generations = list_generations()
    if not generations:
        print(f"世代がありません（{GENERATIONS_DIR}）")
        return 0
    print(f"  {'世代':<40} {'日時':<19} {'ラベル':<20}   戦闘数  勝敗")
    for _path, manifest in generations:
        print(_format_generation(manifest))
    print(
        f"* はピン留め。ピン留めしていない世代は新しい {KEEP_UNPINNED_GENERATIONS} 世代だけ残します。"
    )
    return 0


def _cmd_pin(args: argparse.Namespace) -> int:
    path, _manifest = set_pinned(args.generation, True)
    print(f"ピン留めしました: {path.name}")
    return 0


def _cmd_unpin(args: argparse.Namespace) -> int:
    path, _manifest = set_pinned(args.generation, False)
    print(
        f"ピン留めを外しました: {path.name}"
        f"（次の run で、新しい {KEEP_UNPINNED_GENERATIONS} 世代に入らなければ削除します）"
    )
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    from scripts.simulation.local_sim.run import forbid_database

    # 集計は sim_bench 経由で app を import する。DB は使わない。
    forbid_database()
    from scripts.simulation.local_sim.analysis import (
        build_report,
        format_report,
        write_report,
    )

    path, manifest = find_generation(args.generation)
    report = build_report(path, manifest)
    write_report(path, report)
    if args.format == "json":
        print(report.model_dump_json(indent=2))
    else:
        print(format_report(manifest, report), end="")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    from scripts.simulation.local_sim.run import forbid_database

    forbid_database()
    from scripts.simulation.local_sim.analysis import format_comparison, load_report

    path_a, manifest_a = find_generation(args.generation_a)
    path_b, manifest_b = find_generation(args.generation_b)
    report_a = load_report(path_a, manifest_a)
    report_b = load_report(path_b, manifest_b)
    if args.format == "json":
        print(
            json.dumps(
                {
                    "a": report_a.model_dump(mode="json"),
                    "b": report_b.model_dump(mode="json"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(format_comparison((manifest_a, report_a), (manifest_b, report_b)), end="")
    return 0


def _cmd_log_bench(args: argparse.Namespace) -> int:
    roster = load_roster(args.roster)

    from scripts.simulation.local_sim.run import forbid_database

    forbid_database()
    from scripts.simulation.local_sim.log_bench import (
        LogBenchOptions,
        ParseBenchError,
        format_log_bench,
        run_log_bench,
    )

    options = LogBenchOptions(
        label=args.label,
        formats=args.formats.split(",") if args.formats else None,
        parse=not args.no_parse,
        ndjson_dir=Path(args.keep_ndjson) if args.keep_ndjson else None,
    )
    # 省略した引数は LogBenchOptions の既定値にする。
    for name, value in (
        ("units", args.units),
        ("seed", args.seed),
        ("max_steps", args.steps),
        ("parse_runs", args.runs),
    ):
        if value is not None:
            setattr(options, name, value)
    print(f"ロスター {roster.name} でログを計測します", file=sys.stderr)
    try:
        # エンジンの警告が --format json の出力に混ざらないよう、stderr に出す。
        with contextlib.redirect_stdout(sys.stderr):
            path, result = run_log_bench(
                roster, options, progress=lambda m: print(m, file=sys.stderr)
            )
    except ParseBenchError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(result.model_dump_json(indent=2))
    else:
        print(format_log_bench(result), end="")
    print(f"保存しました: {path}", file=sys.stderr)
    return 0


def _cmd_log_compare(args: argparse.Namespace) -> int:
    from scripts.simulation.local_sim.run import forbid_database

    forbid_database()
    from scripts.simulation.local_sim.log_bench import (
        find_log_bench,
        format_log_comparison,
    )

    a = find_log_bench(args.bench_a)
    b = find_log_bench(args.bench_b)
    print(format_log_comparison(a, b), end="")
    return 0


def _cmd_check_readonly(_args: argparse.Namespace) -> int:
    engine = _connect_readonly()
    print("transaction_read_only = on を確認しました")
    ok = True
    for check in check_writes_rejected(engine):
        mark = "OK" if check.rejected else "NG"
        print(f"  [{mark}] {check.name}: {check.message}")
        ok = ok and check.rejected
    if not ok:
        print("書き込みを拒否できていません。ロールの権限を見直してください。")
        return 1
    print("本番DBへの書き込みが拒否されることを確認しました")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """コマンドライン引数の定義を返す."""
    parser = argparse.ArgumentParser(
        prog="python -m scripts.simulation.local_sim",
        description="本番の機体でバトルをローカル実行するシミュレータ",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser(
        "fetch",
        help="本番DBから参加機体と戦域条件を取得してロスターに保存する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
保存先: {ROSTERS_DIR}/<名前>.json

使用例:
  python -m scripts.simulation.local_sim fetch --pilot user_xxx --npc 7
  python -m scripts.simulation.local_sim fetch --ms <機体ID>:A --ms <機体ID>:A --ace 1 --npc 4
  python -m scripts.simulation.local_sim fetch --pilot user_xxx --npc 9 --theater solomon --minovsky 0.6 --name solomon_test
""",
    )
    fetch.add_argument(
        "--ms",
        action="append",
        default=[],
        metavar="ID[:TEAM]",
        help="参加させる機体ID。:TEAM を付けると同じチーム名の機体と味方になる（複数指定可）",
    )
    fetch.add_argument(
        "--pilot",
        action="append",
        default=[],
        metavar="ID[:TEAM]",
        help="パイロットの出撃機体を参加させる。ID は pilots.id か user_id（複数指定可）",
    )
    fetch.add_argument(
        "--npc",
        type=int,
        default=0,
        metavar="N",
        help="本番の永続化NPCから N 機を選ぶ。足りない分は生成する",
    )
    fetch.add_argument(
        "--ace",
        type=int,
        default=0,
        metavar="N",
        help="エースパイロットをランダムに N 機参加させる",
    )
    fetch.add_argument(
        "--theater",
        default=None,
        metavar="ID",
        help="戦域ID。省略すると戦域なし（宇宙）",
    )
    fetch.add_argument(
        "--minovsky",
        type=float,
        default=None,
        metavar="0-1",
        help="ミノフスキー濃度。省略すると戦域の基準濃度（戦域なしなら 0）",
    )
    fetch.add_argument(
        "--name",
        default=None,
        help="ロスター名。省略すると日時から作る",
    )
    fetch.add_argument(
        "--force", action="store_true", help="同名のロスターを上書きする"
    )
    fetch.set_defaults(func=_cmd_fetch)

    run = sub.add_parser(
        "run",
        help="ロスターの機体でバトルを実行し、1世代として保存する（DB に接続しない）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
保存先: {GENERATIONS_DIR}/<日時>_<ラベル>/
ピン留めしていない世代は新しい {KEEP_UNPINNED_GENERATIONS} 世代だけ残し、古い世代を削除する。

使用例:
  python -m scripts.simulation.local_sim run --roster solomon_test --rounds 20
  python -m scripts.simulation.local_sim run --roster solomon_test --rounds 20 --seed 611 --label before
""",
    )
    run.add_argument(
        "--roster",
        required=True,
        help="ロスター名、またはロスターの JSON ファイルのパス",
    )
    run.add_argument(
        "--rounds", type=int, default=1, metavar="N", help="戦闘数（既定 1）"
    )
    run.add_argument(
        "--steps",
        type=int,
        default=None,
        metavar="N",
        help="1戦の最大ステップ数。省略すると本番バッチの既定値（battle_execution.DEFAULT_MAX_STEPS）",
    )
    run.add_argument(
        "--seed",
        type=int,
        default=None,
        help="1戦目のシード。N 戦目は seed + N - 1。省略するとランダムに決めて記録する",
    )
    run.add_argument(
        "--label",
        default=None,
        help="世代の名前。ディレクトリ名と一覧に使う。省略するとロスター名",
    )
    run.add_argument(
        "--pin",
        action="store_true",
        help="保存する世代をピン留めする。世代管理で削除されない",
    )
    run.set_defaults(func=_cmd_run)

    list_parser = sub.add_parser("list", help="保存した世代を一覧表示する")
    list_parser.set_defaults(func=_cmd_list)

    for name, func, help_text in (
        ("pin", _cmd_pin, "世代をピン留めする。世代管理で削除されない"),
        ("unpin", _cmd_unpin, "世代のピン留めを外す"),
    ):
        pin = sub.add_parser(name, help=help_text)
        pin.add_argument("generation", help="世代ID（前方一致可）、またはラベル")
        pin.set_defaults(func=func)

    report = sub.add_parser(
        "report",
        help="世代の勝敗・戦闘時間・行動分布・機体ごとの撃墜数を集計する",
        description=(
            "世代の battle_NNN.json を集計して表示し、世代ディレクトリの report.json に保存する。"
            " 警告の基準は run_simulation.py bench と同じ（BALANCE_WARN_*）。"
        ),
    )
    report.add_argument("generation", help="世代ID（前方一致可）、またはラベル")
    report.add_argument(
        "--format", choices=["text", "json"], default="text", help="出力形式"
    )
    report.set_defaults(func=_cmd_report)

    compare = sub.add_parser(
        "compare",
        help="2つの世代の集計値を並べて差（B - A）を表示する",
        description=(
            "report.json が無い・古い世代は集計して保存してから比べる。"
            " 戦闘数が違っても比べられるよう、回数は1戦あたりか割合で並べる。"
        ),
    )
    compare.add_argument("generation_a", help="比べる元の世代（A）")
    compare.add_argument("generation_b", help="比べる先の世代（B）")
    compare.add_argument(
        "--format", choices=["text", "json"], default="text", help="出力形式"
    )
    compare.set_defaults(func=_cmd_compare)

    log_bench = sub.add_parser(
        "log-bench",
        help="ロスターの機体で1戦を回し、ログのサイズとパースの負荷を形式ごとに測る",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "全機を個人戦にし、足りない分はロスターの機体を複製して --units 機にする。"
            " 同じロスター・同じ seed なら行数とサイズは同じになる。"
        ),
        epilog="""
保存先: battle_logs/local_sim/log_bench/<日時>_<ラベル>.json
パースの計測には node が要る。無ければパースの計測を省く。

使用例:
  python -m scripts.simulation.local_sim log-bench --roster bench50 --label before
  python -m scripts.simulation.local_sim log-bench --roster small5 --units 50 --formats stored
""",
    )
    log_bench.add_argument(
        "--roster",
        required=True,
        help="ロスター名、またはロスターの JSON ファイルのパス",
    )
    log_bench.add_argument(
        "--units",
        type=int,
        default=None,
        metavar="N",
        help="戦闘に出す機体数。省略すると本番の定員。足りない分はロスターの機体を複製する",
    )
    log_bench.add_argument(
        "--seed",
        type=int,
        default=None,
        help="戦闘のシード。省略すると固定の既定値（log_bench.DEFAULT_SEED）",
    )
    log_bench.add_argument(
        "--steps",
        type=int,
        default=None,
        metavar="N",
        help="最大ステップ数。省略すると本番バッチの既定値",
    )
    log_bench.add_argument(
        "--label",
        default=None,
        help="計測結果の名前。省略するとロスター名",
    )
    log_bench.add_argument(
        "--formats",
        default=None,
        metavar="NAME[,NAME]",
        help="測る形式（stored / draft / draft_no_message）。省略すると全部",
    )
    log_bench.add_argument(
        "--runs",
        type=int,
        default=None,
        metavar="N",
        help="パースを測る回数。中央値を使う",
    )
    log_bench.add_argument(
        "--no-parse", action="store_true", help="Node でのパースの計測を省く"
    )
    log_bench.add_argument(
        "--keep-ndjson",
        default=None,
        metavar="DIR",
        help="形式ごとの NDJSON をこのディレクトリに残す（ブラウザで確かめるとき用）",
    )
    log_bench.add_argument(
        "--format", choices=["text", "json"], default="text", help="出力形式"
    )
    log_bench.set_defaults(func=_cmd_log_bench)

    log_compare = sub.add_parser(
        "log-compare",
        help="2つのログの計測結果を形式ごとに並べ、B / A を表示する",
    )
    log_compare.add_argument(
        "bench_a", help="比べる元（ファイルのパス・ID・その前方一致・ラベル）"
    )
    log_compare.add_argument("bench_b", help="比べる先")
    log_compare.set_defaults(func=_cmd_log_compare)

    check = sub.add_parser(
        "check-readonly",
        help="Read Only の接続で本番DBへの書き込みが拒否されることを確かめる",
    )
    check.set_defaults(func=_cmd_check_readonly)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI を実行して終了コードを返す."""
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (
        ReadOnlyConfigError,
        ValueError,
        FileExistsError,
        FileNotFoundError,
    ) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

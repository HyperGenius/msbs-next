"""ローカルバトルシミュレータの CLI.

backend/ で実行する:
    python -m scripts.simulation.local_sim fetch --pilot <パイロットID> --npc 7
    python -m scripts.simulation.local_sim check-readonly
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import Engine

# python scripts/simulation/local_sim のようにディレクトリを指定して実行したときも import できるようにする。
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.simulation.local_sim.readonly_db import (  # noqa: E402
    ReadOnlyConfigError,
    assert_read_only_session,
    check_writes_rejected,
    use_readonly_database,
)
from scripts.simulation.local_sim.roster import ROSTERS_DIR, save_roster  # noqa: E402


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
    except (ReadOnlyConfigError, ValueError, FileExistsError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

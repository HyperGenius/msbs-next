#!/usr/bin/env python3
"""機体マスターの EN（max_en / en_recovery）を、作成済みの機体へ同期するスクリプト.

既定は読み取りのみで、変わる値を表示する。`--apply` を付けたときだけ書き込む。
何度実行しても結果は同じで、差分が無ければ何も更新しない。

Usage:
    cd backend
    python scripts/maintenance/sync_mobile_suit_en.py                    # 全機体マスターの差分を表示
    python scripts/maintenance/sync_mobile_suit_en.py --master-id gm,zaku_ii
    python scripts/maintenance/sync_mobile_suit_en.py --include-npc      # NPC機も対象にする
    python scripts/maintenance/sync_mobile_suit_en.py --apply
"""

import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlmodel import Session

from app.db import engine
from app.services.mobile_suit_en_sync_service import (
    TARGET_NPC_SKIPPED,
    MobileSuitEnSyncReport,
    sync_mobile_suit_en,
)


def _split(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    return [v.strip() for value in values for v in value.split(",") if v.strip()]


def print_report(report: MobileSuitEnSyncReport) -> None:
    """同期先ごとに、変わる値と件数を表示する."""
    if not report.changes:
        print("変更なし")
        return

    targets = sorted({target for target, *_ in report.changes})
    for target in targets:
        print(f"\n== {target}（{report.updated_rows[target]} 行）")
        rows = sorted(
            (key, count) for key, count in report.changes.items() if key[0] == target
        )
        for (_, master_id, name, old, new), count in rows:
            print(f"  {master_id} / {name}: {old} → {new} ({count}件)")

    if report.updated_rows[TARGET_NPC_SKIPPED]:
        print(
            "\n※ NPC機は更新しません。同期するには --include-npc を付けるか、管理画面で直してください。"
        )


def main() -> None:
    """CLI エントリーポイント."""
    parser = argparse.ArgumentParser(
        description="機体マスターの EN（max_en / en_recovery）を作成済みの機体へ同期する。"
    )
    parser.add_argument(
        "--master-id",
        action="append",
        help="対象の機体マスターID（練習機を含む）。複数指定やカンマ区切りも可。省略すると全件",
    )
    parser.add_argument("--include-npc", action="store_true", help="NPC機も同期する")
    parser.add_argument(
        "--apply", action="store_true", help="書き込む。付けなければ差分の表示のみ"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="--apply の確認プロンプトを省く"
    )
    args = parser.parse_args()

    with Session(engine) as session:
        try:
            report = sync_mobile_suit_en(
                session, _split(args.master_id), include_npc=args.include_npc
            )
        except ValueError as e:
            parser.error(str(e))

        print_report(report)

        if not args.apply:
            session.rollback()
            print(
                "\n読み取りのみで実行しました。書き込むには --apply を付けてください。"
            )
            return
        if not report.has_changes:
            session.rollback()
            return
        if not args.yes:
            answer = input("\nこの内容で書き込みますか？ [y/N]: ")
            if answer.strip().lower() != "y":
                session.rollback()
                print("中止しました。")
                return

        session.commit()
        print("\n書き込みました。")


if __name__ == "__main__":
    main()

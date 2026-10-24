#!/usr/bin/env python3
"""所持している練習機に、練習機の機体マスターIDを設定するスクリプト.

既定は読み取りのみで、設定する件数を表示する。`--apply` を付けたときだけ書き込む。
何度実行しても結果は同じで、設定済みの行は更新しない。

Usage:
    cd backend
    python scripts/maintenance/backfill_trainer_master_id.py          # 設定する件数を表示
    python scripts/maintenance/backfill_trainer_master_id.py --apply
"""

import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlmodel import Session

from app.db import engine
from app.services.trainer_master_backfill_service import (
    TrainerMasterBackfillReport,
    backfill_trainer_master_id,
)


def print_report(report: TrainerMasterBackfillReport) -> None:
    """機体マスターIDごとに、設定する件数を表示する."""
    if not report.has_changes:
        print("変更なし")
        return

    print(f"== mobile_suits.master_mobile_suit_id（{report.updated.total()} 行）")
    for (master_id, name), count in sorted(report.updated.items()):
        print(f"  {name}: NULL → {master_id} ({count}件)")


def main() -> None:
    """CLI エントリーポイント."""
    parser = argparse.ArgumentParser(
        description="所持している練習機に、練習機の機体マスターIDを設定する。"
    )
    parser.add_argument(
        "--apply", action="store_true", help="書き込む。付けなければ件数の表示のみ"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="--apply の確認プロンプトを省く"
    )
    args = parser.parse_args()

    with Session(engine) as session:
        report = backfill_trainer_master_id(session)
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

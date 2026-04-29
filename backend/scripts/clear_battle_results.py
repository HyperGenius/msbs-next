#!/usr/bin/env python3
# backend/scripts/clear_battle_results.py
"""DB上のバトル結果をクリアするスクリプト.

バトルログのスキーマ変更など後方互換性がなくなった際に、
`battle_results` テーブルのデータを削除するために使用します。

Usage:
    python scripts/clear_battle_results.py
    python scripts/clear_battle_results.py --dry-run
    python scripts/clear_battle_results.py --user-id user_xxxx
"""

import argparse
import os
import sys

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlmodel import Session, delete, func, select

from app.db import engine
from app.models.models import BattleResult


def parse_args() -> argparse.Namespace:
    """コマンドライン引数のパース."""
    parser = argparse.ArgumentParser(
        description="DB上のバトル結果（battle_results）を削除します。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/clear_battle_results.py              # 全件削除（確認プロンプトあり）
  python scripts/clear_battle_results.py --dry-run    # 削除件数を確認するだけ（実際には削除しない）
  python scripts/clear_battle_results.py --user-id user_xxxx   # 特定ユーザーの結果のみ削除
  python scripts/clear_battle_results.py --yes        # 確認プロンプトをスキップ
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="削除対象件数を表示するだけで実際には削除しない",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        metavar="USER_ID",
        help="削除対象を絞り込む Clerk User ID（省略時は全件対象）",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="確認プロンプトをスキップして削除を実行する",
    )
    return parser.parse_args()


def main() -> None:
    """メイン処理."""
    args = parse_args()

    with Session(engine) as session:
        # 削除対象件数を確認
        count_stmt = select(func.count()).select_from(BattleResult)
        if args.user_id:
            count_stmt = count_stmt.where(BattleResult.user_id == args.user_id)
        target_count = session.exec(count_stmt).one()

        total_count = session.exec(select(func.count()).select_from(BattleResult)).one()

        print("=" * 60)
        print("バトル結果クリアスクリプト")
        print("=" * 60)
        print(f"テーブル総件数   : {total_count} 件")
        if args.user_id:
            print(f"絞り込み User ID : {args.user_id}")
        print(f"削除対象件数     : {target_count} 件")

        if args.dry_run:
            print("\n[DRY RUN] 実際の削除は行いません。")
            return

        if target_count == 0:
            print("\n削除対象がありません。終了します。")
            return

        # 確認プロンプト
        if not args.yes:
            answer = (
                input(
                    f"\n{target_count} 件のバトル結果を削除します。続行しますか？ [y/N]: "
                )
                .strip()
                .lower()
            )
            if answer not in ("y", "yes"):
                print("キャンセルしました。")
                return

        # 削除実行
        del_stmt = delete(BattleResult)
        if args.user_id:
            del_stmt = del_stmt.where(BattleResult.user_id == args.user_id)

        result = session.exec(del_stmt)  # type: ignore[arg-type]
        session.commit()

        print(f"\n✓ {result.rowcount} 件のバトル結果を削除しました。")


if __name__ == "__main__":
    main()

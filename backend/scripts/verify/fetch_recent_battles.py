#!/usr/bin/env python3
# backend/scripts/verify/fetch_recent_battles.py
"""直近のバトル結果をDBから取得し、検証用にダンプするスクリプト.

シミュレーション結果の妥当性検証のために、`battle_results` テーブルの
直近レコードをコンソール表示 + JSONファイル出力する。

Usage:
    python scripts/verify/fetch_recent_battles.py
    python scripts/verify/fetch_recent_battles.py --limit 50
    python scripts/verify/fetch_recent_battles.py --user-id user_xxxx
    python scripts/verify/fetch_recent_battles.py --with-logs   # battle_logs.logs も含めて出力
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlmodel import Session, select

from app.db import engine
from app.models.models import BattleLogRecord, BattleResult

OUTPUT_DIR = Path(__file__).parent / "output"


def _json_default(obj: Any) -> Any:
    """JSON化できない型（UUID/datetime）を文字列に変換する."""
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数のパース."""
    parser = argparse.ArgumentParser(
        description="直近のバトル結果（battle_results）を取得して表示・出力します。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/verify/fetch_recent_battles.py                    # 直近20件
  python scripts/verify/fetch_recent_battles.py --limit 50         # 直近50件
  python scripts/verify/fetch_recent_battles.py --user-id user_xxxx  # 特定ユーザーのみ
  python scripts/verify/fetch_recent_battles.py --with-logs        # ターンごとの生ログも含める
        """,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        metavar="N",
        help="取得件数（デフォルト: 20）",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        metavar="USER_ID",
        help="絞り込み対象の Clerk User ID（省略時は全ユーザー対象）",
    )
    parser.add_argument(
        "--with-logs",
        action="store_true",
        help="battle_logs.logs（ターンごとの生ログ）も併せて出力する",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="PATH",
        help="出力先JSONパス（省略時は scripts/verify/output/ 配下に自動命名）",
    )
    return parser.parse_args()


def main() -> None:
    """メイン処理."""
    args = parse_args()

    with Session(engine) as session:
        stmt = (
            select(BattleResult)
            .order_by(BattleResult.created_at.desc())
            .limit(args.limit)
        )
        if args.user_id:
            stmt = stmt.where(BattleResult.user_id == args.user_id)
        results = session.exec(stmt).all()

        print("=" * 100)
        print(f"直近バトル結果 取得件数: {len(results)} 件")
        print("=" * 100)

        records: list[dict] = []
        for r in results:
            record = r.model_dump()

            if args.with_logs and r.battle_log_id:
                log = session.get(BattleLogRecord, r.battle_log_id)
                record["logs"] = log.logs if log else None

            records.append(record)

            print(
                f"[{r.created_at.isoformat()}] "
                f"id={r.id} user={r.user_id} "
                f"win_loss={r.win_loss} env={r.environment} "
                f"kills={r.kills} exp={r.exp_gained} credits={r.credits_gained} "
                f"survived={r.player_survived} min_hp%={r.min_hp_percent} "
                f"severity={r.damage_severity} dodge={r.dodge_count} "
                f"tag={r.digest_tag}"
            )

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if args.output:
            output_path = Path(args.output)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = OUTPUT_DIR / f"battles_{timestamp}.json"

        output_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )
        print("\n" + "=" * 100)
        print(f"✓ JSON出力先: {output_path}")
        print("=" * 100)


if __name__ == "__main__":
    main()

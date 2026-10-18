#!/usr/bin/env python3
"""武器マスターの値を、ユーザーデータと機体マスターへ同期するスクリプト.

既定は読み取りのみで、変わる値を表示する。`--apply` を付けたときだけ書き込む。
何度実行しても結果は同じで、差分が無ければ何も更新しない。

Usage:
    cd backend
    python scripts/maintenance/sync_weapon_master.py                      # 全武器の差分を表示
    python scripts/maintenance/sync_weapon_master.py --weapon-id giant_bazooka
    python scripts/maintenance/sync_weapon_master.py --fields max_ammo,en_cost
    python scripts/maintenance/sync_weapon_master.py --weapon-id giant_bazooka --apply
"""

import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlmodel import Session

from app.db import engine
from app.services.weapon_master_sync_service import (
    TARGET_ACE_PILOT,
    WeaponMasterSyncReport,
    sync_weapon_master,
    validate_fields,
)


def _split(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    return [v.strip() for value in values for v in value.split(",") if v.strip()]


def print_report(report: WeaponMasterSyncReport) -> None:
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
        for (_, weapon_id, name, old, new), count in rows:
            print(f"  {weapon_id} / {name}: {old} → {new} ({count}件)")

    if report.updated_rows[TARGET_ACE_PILOT]:
        print(
            "\n※ エースパイロットの武器は更新しません。必要なら管理画面で直してください。"
        )


def main() -> None:
    """CLI エントリーポイント."""
    parser = argparse.ArgumentParser(
        description="武器マスターの値を、ユーザーデータと機体マスターへ同期する。"
    )
    parser.add_argument(
        "--weapon-id",
        action="append",
        help="対象の武器マスターID。複数指定やカンマ区切りも可。省略すると全武器",
    )
    parser.add_argument(
        "--fields",
        action="append",
        help="同期するフィールド（カンマ区切り）。省略すると全スペックフィールドと name",
    )
    parser.add_argument(
        "--apply", action="store_true", help="書き込む。付けなければ差分の表示のみ"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="--apply の確認プロンプトを省く"
    )
    args = parser.parse_args()

    weapon_ids = _split(args.weapon_id)
    fields = _split(args.fields)
    try:
        validate_fields(fields)
    except ValueError as e:
        parser.error(str(e))

    with Session(engine) as session:
        try:
            report = sync_weapon_master(session, weapon_ids, fields)
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
        print(
            "※ backend のマスターデータのキャッシュ（MASTER_DATA_CACHE_TTL_SEC）が"
            "切れるまで、ショップの表示は古い値のままです。"
        )


if __name__ == "__main__":
    main()

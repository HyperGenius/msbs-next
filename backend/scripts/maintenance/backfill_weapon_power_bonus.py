#!/usr/bin/env python3
"""機体強化（weapon_power）の加算値を推定して mobile_suits.weapon_power_bonus に設定するスクリプト.

既定は読み取りのみで、推定結果を表示する。`--apply` を付けたときだけ書き込む。
weapon_power_bonus が 0 の機体だけを対象にするため、2回目以降の実行では何も変えない。

sync_weapon_master.py より先に実行すること。武器マスターの同期は初期装備の
power をマスターの値に戻すため、推定に使う差が消える。

Usage:
    cd backend
    python scripts/maintenance/backfill_weapon_power_bonus.py           # 推定結果を表示
    python scripts/maintenance/backfill_weapon_power_bonus.py --apply
"""

import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlmodel import Session

from app.db import engine
from app.services.weapon_power_bonus_backfill_service import (
    WeaponPowerBonusEstimate,
    apply_weapon_power_bonuses,
    estimate_weapon_power_bonuses,
)


def print_estimates(estimates: list[WeaponPowerBonusEstimate]) -> None:
    """機体ごとに、推定した加算値とスロットごとの差を表示する."""
    if not estimates:
        print("加算値を設定する機体はありません")
        return

    for e in estimates:
        diffs = ", ".join("?" if d is None else str(d) for d in e.slot_diffs)
        mark = "" if e.is_consistent else "  ※差がスロット間で揃っていません"
        print(f"{e.mobile_suit_id} {e.name} (user: {e.user_id})")
        print(f"  加算値: {e.bonus}  スロットごとの差: [{diffs}]{mark}")
    print(f"\n対象: {len(estimates)} 機")


def main() -> None:
    """CLI エントリーポイント."""
    parser = argparse.ArgumentParser(
        description="機体強化の加算値を推定して mobile_suits.weapon_power_bonus に設定する。"
    )
    parser.add_argument(
        "--apply", action="store_true", help="書き込む。付けなければ推定結果の表示のみ"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="--apply の確認プロンプトを省く"
    )
    args = parser.parse_args()

    with Session(engine) as session:
        estimates = estimate_weapon_power_bonuses(session)
        print_estimates(estimates)

        if not args.apply:
            print(
                "\n読み取りのみで実行しました。書き込むには --apply を付けてください。"
            )
            return
        if not estimates:
            return
        if not args.yes:
            answer = input("\nこの内容で書き込みますか？ [y/N]: ")
            if answer.strip().lower() != "y":
                print("中止しました。")
                return

        apply_weapon_power_bonuses(session, estimates)
        session.commit()
        print("\n書き込みました。")


if __name__ == "__main__":
    main()

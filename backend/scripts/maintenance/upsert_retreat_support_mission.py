#!/usr/bin/env python3
"""撤退支援の作戦マスター（missions.id=4）を DB に追加・更新するスクリプト.

既定は読み取りのみで、変わる項目を表示する。`--apply` を付けたときだけ書き込む。
何度実行しても結果は同じで、差分が無ければ何も更新しない。
本番 DB には、差分を確認して承認を得てから `--apply` で実行すること。

Usage:
    cd backend
    uv run python scripts/maintenance/upsert_retreat_support_mission.py
    uv run python scripts/maintenance/upsert_retreat_support_mission.py --apply
    uv run python scripts/maintenance/upsert_retreat_support_mission.py --apply --inactive
"""

import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlmodel import Session

from app.db import engine
from app.models.models import Mission
from app.services.retreat_support_mission import build_retreat_support_mission

_FIELDS = (
    "name",
    "difficulty",
    "description",
    "environment",
    "special_effects",
    "enemy_config",
    "objective",
    "allies_config",
    "layout",
    "is_active",
)


def main() -> None:
    """差分を表示し、`--apply` のときだけ書き込む."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="DB に書き込む")
    parser.add_argument(
        "--inactive",
        action="store_true",
        help="is_active を false にする（定期バトルのエントリーに出さない）",
    )
    args = parser.parse_args()

    desired = build_retreat_support_mission()
    if args.inactive:
        desired.is_active = False

    with Session(engine) as session:
        current = session.get(Mission, desired.id)
        if current is None:
            print(f"追加: Mission {desired.id} {desired.name}")
            if args.apply:
                session.add(desired)
        else:
            changed = [f for f in _FIELDS if getattr(current, f) != getattr(desired, f)]
            if not changed:
                print("変更なし")
                return
            print(f"更新: Mission {desired.id} {current.name} → {changed}")
            if args.apply:
                for field in changed:
                    setattr(current, field, getattr(desired, field))
                session.add(current)
        if args.apply:
            session.commit()
            print("書き込みました")
        else:
            print("（--apply を付けると書き込みます）")


if __name__ == "__main__":
    main()

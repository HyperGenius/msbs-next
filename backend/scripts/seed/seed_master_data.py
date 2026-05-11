#!/usr/bin/env python
"""マスターデータシードスクリプト.

mobile_suits.json / weapons.json から master_mobile_suits / master_weapons
テーブルへデータを投入する。べき等に実行可能（ON CONFLICT DO NOTHING）。

Usage:
    python scripts/seed/seed_master_data.py [--force]

Options:
    --force     既存レコードを上書きする（管理画面で変更済みのデータも上書き）。
                デフォルトは既存レコードをスキップ（管理画面変更を保護する）。

Environment:
    DATABASE_URL (または NEON_DATABASE_URL): 接続先データベースのURL
                                             デフォルト: sqlite:///./dev.db
"""

import argparse
import json
import os
import sys
from pathlib import Path

# プロジェクトルートを Python パスに追加
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from datetime import UTC, datetime

from sqlmodel import Session, create_engine, select


def _get_engine():
    """DATABASE_URL 環境変数からエンジンを生成する."""
    url = os.environ.get("DATABASE_URL") or os.environ.get(
        "NEON_DATABASE_URL", "sqlite:///./dev.db"
    )
    return create_engine(url)


def seed_master_data(force: bool = False) -> dict[str, int]:
    """マスターデータを DB へ投入する.

    Args:
        force: True の場合、既存レコードを上書きする

    Returns:
        dict: 挿入/スキップ件数
    """
    # モデルは engine 生成後にインポート（循環インポート回避）
    from app.models.models import MasterMobileSuit, MasterWeapon

    data_dir = _ROOT / "data" / "master"
    engine = _get_engine()

    from sqlmodel import SQLModel

    SQLModel.metadata.create_all(engine)

    inserted_ms = 0
    skipped_ms = 0
    inserted_w = 0
    skipped_w = 0

    with Session(engine) as session:
        # === mobile_suits ===
        ms_json_path = data_dir / "mobile_suits.json"
        if not ms_json_path.exists():
            print(f"[WARNING] {ms_json_path} が見つかりません。スキップします。")
        else:
            ms_data = json.loads(ms_json_path.read_text(encoding="utf-8"))
            for item in ms_data:
                item_id = item["id"]
                existing = session.get(MasterMobileSuit, item_id)

                if existing is not None and not force:
                    skipped_ms += 1
                    continue

                specs = dict(item["specs"])

                if existing is not None:
                    # --force: 既存レコードを上書き
                    existing.name = item["name"]
                    existing.price = item["price"]
                    existing.faction = item.get("faction", "")
                    existing.description = item["description"]
                    existing.specs = specs
                    existing.updated_at = datetime.now(UTC)
                    session.add(existing)
                else:
                    record = MasterMobileSuit(
                        id=item_id,
                        name=item["name"],
                        price=item["price"],
                        faction=item.get("faction", ""),
                        description=item["description"],
                        specs=specs,
                    )
                    session.add(record)
                    inserted_ms += 1

        # === weapons ===
        weapons_json_path = data_dir / "weapons.json"
        if not weapons_json_path.exists():
            print(f"[WARNING] {weapons_json_path} が見つかりません。スキップします。")
        else:
            weapons_data = json.loads(weapons_json_path.read_text(encoding="utf-8"))
            for item in weapons_data:
                item_id = item["id"]
                existing = session.get(MasterWeapon, item_id)

                if existing is not None and not force:
                    skipped_w += 1
                    continue

                weapon_dict = dict(item["weapon"])

                if existing is not None:
                    existing.name = item["name"]
                    existing.price = item["price"]
                    existing.description = item["description"]
                    existing.weapon = weapon_dict
                    existing.updated_at = datetime.now(UTC)
                    session.add(existing)
                else:
                    record = MasterWeapon(
                        id=item_id,
                        name=item["name"],
                        price=item["price"],
                        description=item["description"],
                        weapon=weapon_dict,
                    )
                    session.add(record)
                    inserted_w += 1

        session.commit()

    return {
        "mobile_suits_inserted": inserted_ms,
        "mobile_suits_skipped": skipped_ms,
        "weapons_inserted": inserted_w,
        "weapons_skipped": skipped_w,
    }


def main() -> None:
    """コマンドラインエントリーポイント."""
    parser = argparse.ArgumentParser(
        description="マスターデータ (mobile_suits / weapons) を DB へシードする"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="既存レコードを上書きする（デフォルトはスキップ）",
    )
    args = parser.parse_args()

    print(f"[INFO] シード開始 (force={args.force})")
    result = seed_master_data(force=args.force)
    print(f"[INFO] mobile_suits: {result['mobile_suits_inserted']} 件挿入, "
          f"{result['mobile_suits_skipped']} 件スキップ")
    print(f"[INFO] weapons: {result['weapons_inserted']} 件挿入, "
          f"{result['weapons_skipped']} 件スキップ")
    print("[INFO] シード完了")


if __name__ == "__main__":
    main()

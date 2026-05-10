#!/usr/bin/env python3
"""Pilot.inventory / MobileSuit.weapons を player_weapons テーブルへ移行するスクリプト.

べき等（再実行しても二重挿入されない）になっています。
実行前に NEON_DATABASE_URL 環境変数を設定してください。

Usage:
    cd backend
    NEON_DATABASE_URL="postgresql://..." python scripts/maintenance/migrate_weapon_instances.py
"""

import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlmodel import Session, SQLModel, create_engine, select

from app.core.gamedata import get_weapon_listing_by_id
from app.models.models import MobileSuit, Pilot, PlayerWeapon


def _get_weapon_id_from_obj(weapon: object) -> str | None:
    """武器オブジェクト（またはdict）からIDを取得する."""
    if hasattr(weapon, "id"):
        return weapon.id  # type: ignore[union-attr]
    if isinstance(weapon, dict):
        return weapon.get("id")
    return None


def _get_weapon_snapshot_from_obj(weapon: object) -> dict:
    """武器オブジェクト（またはdict）からスナップショットを取得する."""
    if hasattr(weapon, "model_dump"):
        return weapon.model_dump()  # type: ignore[union-attr]
    if isinstance(weapon, dict):
        return weapon
    return {}


def _build_equipped_slots(
    session: Session, user_id: str
) -> dict[str, list[tuple[uuid.UUID, int]]]:
    """ユーザーの機体に装備された武器スロットのマッピングを構築する."""
    ms_stmt = select(MobileSuit).where(MobileSuit.user_id == user_id)
    all_ms = session.exec(ms_stmt).all()
    equipped_slots: dict[str, list[tuple[uuid.UUID, int]]] = {}
    for ms in all_ms:
        for slot_idx, w in enumerate(ms.weapons or []):
            w_id = _get_weapon_id_from_obj(w)
            if w_id:
                equipped_slots.setdefault(w_id, []).append((ms.id, slot_idx))
    return equipped_slots


def migrate(session: Session) -> None:
    """既存データを player_weapons テーブルへ移行する."""
    print("=== PlayerWeapon データ移行スクリプト ===")

    # 既存の player_weapons を取得（べき等チェック用）
    existing_stmt = select(PlayerWeapon)
    existing_pws = session.exec(existing_stmt).all()
    if existing_pws:
        print(
            f"既に {len(existing_pws)} 件の PlayerWeapon が存在します。スキップします。"
        )
        print(
            "  ※ 完全な再実行が必要な場合は先に player_weapons テーブルを空にしてください。"
        )
        return

    # 全パイロットを取得
    all_pilots = session.exec(select(Pilot)).all()
    print(f"パイロット数: {len(all_pilots)}")

    total_inserted = 0

    for pilot in all_pilots:
        inventory = pilot.inventory or {}
        user_id = pilot.user_id

        if not inventory:
            continue

        print(f"\nパイロット: {pilot.name} ({user_id})")
        print(f"  インベントリ: {inventory}")

        # 機体スロットのマッピングを構築: {weapon_id: [(ms_id, slot_index), ...]}
        equipped_slots = _build_equipped_slots(session, user_id)

        print(f"  装備済みスロット: {equipped_slots}")

        # inventory の各武器IDについて count 件の PlayerWeapon を生成
        for weapon_id, count in inventory.items():
            # weapons.json からスナップショットを取得
            listing = get_weapon_listing_by_id(weapon_id)
            if listing:
                weapon_obj = listing["weapon"]
                base_snapshot = weapon_obj.model_dump()
            else:
                # weapons.json に存在しない場合はスキップせずそのまま保持
                print(
                    f"  警告: weapons.json に {weapon_id} が見つかりません。空スナップショットで保持します。"
                )
                base_snapshot = {"id": weapon_id}

            # 装備済みスロットのリストを取得（先着順に割り当て）
            slots_for_weapon = equipped_slots.get(weapon_id, [])

            for i in range(count):
                if i < len(slots_for_weapon):
                    equipped_ms_id, equipped_slot = slots_for_weapon[i]
                else:
                    equipped_ms_id = None
                    equipped_slot = None

                pw = PlayerWeapon(
                    user_id=user_id,
                    master_weapon_id=weapon_id,
                    base_snapshot=base_snapshot,
                    custom_stats={},
                    equipped_ms_id=equipped_ms_id,
                    equipped_slot=equipped_slot,
                    acquired_at=datetime.now(UTC),
                )
                session.add(pw)
                total_inserted += 1
                print(
                    f"  INSERT PlayerWeapon: weapon_id={weapon_id}, equipped_ms_id={equipped_ms_id}, slot={equipped_slot}"
                )

    session.commit()
    print(f"\n✅ 移行完了: {total_inserted} 件の PlayerWeapon を INSERT しました。")


def main() -> None:
    """メイン処理."""
    db_url = os.environ.get("NEON_DATABASE_URL")
    if not db_url:
        print("エラー: NEON_DATABASE_URL 環境変数が設定されていません。")
        sys.exit(1)

    engine = create_engine(db_url)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        migrate(session)


if __name__ == "__main__":
    main()

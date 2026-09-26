#!/usr/bin/env python
"""ドロップテーブルシードスクリプト.

ドロップテーブルの初期データを drop_tables / drop_table_entries へ投入する。
べき等に実行できる。既存のテーブル・エントリーは、デフォルトでは変更しない。
設計図マスターが無い設計図のエントリーは投入しない。

Usage:
    python scripts/seed/seed_drop_tables.py [--force] [--dry-run]

Options:
    --force     既存のテーブル・エントリーの設定を、このスクリプトの値で上書きする。
    --dry-run   投入内容を表示するだけで、コミットしない。

Environment:
    DATABASE_URL (または NEON_DATABASE_URL): 接続先データベースのURL
"""

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, create_engine, select

# プロジェクトルートを Python パスに追加
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

# .env を読み込む（backend/.env）
load_dotenv(_ROOT / ".env")

from app.models.models import (  # noqa: E402
    DropScopeType,
    DropTable,
    DropTableEntry,
    MasterBlueprint,
)
from app.services.drop_service import BATCH_SCOPE_KEY  # noqa: E402


@dataclass(frozen=True)
class EntrySeed:
    """投入するエントリー."""

    blueprint_id: str
    weight: int
    requires_win: bool = False


@dataclass(frozen=True)
class TableSeed:
    """投入するドロップテーブル."""

    scope_type: DropScopeType
    scope_key: str
    name: str
    drop_rate: float
    win_rate_multiplier: float
    entries: tuple[EntrySeed, ...]


# 値は運用しながら admin-tool で調整する前提の初期値。
DROP_TABLE_SEEDS: tuple[TableSeed, ...] = (
    TableSeed(
        scope_type=DropScopeType.BATCH,
        scope_key=BATCH_SCOPE_KEY,
        name="定期バトル",
        drop_rate=0.3,
        win_rate_multiplier=1.5,
        entries=(
            EntrySeed("mobile_suit:dom", weight=3),
            EntrySeed("mobile_suit:zaku_ii_f", weight=3),
            EntrySeed("mobile_suit:gelgoog", weight=1, requires_win=True),
            EntrySeed("mobile_suit:gundam", weight=1, requires_win=True),
        ),
    ),
)


def _get_engine():
    """DATABASE_URL 環境変数からエンジンを生成する."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL または NEON_DATABASE_URL が設定されていません")
    return create_engine(url)


def _upsert_table(session: Session, seed: TableSeed, force: bool) -> DropTable:
    table = session.exec(
        select(DropTable).where(
            DropTable.scope_type == seed.scope_type.value,
            DropTable.scope_key == seed.scope_key,
        )
    ).first()
    if table is None:
        table = DropTable(
            scope_type=seed.scope_type.value,
            scope_key=seed.scope_key,
            name=seed.name,
            drop_rate=seed.drop_rate,
            win_rate_multiplier=seed.win_rate_multiplier,
        )
        print(f"[INFO] テーブル作成: {seed.name}")
    elif force:
        table.name = seed.name
        table.drop_rate = seed.drop_rate
        table.win_rate_multiplier = seed.win_rate_multiplier
        table.updated_at = datetime.now(UTC)
        print(f"[INFO] テーブル上書き: {seed.name}")
    else:
        print(f"[INFO] テーブルは既存のためスキップ: {seed.name}")
    session.add(table)
    session.flush()
    return table


def seed_drop_tables(session: Session, force: bool = False) -> dict[str, int]:
    """ドロップテーブルの初期データを投入する.

    コミットは呼び出し側で行う。

    Returns:
        投入・上書き・スキップしたエントリーの件数。
    """
    counts = {"inserted": 0, "updated": 0, "skipped": 0, "missing_blueprint": 0}
    for seed in DROP_TABLE_SEEDS:
        table = _upsert_table(session, seed, force)
        for entry_seed in seed.entries:
            if session.get(MasterBlueprint, entry_seed.blueprint_id) is None:
                print(f"[WARNING] 設計図マスターが無い: {entry_seed.blueprint_id}")
                counts["missing_blueprint"] += 1
                continue

            entry = session.exec(
                select(DropTableEntry).where(
                    DropTableEntry.drop_table_id == table.id,
                    DropTableEntry.blueprint_id == entry_seed.blueprint_id,
                )
            ).first()
            if entry is None:
                entry = DropTableEntry(
                    drop_table_id=table.id, blueprint_id=entry_seed.blueprint_id
                )
                counts["inserted"] += 1
            elif force:
                counts["updated"] += 1
            else:
                counts["skipped"] += 1
                continue

            entry.weight = entry_seed.weight
            entry.requires_win = entry_seed.requires_win
            session.add(entry)
            print(
                f"[INFO]   {entry_seed.blueprint_id}: 重み {entry_seed.weight}"
                + ("・勝利時のみ" if entry_seed.requires_win else "")
            )
    return counts


def main() -> None:
    """コマンドラインエントリーポイント."""
    parser = argparse.ArgumentParser(description="ドロップテーブルを DB へシードする")
    parser.add_argument(
        "--force",
        action="store_true",
        help="既存のテーブル・エントリーを上書きする（デフォルトはスキップ）",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="コミットせずに投入内容を表示する"
    )
    args = parser.parse_args()

    print(f"[INFO] シード開始 (force={args.force}, dry_run={args.dry_run})")
    with Session(_get_engine()) as session:
        counts = seed_drop_tables(session, force=args.force)
        if args.dry_run:
            session.rollback()
            print("[INFO] dry-run のためコミットしない")
        else:
            session.commit()
    print(
        f"[INFO] エントリー: {counts['inserted']} 件挿入, {counts['updated']} 件上書き, "
        f"{counts['skipped']} 件スキップ, 設計図マスター無し {counts['missing_blueprint']} 件"
    )
    print("[INFO] シード完了")


if __name__ == "__main__":
    main()

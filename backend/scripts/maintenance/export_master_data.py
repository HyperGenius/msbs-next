#!/usr/bin/env python
"""DB のマスターデータを JSON に書き出す.

6つのマスター（機体・武器・エースパイロット・技術・環境タイプ・戦域）と
設計図マスターを、`seed_master_data.py --data-dir` が読める形で書き出す。
既定では本番 DB に読み取り専用で接続する（`NEON_READONLY_DATABASE_URL`）。

書き出したファイルは Git に入れない。正本は DB であり、Git に残すと DB とずれるため。

Usage:
    python scripts/maintenance/export_master_data.py
    python scripts/maintenance/export_master_data.py --output-dir /tmp/master
    python scripts/maintenance/export_master_data.py --database-url sqlite:///./dev.db
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.master_data import (  # noqa: E402
    EXPORT_DIR,
    MasterData,
    collect_master_data,
    load_master_data_from_readonly_db,
    write_master_dir,
)
from scripts.simulation.local_sim.readonly_db import ReadOnlyConfigError  # noqa: E402


def _collect_from_url(url: str) -> MasterData:
    from sqlmodel import Session, create_engine

    with Session(create_engine(url)) as session:
        return collect_master_data(session)


def main() -> int:
    """書き出して件数を表示する."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=EXPORT_DIR,
        help=f"出力先（既定: {EXPORT_DIR.relative_to(EXPORT_DIR.parents[2])}）",
    )
    parser.add_argument(
        "--database-url",
        help="本番 DB の代わりに読む DB の URL（ローカルの DB など）",
    )
    args = parser.parse_args()

    try:
        if args.database_url:
            data = _collect_from_url(args.database_url)
        else:
            data = load_master_data_from_readonly_db()
    except ReadOnlyConfigError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1

    for path in write_master_dir(data, args.output_dir):
        print(f"[INFO] {path}: {len(data[path.stem])} 件")
    return 0


if __name__ == "__main__":
    sys.exit(main())

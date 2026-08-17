#!/usr/bin/env python3
# backend/scripts/maintenance/offload_battle_logs_to_gcs.py
"""battle_logs.logs をCloud Storageへオフロードするスクリプト（Issue #493）.

以下2つの用途を兼ねる（どちらも「gcs_path が未設定の行を対象にアップロードし、
成功したら gcs_path をセットして logs を空にする」という同一の処理のため）:

1. 既存データのバックフィル: 本Issue導入前に作成された全行をGCSへ移行する
2. 失敗分の再試行: バトル終了時の非同期オフロード（`main.py`の`BackgroundTasks`）が
   失敗・未実施のまま残った行を拾い直す（Cloud Schedulerなどで定期実行する想定）

`--restore-archived` を指定すると、#489のJSONBマイグレーションで`ARCHIVE_SIZE_THRESHOLD_BYTES`
超のため退避・削除された行（`backend/scripts/verify/output/battle_logs_jsonb_migration_backup/`）
をこのマシンのローカルバックアップから復元してGCSへアップロードする、別モードで動作する
（詳細は該当オプションのヘルプを参照）。

Usage:
    python scripts/maintenance/offload_battle_logs_to_gcs.py --dry-run
    python scripts/maintenance/offload_battle_logs_to_gcs.py --limit 50
    python scripts/maintenance/offload_battle_logs_to_gcs.py --restore-archived --dry-run
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlmodel import Session, func, select  # noqa: E402

from app.db import engine  # noqa: E402
from app.models.models import BattleLogRecord, BattleResult  # noqa: E402
from app.services.battle_log_storage_service import (  # noqa: E402
    offload_battle_log_to_gcs,
    upload_ndjson_text,
)

# 1回のDB往復で取得するIDの件数。ID自体は軽量だが、対応するlogs列は最大で
# 数十MB/行になり得る（#489の記録ではテキスト換算86MB）ため、IDだけを
# ページング取得し、logs本体は1行ずつロードして処理する（Copilotレビュー指摘、
# PR #495）。まとめて`.all()`すると全行分のlogsが同時にメモリへ乗ってしまう。
_ID_PAGE_SIZE = 100

_BACKUP_DIR = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "verify"
    / "output"
    / "battle_logs_jsonb_migration_backup"
)


def parse_args() -> argparse.Namespace:
    """コマンドライン引数のパース."""
    parser = argparse.ArgumentParser(
        description="battle_logs.logs をCloud Storageへオフロードします。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/maintenance/offload_battle_logs_to_gcs.py --dry-run     # 対象件数を確認するだけ
  python scripts/maintenance/offload_battle_logs_to_gcs.py --limit 50    # 先頭50件のみ処理
  python scripts/maintenance/offload_battle_logs_to_gcs.py               # 全件処理（確認プロンプトあり）
  python scripts/maintenance/offload_battle_logs_to_gcs.py --restore-archived --dry-run
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="対象件数を表示するだけで実際にはアップロード・更新しない",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="1回の実行で処理する件数の上限（省略時は全件）",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="確認プロンプトをスキップして実行する",
    )
    parser.add_argument(
        "--restore-archived",
        action="store_true",
        help=(
            "gcs_path未設定の通常行ではなく、#489で退避・削除された巨大行を"
            "ローカルバックアップ（本スクリプト実行マシン上に残っている場合のみ）から"
            "復元してGCSへアップロードするモードに切り替える。BattleLogRecord行は"
            "元のIDで再作成するが、battle_results.battle_log_id の再リンクは行わない"
            "（退避時に参照元のbattle_results.idを記録していないため、どの行が"
            "参照していたか機械的には特定できない。mission_idまたはroom_idが"
            "一致するcandidateを表示するので手動で確認・更新すること）"
        ),
    )
    return parser.parse_args()


def _confirm_backfill(dry_run: bool, limit: int | None, skip_confirm: bool) -> bool:
    """対象件数の表示・dry-run判定・確認プロンプトを行う.

    Returns:
        実際にオフロード処理へ進んでよい場合True。
    """
    with Session(engine) as session:
        count_stmt = (
            select(func.count())
            .select_from(BattleLogRecord)
            .where(
                BattleLogRecord.gcs_path.is_(None)  # type: ignore[union-attr]
            )
        )
        target_count = session.exec(count_stmt).one()

    print("=" * 60)
    print("バトルログ Cloud Storage オフロードスクリプト")
    print("=" * 60)
    print(f"未オフロード件数: {target_count} 件")
    if limit is not None:
        print(f"今回処理する上限: {limit} 件")

    if target_count == 0:
        print("\n対象がありません。終了します。")
        return False

    if dry_run:
        print("\n[DRY RUN] 実際のアップロードは行いません。")
        return False

    if skip_confirm:
        return True

    answer = (
        input(f"\n{target_count} 件をGCSへオフロードします。続行しますか？ [y/N]: ")
        .strip()
        .lower()
    )
    if answer not in ("y", "yes"):
        print("キャンセルしました。")
        return False
    return True


def _run_backfill(dry_run: bool, limit: int | None, skip_confirm: bool) -> None:
    if not _confirm_backfill(dry_run, limit, skip_confirm):
        return

    succeeded = 0
    failed = 0
    processed = 0
    while limit is None or processed < limit:
        page_size = (
            _ID_PAGE_SIZE if limit is None else min(_ID_PAGE_SIZE, limit - processed)
        )
        with Session(engine) as session:
            id_stmt = (
                select(BattleLogRecord.id)
                .where(BattleLogRecord.gcs_path.is_(None))  # type: ignore[union-attr]
                .limit(page_size)
            )
            ids = session.exec(id_stmt).all()

        if not ids:
            break

        for log_id in ids:
            # logs本体はこの1行分だけをロードする（ページ全体をまとめて
            # ロードしない）。offload_battle_log_to_gcs()内部でも別途
            # セッションを開くため往復は増えるが、大規模行でのOOMを避ける
            # ことを優先する。
            with Session(engine) as session:
                record = session.get(BattleLogRecord, log_id)
            if record is None:
                continue

            if offload_battle_log_to_gcs(log_id, record.logs):
                succeeded += 1
            else:
                failed += 1
                print(f"  ✗ 失敗: {log_id}（次回実行で再試行されます）")

        processed += len(ids)

    print(f"\n完了: 成功 {succeeded} 件 / 失敗 {failed} 件")


def _run_restore_archived(dry_run: bool, skip_confirm: bool) -> None:
    manifest_path = _BACKUP_DIR / "manifest.json"
    if not manifest_path.exists():
        print(f"バックアップmanifestが見つかりません: {manifest_path}")
        print(
            "このマシンに#489マイグレーション実行時のバックアップが残っていない場合、"
        )
        print("該当バトルのリプレイは復旧不能です。")
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print("=" * 60)
    print("退避済みバトルログ 復元スクリプト")
    print("=" * 60)
    print(f"バックアップ対象: {len(manifest)} 件")

    if dry_run:
        for entry in manifest:
            print(f"  - {entry['id']} ({entry['logs_size_bytes']} bytes)")
        print("\n[DRY RUN] 実際の復元は行いません。")
        return

    if not skip_confirm:
        answer = (
            input(
                f"\n{len(manifest)} 件を復元してGCSへアップロードします。続行しますか？ [y/N]: "
            )
            .strip()
            .lower()
        )
        if answer not in ("y", "yes"):
            print("キャンセルしました。")
            return

    with Session(engine) as session:
        for entry in manifest:
            _restore_one_archived_entry(session, entry)


def _restore_one_archived_entry(session: Session, entry: dict) -> None:
    """バックアップmanifestの1件分を復元し、GCSへアップロードする.

    manifest（JSON）から読んだ `id`/`room_id`/`created_at` は文字列のため、
    `BattleLogRecord`のフィールド型（UUID/datetime）へ明示的に変換してから使う
    （Copilotレビュー指摘、PR #495）。再実行時に同じIDの行が既に復元済みの場合は
    安全にスキップする（INSERTの主キー重複エラーを避けるため）。

    `battle_results.battle_log_id` の再リンクは行わない（誤った行を書き換える
    リスクの方が、リプレイ不能のまま残るリスクより大きいため）。代わりに
    条件が一致する候補を参考表示するのみに留める。
    """
    log_id = uuid.UUID(entry["id"])

    if session.get(BattleLogRecord, log_id) is not None:
        print(f"  - スキップ（復元済み）: {log_id}")
        return

    backup_file = _BACKUP_DIR / entry["backup_file"]
    if not backup_file.exists():
        print(f"  ✗ バックアップファイルが見つかりません: {backup_file}")
        return

    # バックアップは `logs::text`（JSON配列テキスト）のまま保存されている
    # （#489の退避処理はNDJSON化前の生カラム値をそのままダンプしたため）。
    # GCS側の契約であるNDJSONへ変換してからアップロードする。
    logs_array = json.loads(backup_file.read_text(encoding="utf-8"))
    ndjson_text = "\n".join(json.dumps(item, ensure_ascii=False) for item in logs_array)
    if logs_array:
        ndjson_text += "\n"

    gcs_path = upload_ndjson_text(log_id, ndjson_text)

    record = BattleLogRecord(
        id=log_id,
        room_id=uuid.UUID(entry["room_id"]) if entry.get("room_id") else None,
        mission_id=entry["mission_id"],
        created_at=datetime.fromisoformat(entry["created_at"]),
        logs=[],
        gcs_path=gcs_path,
    )
    session.add(record)
    session.commit()
    print(f"  ✓ 復元・アップロード完了: {log_id}")

    candidates = _find_relink_candidates(session, entry)
    if candidates:
        print(
            "    再リンク候補（battle_log_id IS NULL かつ同条件、手動で確認）: "
            f"{[str(c[0]) for c in candidates]}"
        )


def _find_relink_candidates(session: Session, entry: dict) -> list:
    """`battle_results.battle_log_id` の再リンク先候補を検索する（参考表示用）."""
    stmt = select(BattleResult.id, BattleResult.created_at).where(
        BattleResult.battle_log_id.is_(None)  # type: ignore[union-attr]
    )
    if entry.get("mission_id") is not None:
        stmt = stmt.where(BattleResult.mission_id == entry["mission_id"])
    elif entry.get("room_id") is not None:
        stmt = stmt.where(BattleResult.room_id == uuid.UUID(entry["room_id"]))
    return list(session.exec(stmt).all())


def main() -> None:
    """メイン処理."""
    args = parse_args()
    if args.restore_archived:
        _run_restore_archived(dry_run=args.dry_run, skip_confirm=args.yes)
    else:
        _run_backfill(dry_run=args.dry_run, limit=args.limit, skip_confirm=args.yes)


if __name__ == "__main__":
    main()

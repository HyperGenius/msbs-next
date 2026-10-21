"""機体マスターの EN（max_en / en_recovery）を、作成済みの機体へ同期する.

機体のスペックは購入・作成時に機体マスターからコピーされるため、
機体マスターの EN を変えても作成済みの ``mobile_suits`` は古い値のままになる。
対応付けには ``mobile_suits.master_mobile_suit_id`` を使う。

- プレイヤー機: 同期する
- NPC 機（``user_id`` が ``npc-`` で始まる）: 管理画面で機体ごとに調整するため、
  ``include_npc`` を指定したときだけ同期する
- エース機の雛形（``ace_pilots.mobile_suit``）: エース専用の値を持たせるため同期しない

EN は機体強化の対象ではないので、機体マスターの値でそのまま上書きしてよい。
"""

from collections import Counter
from dataclasses import dataclass, field

from sqlmodel import Session, col, select

from app.models.models import MasterMobileSuit, MasterMobileSuitSpec, MobileSuit

SYNCABLE_FIELDS: tuple[str, ...] = ("max_en", "en_recovery")

NPC_USER_ID_PREFIX = "npc-"

TARGET_PLAYER = "mobile_suits（プレイヤー機）"
TARGET_NPC = "mobile_suits（NPC機）"
TARGET_NPC_SKIPPED = "mobile_suits（NPC機・対象外）"


@dataclass
class MobileSuitEnSyncReport:
    """同期で変わる（変わった）値の集計."""

    # (同期先, 機体マスターID, フィールド, 変更前, 変更後) → 件数
    changes: Counter[tuple[str, str, str, int, int]] = field(default_factory=Counter)
    # 同期先 → 更新した行数
    updated_rows: Counter[str] = field(default_factory=Counter)

    @property
    def has_changes(self) -> bool:
        """更新する行が1つでもあるか."""
        return any(
            target != TARGET_NPC_SKIPPED and count > 0
            for target, count in self.updated_rows.items()
        )


def _load_masters(
    session: Session, master_ids: list[str] | None
) -> dict[str, dict[str, int]]:
    stmt = select(MasterMobileSuit)
    if master_ids:
        stmt = stmt.where(col(MasterMobileSuit.id).in_(master_ids))
    # specs にキーが無い機体マスターは既定値として扱う（バトルで使われる値と同じ）
    defaults = {
        name: MasterMobileSuitSpec.model_fields[name].get_default()
        for name in SYNCABLE_FIELDS
    }
    masters = {
        mms.id: {
            name: (mms.specs or {}).get(name, defaults[name])
            for name in SYNCABLE_FIELDS
        }
        for mms in session.exec(stmt).all()
    }
    missing = sorted(set(master_ids or []) - masters.keys())
    if missing:
        raise ValueError(f"機体マスターに無いIDです: {', '.join(missing)}")
    return masters


def _target(ms: MobileSuit) -> str | None:
    if ms.user_id is None:
        # マッチング時に作られるエース機のコピーなど。編集対象にしない
        return None
    if ms.user_id.startswith(NPC_USER_ID_PREFIX):
        return TARGET_NPC
    return TARGET_PLAYER


def sync_mobile_suit_en(
    session: Session,
    master_ids: list[str] | None = None,
    include_npc: bool = False,
) -> MobileSuitEnSyncReport:
    """機体マスターの EN を作成済みの機体へ反映し、変わった値を返す.

    commit はしない。呼び出し元が結果を見て commit か rollback を選ぶ。
    """
    report = MobileSuitEnSyncReport()

    with session.no_autoflush:
        masters = _load_masters(session, master_ids)
        if not masters:
            return report

        stmt = select(MobileSuit).where(
            col(MobileSuit.master_mobile_suit_id).in_(list(masters))
        )
        for ms in session.exec(stmt).all():
            target = _target(ms)
            if target is None:
                continue
            master_id = ms.master_mobile_suit_id
            assert master_id is not None
            diffs = {
                name: (getattr(ms, name), new)
                for name, new in masters[master_id].items()
                if getattr(ms, name) != new
            }
            if not diffs:
                continue
            if target == TARGET_NPC and not include_npc:
                target = TARGET_NPC_SKIPPED
            else:
                for name, (_, new) in diffs.items():
                    setattr(ms, name, new)
                session.add(ms)
            for name, (old, new) in diffs.items():
                report.changes[(target, master_id, name, old, new)] += 1
            report.updated_rows[target] += 1

    return report

"""所持している練習機に、練習機の機体マスターIDを設定する.

練習機が機体マスターに無かったころに作った機体は ``master_mobile_suit_id`` が NULL になっている。
機体名が練習機の機体マスターと一致する行に、その機体マスターIDを設定する。

- ``user_id`` が NULL の機体（マッチング時に作られるエース機のコピーなど）は対象にしない
- 機体名を変えた練習機は、機体名で引けないため対象外
"""

from collections import Counter
from dataclasses import dataclass, field

from sqlmodel import Session, col, select

from app.models.models import MasterMobileSuit, MobileSuit


@dataclass
class TrainerMasterBackfillReport:
    """設定する（設定した）機体マスターIDの集計."""

    # (機体マスターID, 機体名) → 件数
    updated: Counter[tuple[str, str]] = field(default_factory=Counter)

    @property
    def has_changes(self) -> bool:
        """更新する行が1つでもあるか."""
        return bool(self.updated)


def backfill_trainer_master_id(session: Session) -> TrainerMasterBackfillReport:
    """練習機の機体マスターIDを、所持している練習機へ設定し、設定した件数を返す.

    commit はしない。呼び出し元が結果を見て commit か rollback を選ぶ。
    """
    report = TrainerMasterBackfillReport()
    trainer_ids_by_name = {
        mms.name: mms.id
        for mms in session.exec(
            select(MasterMobileSuit).where(col(MasterMobileSuit.is_trainer).is_(True))
        ).all()
    }
    if not trainer_ids_by_name:
        return report

    stmt = select(MobileSuit).where(
        col(MobileSuit.master_mobile_suit_id).is_(None),
        col(MobileSuit.user_id).is_not(None),
        col(MobileSuit.name).in_(list(trainer_ids_by_name)),
    )
    for ms in session.exec(stmt).all():
        master_id = trainer_ids_by_name[ms.name]
        ms.master_mobile_suit_id = master_id
        session.add(ms)
        report.updated[(master_id, ms.name)] += 1
    return report

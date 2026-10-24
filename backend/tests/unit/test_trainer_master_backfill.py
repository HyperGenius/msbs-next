"""練習機の機体マスターIDのバックフィル（backfill_trainer_master_id）のテスト."""

from sqlmodel import Session

from app.models.models import MobileSuit
from app.services.trainer_master_backfill_service import backfill_trainer_master_id

TRAINER_NAME = "MS-06T Zaku II Trainer"


def _create_ms(
    session: Session, user_id: str | None, name: str, master_id: str | None = None
) -> MobileSuit:
    ms = MobileSuit(
        user_id=user_id,
        name=name,
        max_hp=700,
        current_hp=700,
        armor=40,
        mobility=1.0,
        master_mobile_suit_id=master_id,
    )
    session.add(ms)
    session.commit()
    session.refresh(ms)
    return ms


def test_backfill_sets_trainer_master_id(session: Session) -> None:
    """機体名が練習機と一致し、機体マスターIDが NULL の機体だけに設定すること."""
    target = _create_ms(session, "backfill_user", TRAINER_NAME)
    ace_copy = _create_ms(session, None, TRAINER_NAME)
    renamed = _create_ms(session, "backfill_user", "My Trainer")
    other = _create_ms(session, "backfill_user", "Zaku II", master_id="zaku_ii")

    report = backfill_trainer_master_id(session)
    session.commit()

    assert report.updated == {("zaku_ii_trainer", TRAINER_NAME): 1}
    for ms in (target, ace_copy, renamed, other):
        session.refresh(ms)
    assert target.master_mobile_suit_id == "zaku_ii_trainer"
    assert ace_copy.master_mobile_suit_id is None
    assert renamed.master_mobile_suit_id is None
    assert other.master_mobile_suit_id == "zaku_ii"


def test_backfill_is_idempotent(session: Session) -> None:
    """設定済みなら2回目は何も更新しないこと."""
    _create_ms(session, "backfill_user", TRAINER_NAME)
    backfill_trainer_master_id(session)
    session.commit()

    report = backfill_trainer_master_id(session)

    assert not report.has_changes

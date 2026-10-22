"""機体マスターの EN の同期（sync_mobile_suit_en）のテスト."""

import pytest
from sqlalchemy.orm import attributes
from sqlmodel import Session

from app.core.gamedata import STARTER_KITS
from app.models.models import MasterMobileSuit, MobileSuit
from app.services.mobile_suit_en_sync_service import (
    TARGET_NPC,
    TARGET_NPC_SKIPPED,
    TARGET_PLAYER,
    sync_mobile_suit_en,
)

# テスト用データにある機体マスター
MASTER_MS_ID = "zaku_ii"


def _update_master(session: Session, **changes: object) -> None:
    master = session.get(MasterMobileSuit, MASTER_MS_ID)
    assert master is not None
    master.specs = {**master.specs, **changes}
    attributes.flag_modified(master, "specs")
    session.add(master)
    session.commit()


def _create_ms(
    session: Session,
    user_id: str | None,
    master_id: str | None = MASTER_MS_ID,
    name: str = "Zaku II",
) -> MobileSuit:
    ms = MobileSuit(
        user_id=user_id,
        name=name,
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        max_en=1000,
        en_recovery=100,
        master_mobile_suit_id=master_id,
    )
    session.add(ms)
    session.commit()
    session.refresh(ms)
    return ms


@pytest.fixture
def suits(session: Session) -> dict[str, MobileSuit]:
    """プレイヤー機・NPC機・エース機のコピー・機体マスターIDの無い機体."""
    return {
        "player": _create_ms(session, "en_sync_user"),
        "npc": _create_ms(session, "npc-0123456789abcdef"),
        "ace_copy": _create_ms(session, None),
        # 機体マスターIDのカラムを追加する前に購入した機体
        "by_name": _create_ms(session, "en_sync_user", master_id=None),
        # 機体名を変えると機体マスターを引けない
        "renamed": _create_ms(session, "en_sync_user", master_id=None, name="My Zaku"),
    }


def test_dry_run_reports_changes_without_writing(
    session: Session, suits: dict[str, MobileSuit]
) -> None:
    """Rollback すれば DB は変わらず、変わる値は報告される."""
    _update_master(session, en_recovery=40)

    report = sync_mobile_suit_en(session, [MASTER_MS_ID])
    session.rollback()

    assert report.has_changes
    assert report.changes[(TARGET_PLAYER, MASTER_MS_ID, "en_recovery", 100, 40)] == 2
    assert report.updated_rows[TARGET_PLAYER] == 2
    session.refresh(suits["player"])
    assert suits["player"].en_recovery == 100


def test_apply_updates_player_mobile_suits_only(
    session: Session, suits: dict[str, MobileSuit]
) -> None:
    """プレイヤー機だけを更新し、NPC機は対象外として数える."""
    _update_master(session, max_en=800, en_recovery=40)

    report = sync_mobile_suit_en(session, [MASTER_MS_ID])
    session.commit()

    for key in suits:
        session.refresh(suits[key])
    assert (suits["player"].max_en, suits["player"].en_recovery) == (800, 40)
    assert suits["npc"].en_recovery == 100
    assert suits["ace_copy"].en_recovery == 100
    assert (suits["by_name"].max_en, suits["by_name"].en_recovery) == (800, 40)
    assert suits["renamed"].en_recovery == 100
    assert report.updated_rows[TARGET_NPC_SKIPPED] == 1
    assert report.updated_rows[TARGET_NPC] == 0


def test_include_npc_updates_npc_mobile_suits(
    session: Session, suits: dict[str, MobileSuit]
) -> None:
    """include_npc を指定すると NPC機も更新する."""
    _update_master(session, en_recovery=40)

    report = sync_mobile_suit_en(session, [MASTER_MS_ID], include_npc=True)
    session.commit()

    session.refresh(suits["npc"])
    assert suits["npc"].en_recovery == 40
    assert report.updated_rows[TARGET_NPC] == 1
    assert report.updated_rows[TARGET_NPC_SKIPPED] == 0


def test_master_without_en_keys_uses_defaults(
    session: Session, suits: dict[str, MobileSuit]
) -> None:
    """機体マスターの specs に EN のキーが無ければ既定値（1000 / 100）として比べる."""
    master = session.get(MasterMobileSuit, MASTER_MS_ID)
    assert master is not None
    master.specs = {
        k: v for k, v in master.specs.items() if k not in ("max_en", "en_recovery")
    }
    attributes.flag_modified(master, "specs")
    session.add(master)
    session.commit()

    report = sync_mobile_suit_en(session, [MASTER_MS_ID])

    assert not report.has_changes


def test_second_run_has_no_changes(
    session: Session, suits: dict[str, MobileSuit]
) -> None:
    """同期済みなら差分は出ない."""
    _update_master(session, en_recovery=40)
    sync_mobile_suit_en(session, [MASTER_MS_ID])
    session.commit()

    report = sync_mobile_suit_en(session, [MASTER_MS_ID])

    assert not report.has_changes


def test_unknown_master_id_raises(session: Session) -> None:
    """機体マスターに無いIDを指定するとエラーになる."""
    with pytest.raises(ValueError, match="no_such_ms"):
        sync_mobile_suit_en(session, ["no_such_ms"])


def test_starter_kit_mobile_suits_use_starter_kit_values(session: Session) -> None:
    """機体マスターに無い練習機は、機体名で STARTER_KITS の EN を引く."""
    kit = STARTER_KITS["ZEON"]
    trainer = _create_ms(session, "en_sync_user", master_id=None, name=kit["name"])

    report = sync_mobile_suit_en(session, [kit["id"]])
    session.commit()

    session.refresh(trainer)
    assert trainer.max_en == kit["specs"]["max_en"]
    assert trainer.en_recovery == kit["specs"]["en_recovery"]
    assert report.updated_rows[TARGET_PLAYER] == 1

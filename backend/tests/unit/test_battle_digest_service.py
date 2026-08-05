"""Tests for app.services.battle_digest_service (Issue #415).

BattleResultの生成箇所(main.py / scripts/run_batch.py)が共通で使う
ダイジェスト計算ヘルパーの単体テスト。
"""

from datetime import UTC, datetime

from sqlmodel import Session, SQLModel, create_engine

from app.db import json_serializer
from app.models.models import BattleResult, MobileSuit
from app.services.battle_digest_service import (
    compute_battle_digest_fields,
    get_previous_digest_text,
)


def _make_session() -> Session:
    engine = create_engine("sqlite:///:memory:", json_serializer=json_serializer)
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _make_player(current_hp: int = 1000, max_hp: int = 1000) -> MobileSuit:
    return MobileSuit(
        name="Gelgoog", max_hp=max_hp, current_hp=current_hp, side="PLAYER"
    )


def test_get_previous_digest_text_none_when_no_user():
    """未ログイン（user_id無し）の場合は常にNone."""
    session = _make_session()
    assert get_previous_digest_text(session, None) is None


def test_get_previous_digest_text_returns_latest():
    """同一ユーザーの直近のBattleResultのdigest_textを返す."""
    session = _make_session()
    older = BattleResult(
        user_id="user1",
        win_loss="WIN",
        digest_text="古い一言ログ",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    newer = BattleResult(
        user_id="user1",
        win_loss="WIN",
        digest_text="新しい一言ログ",
        created_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    session.add(older)
    session.add(newer)
    session.commit()

    assert get_previous_digest_text(session, "user1") == "新しい一言ログ"


def test_compute_battle_digest_fields_returns_battle_result_ready_dict():
    """BattleResult(**dict)にそのまま展開できるキー・値を返す."""
    session = _make_session()
    player = _make_player(current_hp=1000, max_hp=1000)

    fields = compute_battle_digest_fields(
        session=session,
        user_id=None,
        player=player,
        logs=[],
        kills=1,
        win_loss="WIN",
        steps_used=10,
        max_steps=50,
    )

    assert set(fields.keys()) == {
        "player_survived",
        "min_hp_percent",
        "damage_severity",
        "damage_taken_count",
        "max_hit_damage",
        "dodge_count",
        "attacks_received_count",
        "pilot_ms_name",
        "digest_tag",
        "digest_text",
    }
    assert fields["player_survived"] is True
    assert fields["min_hp_percent"] == 100
    assert fields["damage_severity"] == "無傷"
    assert fields["pilot_ms_name"] == "Gelgoog"
    assert fields["digest_text"] is not None

    # BattleResult に問題なく展開できること
    result = BattleResult(user_id=None, win_loss="WIN", **fields)
    assert result.digest_tag == fields["digest_tag"]

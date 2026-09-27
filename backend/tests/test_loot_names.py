"""戦利品の対象の名前を付けるテスト."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, desc, select

from app.core.auth import get_current_user, get_current_user_optional
from app.models.models import BattleResult, LootItem, MasterMobileSuit
from app.services.loot_service import LootService
from main import app

USER_ID = "test_loot_user"


def _loot(target_type: str, target_id: str, is_new: bool = True) -> dict:
    return LootItem(
        kind="BLUEPRINT",
        blueprint_id=f"{target_type.lower()}:{target_id}",
        target_type=target_type,
        target_id=target_id,
        is_new=is_new,
        credits_awarded=0 if is_new else 300,
    ).model_dump()


def _make_battle(
    session: Session, loot: list[dict] | None, minutes_ago: int = 0
) -> BattleResult:
    battle = BattleResult(
        user_id=USER_ID,
        win_loss="WIN",
        loot=loot,
        created_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
    )
    session.add(battle)
    session.commit()
    session.refresh(battle)
    return battle


@contextmanager
def _recorded_queries(session: Session) -> Iterator[list[str]]:
    statements: list[str] = []

    def _record(conn, cursor, statement, parameters, context, executemany) -> None:  # type: ignore[no-untyped-def]
        statements.append(statement)

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", _record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", _record)


@pytest.fixture(name="user_client")
def user_client_fixture(client: TestClient) -> TestClient:
    """ログイン済みのクライアントを返す."""
    app.dependency_overrides[get_current_user] = lambda: USER_ID
    app.dependency_overrides[get_current_user_optional] = lambda: USER_ID
    return client


def test_with_names_uses_master_names(session: Session) -> None:
    """機体は name_ja を優先し、武器は name を名前にすること."""
    gelgoog = session.get(MasterMobileSuit, "gelgoog")
    assert gelgoog is not None
    gelgoog.name_ja = "ゲルググ"
    session.add(gelgoog)
    session.commit()

    [loot] = LootService.with_names(
        session,
        [
            [
                _loot("MOBILE_SUIT", "gelgoog"),
                _loot("MOBILE_SUIT", "dom"),
                _loot("WEAPON", "beam_rifle", is_new=False),
            ]
        ],
    )

    assert loot is not None
    assert [item.target_name for item in loot] == ["ゲルググ", "Dom", "Beam Rifle"]
    assert loot[2].credits_awarded == 300


def test_with_names_falls_back_to_target_id(session: Session) -> None:
    """対象のマスターが無ければ target_id を名前にすること."""
    [loot] = LootService.with_names(
        session, [[_loot("MOBILE_SUIT", "deleted_ms"), _loot("WEAPON", "gone")]]
    )

    assert loot is not None
    assert [item.target_name for item in loot] == ["deleted_ms", "gone"]


def test_with_names_keeps_none_and_empty(session: Session) -> None:
    """導入前のバトル（None）と、ドロップなし（空配列）はそのまま返すこと."""
    with _recorded_queries(session) as statements:
        loots = LootService.with_names(session, [None, []])

    assert loots == [None, []]
    assert statements == []


def test_summaries_query_count_does_not_depend_on_battles(session: Session) -> None:
    """バトル履歴の名前の取得が、バトル件数によらず2回のクエリで済むこと."""
    _make_battle(session, [_loot("MOBILE_SUIT", "dom")], minutes_ago=1)
    _make_battle(session, [_loot("WEAPON", "beam_rifle")], minutes_ago=2)
    _make_battle(session, [_loot("MOBILE_SUIT", "gundam")], minutes_ago=3)
    _make_battle(session, [], minutes_ago=4)
    _make_battle(session, None, minutes_ago=5)
    battles = session.exec(
        select(BattleResult).order_by(desc(BattleResult.created_at))
    ).all()

    with _recorded_queries(session) as statements:
        summaries = LootService.summaries(session, battles)

    assert len(statements) == 2
    assert [
        None if s.loot is None else [item.target_name for item in s.loot]
        for s in summaries
    ] == [["Dom"], ["Beam Rifle"], ["Gundam"], [], None]


def test_battle_endpoints_include_target_name(
    user_client: TestClient, session: Session
) -> None:
    """一覧・未読・詳細のレスポンスに対象の名前が含まれること."""
    battle = _make_battle(session, [_loot("MOBILE_SUIT", "gouf")])
    _make_battle(session, None, minutes_ago=1)

    history = user_client.get("/api/battles").json()
    unread = user_client.get("/api/battles/unread").json()
    detail = user_client.get(f"/api/battles/{battle.id}").json()

    assert [b["loot"] for b in history][1] is None
    for loot in (history[0]["loot"], unread[0]["loot"], detail["loot"]):
        assert loot[0]["target_name"] == "Gouf"
        assert loot[0]["target_id"] == "gouf"

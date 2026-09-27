"""設計図コレクション（図鑑）サービス・APIのテスト."""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.models.models import (
    BlueprintCollectionItem,
    BlueprintSource,
    DropTable,
    DropTableEntry,
    MasterBlueprint,
    ObtainableTheater,
    Pilot,
)
from app.services.blueprint_collection_service import (
    ALL_THEATERS_LABEL,
    BlueprintCollectionService,
    theater_label_for,
)
from app.services.blueprint_service import BlueprintService
from app.services.drop_service import DropScope
from main import app

USER_ID = "test_collection_user"
ZAKU_II = "mobile_suit:zaku_ii"
DOM = "mobile_suit:dom"
GELGOOG = "mobile_suit:gelgoog"
GUNDAM = "mobile_suit:gundam"
BEAM_RIFLE = "weapon:beam_rifle"


@pytest.fixture(name="pilot")
def pilot_fixture(session: Session) -> Pilot:
    """ジオン所属のパイロットを作成する."""
    pilot = Pilot(user_id=USER_ID, name="Collection Pilot", faction="ZEON")
    session.add(pilot)
    session.commit()
    return pilot


def _make_restricted(session: Session, *blueprint_ids: str) -> None:
    for blueprint_id in blueprint_ids:
        blueprint = session.get(MasterBlueprint, blueprint_id)
        assert blueprint is not None
        blueprint.is_standard_issue = False
        session.add(blueprint)
    session.commit()


def _make_table(
    session: Session, scope: DropScope, entries: list[tuple[str, bool]]
) -> None:
    table = DropTable(
        scope_type=scope.scope_type.value,
        scope_key=scope.scope_key,
        name=f"{scope.scope_type.value}:{scope.scope_key}",
        drop_rate=0.3,
    )
    session.add(table)
    session.flush()
    for blueprint_id, requires_win in entries:
        session.add(
            DropTableEntry(
                drop_table_id=table.id,
                blueprint_id=blueprint_id,
                requires_win=requires_win,
            )
        )
    session.commit()


def _by_id(items: list[BlueprintCollectionItem]) -> dict[str, BlueprintCollectionItem]:
    return {item.blueprint_id: item for item in items}


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


def test_theater_label_for() -> None:
    """定期バトルは固定ラベル、ミッションは対象外になること."""
    assert theater_label_for(DropScope.batch()) == ALL_THEATERS_LABEL
    assert theater_label_for(DropScope.mission(1)) is None


def test_collection_lists_all_blueprints_with_names(
    session: Session, pilot: Pilot
) -> None:
    """全設計図が、対象の名前と勢力付きで設計図ID順に並ぶこと."""
    items = BlueprintCollectionService.get_collection(session, USER_ID)

    all_ids = sorted(session.exec(select(MasterBlueprint.id)).all())
    assert [item.blueprint_id for item in items] == all_ids

    by_id = _by_id(items)
    assert by_id[GUNDAM].target_type == "MOBILE_SUIT"
    assert by_id[GUNDAM].target_name == "Gundam"
    assert by_id[GUNDAM].faction == "FEDERATION"
    assert by_id[BEAM_RIFLE].target_type == "WEAPON"
    assert by_id[BEAM_RIFLE].target_name == "Beam Rifle"
    assert by_id[BEAM_RIFLE].faction == ""


def test_collection_states(session: Session, pilot: Pilot) -> None:
    """標準配備・所持・未所持・勢力外が区別されること."""
    _make_restricted(session, DOM, GELGOOG, GUNDAM)
    _make_table(session, DropScope.batch(), [(DOM, False), (GUNDAM, False)])
    BlueprintService.grant_blueprint(session, USER_ID, GELGOOG, BlueprintSource.DROP)
    session.commit()

    by_id = _by_id(BlueprintCollectionService.get_collection(session, USER_ID))

    standard = by_id[ZAKU_II]
    assert standard.is_standard_issue is True
    assert standard.is_owned is False
    assert standard.obtainable_theaters == []

    owned = by_id[GELGOOG]
    assert owned.is_owned is True
    assert owned.source == "DROP"
    assert owned.acquired_at is not None
    assert owned.obtainable_theaters == []

    unowned = by_id[DOM]
    assert unowned.is_owned is False
    assert unowned.acquired_at is None
    assert unowned.source is None
    assert unowned.is_available_to_faction is True
    assert unowned.obtainable_theaters == [
        ObtainableTheater(label=ALL_THEATERS_LABEL, requires_win=False)
    ]

    other_faction = by_id[GUNDAM]
    assert other_faction.is_available_to_faction is False
    assert other_faction.obtainable_theaters == []


def test_collection_shows_migration_source(session: Session, pilot: Pilot) -> None:
    """導入時に付与した設計図は入手経路が MIGRATION になること."""
    _make_restricted(session, DOM)
    BlueprintService.grant_blueprint(session, USER_ID, DOM, BlueprintSource.MIGRATION)
    session.commit()

    item = _by_id(BlueprintCollectionService.get_collection(session, USER_ID))[DOM]
    assert item.is_owned is True
    assert item.source == "MIGRATION"


def test_collection_requires_win_theater(session: Session, pilot: Pilot) -> None:
    """勝利時のみのエントリーは requires_win が true になること."""
    _make_restricted(session, DOM)
    _make_table(session, DropScope.batch(), [(DOM, True)])

    item = _by_id(BlueprintCollectionService.get_collection(session, USER_ID))[DOM]
    assert item.obtainable_theaters == [
        ObtainableTheater(label=ALL_THEATERS_LABEL, requires_win=True)
    ]


def test_collection_ignores_mission_tables(session: Session, pilot: Pilot) -> None:
    """ミッションのテーブルにしか無い設計図は、入手できる戦域が空になること."""
    _make_restricted(session, DOM, BEAM_RIFLE)
    _make_table(session, DropScope.mission(1), [(DOM, False), (BEAM_RIFLE, False)])
    _make_table(session, DropScope.batch(), [(DOM, True)])

    by_id = _by_id(BlueprintCollectionService.get_collection(session, USER_ID))
    assert by_id[DOM].obtainable_theaters == [
        ObtainableTheater(label=ALL_THEATERS_LABEL, requires_win=True)
    ]
    assert by_id[BEAM_RIFLE].is_available_to_faction is True
    assert by_id[BEAM_RIFLE].obtainable_theaters == []


def test_collection_excludes_blueprints_without_target(
    session: Session, pilot: Pilot
) -> None:
    """機体・武器マスターが無い設計図は一覧に出さないこと."""
    session.add(
        MasterBlueprint(
            id="mobile_suit:deleted_ms",
            target_type="MOBILE_SUIT",
            target_id="deleted_ms",
            is_standard_issue=False,
        )
    )
    session.commit()

    ids = {
        item.blueprint_id
        for item in BlueprintCollectionService.get_collection(session, USER_ID)
    }
    assert "mobile_suit:deleted_ms" not in ids


def test_collection_without_pilot_treats_all_factions_available(
    session: Session,
) -> None:
    """パイロットが無ければ、全ての機体を勢力で絞らないこと."""
    _make_restricted(session, GUNDAM)
    _make_table(session, DropScope.batch(), [(GUNDAM, False)])

    item = _by_id(BlueprintCollectionService.get_collection(session, USER_ID))[GUNDAM]
    assert item.is_available_to_faction is True
    assert item.obtainable_theaters == [
        ObtainableTheater(label=ALL_THEATERS_LABEL, requires_win=False)
    ]


def test_collection_query_count_is_constant(session: Session, pilot: Pilot) -> None:
    """取得が設計図・エントリー・所持設計図の数によらず7回のクエリで済むこと."""
    blueprint_ids = list(session.exec(select(MasterBlueprint.id)).all())
    _make_restricted(session, *blueprint_ids)
    _make_table(session, DropScope.batch(), [(bid, False) for bid in blueprint_ids])
    _make_table(session, DropScope.mission(1), [(bid, True) for bid in blueprint_ids])
    for blueprint_id in blueprint_ids[:3]:
        BlueprintService.grant_blueprint(
            session, USER_ID, blueprint_id, BlueprintSource.DROP
        )
    session.commit()

    with _recorded_queries(session) as statements:
        items = BlueprintCollectionService.get_collection(session, USER_ID)

    assert len(items) == len(blueprint_ids) > 3
    assert len(statements) == 7


def test_get_collection_api(client: TestClient, session: Session, pilot: Pilot) -> None:
    """GET /api/blueprints/collection でログイン中プレイヤーの図鑑を取得できること."""
    _make_restricted(session, DOM)
    _make_table(session, DropScope.batch(), [(DOM, True)])

    app.dependency_overrides[get_current_user] = lambda: USER_ID
    try:
        response = client.get("/api/blueprints/collection")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_200_OK
    dom = next(item for item in response.json() if item["blueprint_id"] == DOM)
    assert dom == {
        "blueprint_id": DOM,
        "target_type": "MOBILE_SUIT",
        "target_id": "dom",
        "target_name": "Dom",
        "faction": "ZEON",
        "is_standard_issue": False,
        "is_owned": False,
        "acquired_at": None,
        "source": None,
        "is_available_to_faction": True,
        "obtainable_theaters": [{"label": ALL_THEATERS_LABEL, "requires_win": True}],
        "tech_requirements": [],
    }


def test_get_collection_api_requires_auth(client: TestClient) -> None:
    """未認証では図鑑を取得できないこと."""
    response = client.get("/api/blueprints/collection")
    assert response.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    )

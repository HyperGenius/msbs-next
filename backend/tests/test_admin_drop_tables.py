"""管理者用ドロップテーブル API のテスト."""

import random
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, col, select

from app.models.models import (
    BlueprintTargetType,
    DropScopeType,
    DropTable,
    DropTableEntry,
    MasterBlueprint,
    Pilot,
)
from app.services.blueprint_service import BlueprintService
from app.services.drop_service import DropScope, DropService
from app.services.drop_table_service import DropTableService

ADMIN_KEY = "test_admin_key_12345"
HEADERS = {"X-API-Key": ADMIN_KEY}
ENDPOINT = "/api/admin/drop-tables/batch"

DOM = "mobile_suit:dom"
GELGOOG = "mobile_suit:gelgoog"
GUNDAM = "mobile_suit:gundam"
BEAM_RIFLE = "weapon:beam_rifle"


@pytest.fixture(autouse=True)
def admin_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """管理者APIキーを設定する."""
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)


def _make_restricted(session: Session, *blueprint_ids: str) -> None:
    for blueprint_id in blueprint_ids:
        blueprint = session.get(MasterBlueprint, blueprint_id)
        assert blueprint is not None
        blueprint.is_standard_issue = False
        session.add(blueprint)
    session.commit()


def _make_batch_table(
    session: Session, entries: list[tuple[str, int, bool]]
) -> DropTable:
    scope = DropScope.batch()
    table = DropTable(
        scope_type=scope.scope_type.value,
        scope_key=scope.scope_key,
        name="既存テーブル",
        drop_rate=0.3,
        win_rate_multiplier=1.5,
    )
    session.add(table)
    session.flush()
    for blueprint_id, weight, requires_win in entries:
        session.add(
            DropTableEntry(
                drop_table_id=table.id,
                blueprint_id=blueprint_id,
                weight=weight,
                requires_win=requires_win,
            )
        )
    session.commit()
    return table


def _payload(entries: list[dict] | None = None, **overrides: object) -> dict:
    return {
        "name": "定期バトル",
        "drop_rate": 0.4,
        "win_rate_multiplier": 2.0,
        "entries": entries if entries is not None else [],
        **overrides,
    }


def _batch_entries(session: Session) -> list[DropTableEntry]:
    table = DropService.find_table(session, DropScope.batch())
    assert table is not None
    return list(
        session.exec(
            select(DropTableEntry)
            .where(DropTableEntry.drop_table_id == table.id)
            .order_by(col(DropTableEntry.blueprint_id))
        ).all()
    )


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


# ===================== 認証 =====================


def test_get_requires_api_key(client: TestClient) -> None:
    """APIキーが違えば 401 になること."""
    response = client.get(ENDPOINT, headers={"X-API-Key": "wrong"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_put_requires_api_key(client: TestClient, session: Session) -> None:
    """APIキーが違えば 401 になり、テーブルを作成しないこと."""
    response = client.put(ENDPOINT, json=_payload(), headers={"X-API-Key": "wrong"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert DropService.find_table(session, DropScope.batch()) is None


# ===================== 取得 =====================


def test_get_without_table_returns_defaults(
    client: TestClient, session: Session
) -> None:
    """テーブルが無ければ、ドロップ率0・エントリー無しの既定値を返すこと."""
    _make_restricted(session, GELGOOG, BEAM_RIFLE)

    response = client.get(ENDPOINT, headers=HEADERS)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] is None
    assert data["name"] == "定期バトル"
    assert data["drop_rate"] == 0.0
    assert data["win_rate_multiplier"] == 1.0
    assert data["entries"] == []
    assert [b["blueprint_id"] for b in data["unobtainable_blueprints"]] == [
        GELGOOG,
        BEAM_RIFLE,
    ]


def test_get_returns_entries_with_target_info(
    client: TestClient, session: Session
) -> None:
    """エントリーに対象の名前・勢力・標準配備かが付くこと."""
    _make_restricted(session, GELGOOG, GUNDAM)
    table = _make_batch_table(
        session, [(GELGOOG, 2, True), (DOM, 3, False), (BEAM_RIFLE, 1, False)]
    )

    response = client.get(ENDPOINT, headers=HEADERS)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == table.id
    assert data["name"] == "既存テーブル"
    assert data["drop_rate"] == 0.3
    assert data["win_rate_multiplier"] == 1.5
    # 追加した順に並ぶ。
    assert data["entries"] == [
        {
            "blueprint_id": GELGOOG,
            "target_type": "MOBILE_SUIT",
            "target_id": "gelgoog",
            "target_name": "Gelgoog",
            "faction": "ZEON",
            "is_standard_issue": False,
            "weight": 2,
            "requires_win": True,
        },
        {
            "blueprint_id": DOM,
            "target_type": "MOBILE_SUIT",
            "target_id": "dom",
            "target_name": "Dom",
            "faction": "ZEON",
            "is_standard_issue": True,
            "weight": 3,
            "requires_win": False,
        },
        {
            "blueprint_id": BEAM_RIFLE,
            "target_type": "WEAPON",
            "target_id": "beam_rifle",
            "target_name": "Beam Rifle",
            "faction": "",
            "is_standard_issue": True,
            "weight": 1,
            "requires_win": False,
        },
    ]
    # テーブルに入っている要設計図は、入手手段が無い一覧に含めない。
    assert [b["blueprint_id"] for b in data["unobtainable_blueprints"]] == [GUNDAM]


def test_get_ignores_mission_table(client: TestClient, session: Session) -> None:
    """ミッションのテーブルは定期バトルのテーブルとして返さないこと."""
    session.add(
        DropTable(
            scope_type=DropScopeType.MISSION.value,
            scope_key="1",
            name="ミッション",
            drop_rate=0.9,
        )
    )
    session.commit()

    response = client.get(ENDPOINT, headers=HEADERS)

    assert response.json()["id"] is None


def test_get_detail_query_count_is_constant(session: Session) -> None:
    """取得がエントリー数によらず3回のクエリで済むこと."""
    blueprint_ids = list(session.exec(select(MasterBlueprint.id)).all())
    _make_batch_table(session, [(bid, 1, False) for bid in blueprint_ids])

    with _recorded_queries(session) as statements:
        detail = DropTableService.get_detail(session, DropScope.batch())

    assert len(detail.entries) == len(blueprint_ids) > 3
    assert len(statements) == 3


# ===================== 保存 =====================


def test_put_creates_table_when_missing(client: TestClient, session: Session) -> None:
    """テーブルが無ければ作成し、保存後の内容を返すこと."""
    response = client.put(
        ENDPOINT,
        json=_payload(
            [
                {"blueprint_id": GELGOOG, "weight": 2, "requires_win": True},
                {"blueprint_id": BEAM_RIFLE, "weight": 5},
            ]
        ),
        headers=HEADERS,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    table = DropService.find_table(session, DropScope.batch())
    assert table is not None
    assert data["id"] == table.id
    assert (table.name, table.drop_rate, table.win_rate_multiplier) == (
        "定期バトル",
        0.4,
        2.0,
    )
    assert [
        (e["blueprint_id"], e["weight"], e["requires_win"]) for e in data["entries"]
    ] == [
        (GELGOOG, 2, True),
        (BEAM_RIFLE, 5, False),
    ]


def test_put_replaces_existing_entries(client: TestClient, session: Session) -> None:
    """既存テーブルの設定を更新し、エントリーを入力の内容で置き換えること."""
    table = _make_batch_table(session, [(DOM, 3, False), (GELGOOG, 1, True)])

    response = client.put(
        ENDPOINT,
        json=_payload(
            [
                {"blueprint_id": GELGOOG, "weight": 4, "requires_win": False},
                {"blueprint_id": GUNDAM, "weight": 1, "requires_win": True},
            ],
            name="改定後",
            drop_rate=1.0,
            win_rate_multiplier=1.0,
        ),
        headers=HEADERS,
    )

    assert response.status_code == status.HTTP_200_OK
    session.expire_all()
    saved = DropService.find_table(session, DropScope.batch())
    assert saved is not None
    assert saved.id == table.id
    assert (saved.name, saved.drop_rate, saved.win_rate_multiplier) == (
        "改定後",
        1.0,
        1.0,
    )
    assert [
        (e.blueprint_id, e.weight, e.requires_win) for e in _batch_entries(session)
    ] == [(GELGOOG, 4, False), (GUNDAM, 1, True)]


def test_put_accepts_empty_entries(client: TestClient, session: Session) -> None:
    """エントリーを0件にして保存できること."""
    _make_batch_table(session, [(DOM, 3, False)])

    response = client.put(ENDPOINT, json=_payload([]), headers=HEADERS)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["entries"] == []
    assert _batch_entries(session) == []


def test_put_does_not_change_mission_table(
    client: TestClient, session: Session
) -> None:
    """ミッションのテーブルは変更しないこと."""
    mission_table = DropTable(
        scope_type=DropScopeType.MISSION.value,
        scope_key="1",
        name="ミッション",
        drop_rate=0.9,
    )
    session.add(mission_table)
    session.flush()
    session.add(DropTableEntry(drop_table_id=mission_table.id, blueprint_id=DOM))
    session.commit()

    response = client.put(ENDPOINT, json=_payload([]), headers=HEADERS)

    assert response.status_code == status.HTTP_200_OK
    session.expire_all()
    assert session.get(DropTable, mission_table.id).drop_rate == 0.9  # type: ignore[union-attr]
    assert (
        session.exec(
            select(DropTableEntry).where(
                DropTableEntry.drop_table_id == mission_table.id
            )
        ).first()
        is not None
    )


def test_saved_table_is_used_by_shop_and_drop(
    client: TestClient, session: Session
) -> None:
    """保存した内容がショップの入手ヒントと抽選に反映されること."""
    _make_restricted(session, GELGOOG)
    session.add(Pilot(user_id="drop_admin_user", name="P", faction="ZEON"))
    session.commit()

    client.put(
        ENDPOINT,
        json=_payload([{"blueprint_id": GELGOOG, "weight": 1}], drop_rate=1.0),
        headers=HEADERS,
    )

    states = BlueprintService.get_unlock_states(
        session, "drop_admin_user", BlueprintTargetType.MOBILE_SUIT, ["gelgoog"]
    )
    assert states["gelgoog"].unlock_hint == "定期バトルでドロップ"

    loot = DropService.roll(
        session,
        "drop_admin_user",
        DropScope.batch(),
        is_win=False,
        battle_result_id=uuid.uuid4(),
        rng=random.Random(0),
    )
    assert [item.blueprint_id for item in loot] == [GELGOOG]


# ===================== バリデーション =====================


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        (
            [
                {"blueprint_id": DOM, "weight": 1},
                {"blueprint_id": DOM, "weight": 2, "requires_win": True},
            ],
            "Duplicate blueprints: mobile_suit:dom",
        ),
        (
            [{"blueprint_id": "mobile_suit:no_such_ms", "weight": 1}],
            "Blueprints not found: mobile_suit:no_such_ms",
        ),
    ],
)
def test_put_rejects_invalid_entries(
    client: TestClient, session: Session, entries: list[dict], message: str
) -> None:
    """重複した設計図・存在しない設計図は 422 になり、保存しないこと."""
    table = _make_batch_table(session, [(GELGOOG, 1, False)])

    response = client.put(ENDPOINT, json=_payload(entries), headers=HEADERS)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()["detail"] == message
    session.expire_all()
    assert session.get(DropTable, table.id).drop_rate == 0.3  # type: ignore[union-attr]
    assert [e.blueprint_id for e in _batch_entries(session)] == [GELGOOG]


@pytest.mark.parametrize(
    "overrides",
    [
        {"drop_rate": -0.01},
        {"drop_rate": 1.01},
        {"win_rate_multiplier": 0.99},
        {"name": ""},
        {"entries": [{"blueprint_id": DOM, "weight": 0}]},
        {"entries": [{"blueprint_id": DOM, "weight": 1.5}]},
    ],
)
def test_put_rejects_out_of_range_values(
    client: TestClient, session: Session, overrides: dict
) -> None:
    """範囲外の値は 422 になり、テーブルを作成しないこと."""
    response = client.put(ENDPOINT, json=_payload(**overrides), headers=HEADERS)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert DropService.find_table(session, DropScope.batch()) is None

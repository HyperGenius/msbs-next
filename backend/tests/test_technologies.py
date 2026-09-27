"""技術断片・技術Lvのテスト."""

import random
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.models.models import (
    BlueprintSource,
    BlueprintTargetType,
    BlueprintTechRequirement,
    DropRewardType,
    DropTable,
    DropTableEntry,
    LootItem,
    MasterBlueprint,
    MasterBlueprintSettingsInput,
    MasterMobileSuit,
    MasterTechnology,
    Pilot,
    PlayerTechnology,
    TechRequirement,
)
from app.services.blueprint_collection_service import (
    ALL_THEATERS_LABEL,
    BlueprintCollectionService,
)
from app.services.blueprint_service import BlueprintService, format_missing_tech
from app.services.drop_service import DropScope, DropService
from app.services.loot_service import LootService
from app.services.technology_service import TechnologyService
from main import app

USER_ID = "test_tech_user"
ADMIN_KEY = "test_admin_key_12345"
ADMIN_HEADERS = {"X-API-Key": ADMIN_KEY}

BEAM = "beam_generator_tech"
PSYCOMMU = "psycommu_tech"
BEAM_RIFLE = "weapon:beam_rifle"
GELGOOG = "mobile_suit:gelgoog"
OVERFLOW_CREDITS = 500


@pytest.fixture(autouse=True)
def admin_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """管理者APIキーを設定する."""
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)


@pytest.fixture(name="pilot")
def pilot_fixture(session: Session) -> Pilot:
    """連邦所属のパイロットを作成する."""
    pilot = Pilot(
        user_id=USER_ID, name="Tech Pilot", faction="FEDERATION", credits=10000
    )
    session.add(pilot)
    session.commit()
    session.refresh(pilot)
    return pilot


@pytest.fixture(name="as_user")
def as_user_fixture() -> Iterator[None]:
    """API をテスト用のプレイヤーとして呼ぶ."""
    app.dependency_overrides[get_current_user] = lambda: USER_ID
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _require(
    session: Session,
    blueprint_id: str,
    requirements: list[tuple[str, int]],
    is_standard_issue: bool = False,
) -> None:
    blueprint = session.get(MasterBlueprint, blueprint_id)
    assert blueprint is not None
    blueprint.is_standard_issue = is_standard_issue
    session.add(blueprint)
    for tech_id, required_lv in requirements:
        session.add(
            BlueprintTechRequirement(
                blueprint_id=blueprint_id, tech_id=tech_id, required_lv=required_lv
            )
        )
    session.commit()


def _set_fragments(session: Session, tech_id: str, count: int) -> None:
    session.add(
        PlayerTechnology(user_id=USER_ID, tech_id=tech_id, fragment_count=count)
    )
    session.commit()


def _make_table(
    session: Session,
    entries: list[DropTableEntry],
    scope: DropScope | None = None,
) -> DropTable:
    scope = scope or DropScope.batch()
    table = DropTable(
        scope_type=scope.scope_type.value,
        scope_key=scope.scope_key,
        name="テスト用テーブル",
        drop_rate=1.0,
    )
    session.add(table)
    session.flush()
    for entry in entries:
        entry.drop_table_id = table.id
        session.add(entry)
    session.commit()
    return table


def _tech_entry(
    tech_id: str, weight: int = 1, requires_win: bool = False
) -> DropTableEntry:
    return DropTableEntry(
        reward_type=DropRewardType.TECH_FRAGMENT.value,
        tech_id=tech_id,
        weight=weight,
        requires_win=requires_win,
    )


def _blueprint_entry(blueprint_id: str, weight: int = 1) -> DropTableEntry:
    return DropTableEntry(blueprint_id=blueprint_id, weight=weight)


def _roll(session: Session, seed: int = 0, is_win: bool = True) -> list[LootItem]:
    return DropService.roll(
        session,
        USER_ID,
        DropScope.batch(),
        is_win=is_win,
        battle_result_id=uuid.uuid4(),
        rng=random.Random(seed),
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


# --- 初期データ ---


def test_seed_technologies(session: Session) -> None:
    """ビームジェネレータ技術・サイコミュ技術が初期データとして入っていること."""
    techs = {t.id: t for t in session.exec(select(MasterTechnology)).all()}

    assert set(techs) == {BEAM, PSYCOMMU}
    assert techs[BEAM].name == "ビームジェネレータ技術"
    assert techs[PSYCOMMU].name == "サイコミュ技術"
    assert all(t.level_thresholds == [3, 8, 15] for t in techs.values())


# --- Lvの計算 ---


@pytest.mark.parametrize(
    ("count", "level", "next_threshold", "remaining"),
    [
        (0, 0, 3, 3),
        (2, 0, 3, 1),
        (3, 1, 8, 5),
        (14, 2, 15, 1),
        (15, 3, None, None),
        (20, 3, None, None),
    ],
)
def test_progress(
    count: int, level: int, next_threshold: int | None, remaining: int | None
) -> None:
    """累計数と閾値から、技術Lvと次のLvまでの残りが決まること."""
    progress = TechnologyService.progress([3, 8, 15], count)

    assert progress.level == level
    assert progress.max_level == 3
    assert progress.next_level_threshold == next_threshold
    assert progress.fragments_to_next_level == remaining


# --- 断片の付与 ---


def test_grant_fragment_creates_record(session: Session, pilot: Pilot) -> None:
    """初めての断片で累計数の記録が作られること."""
    result = TechnologyService.grant_fragment(session, USER_ID, BEAM)
    session.commit()

    assert result.fragment_count == 1
    assert result.progress.level == 0
    assert result.progress.fragments_to_next_level == 2
    assert result.is_level_up is False
    assert result.credits_awarded == 0
    owned = session.exec(
        select(PlayerTechnology).where(PlayerTechnology.user_id == USER_ID)
    ).one()
    assert owned.fragment_count == 1


def test_grant_fragment_levels_up_at_threshold(session: Session, pilot: Pilot) -> None:
    """閾値に達すると自動で技術Lvが上がること."""
    _set_fragments(session, BEAM, 2)

    result = TechnologyService.grant_fragment(session, USER_ID, BEAM)

    assert result.fragment_count == 3
    assert result.progress.level == 1
    assert result.is_level_up is True


def test_grant_fragment_reaching_max_level_is_counted(
    session: Session, pilot: Pilot
) -> None:
    """最大Lvに達する断片は換金せず累計数に加算すること."""
    _set_fragments(session, BEAM, 14)

    result = TechnologyService.grant_fragment(session, USER_ID, BEAM)

    assert result.fragment_count == 15
    assert result.progress.level == 3
    assert result.is_level_up is True
    assert result.credits_awarded == 0


def test_grant_fragment_after_max_level_is_converted(
    session: Session, pilot: Pilot
) -> None:
    """最大Lv後の断片は累計数に加算せず、クレジットに換金されること."""
    _set_fragments(session, BEAM, 15)

    result = TechnologyService.grant_fragment(session, USER_ID, BEAM)
    session.commit()

    assert result.fragment_count == 15
    assert result.progress.level == 3
    assert result.is_level_up is False
    assert result.credits_awarded == OVERFLOW_CREDITS
    session.refresh(pilot)
    assert pilot.credits == 10000 + OVERFLOW_CREDITS
    owned = session.exec(
        select(PlayerTechnology).where(PlayerTechnology.user_id == USER_ID)
    ).one()
    assert owned.fragment_count == 15


def test_raising_thresholds_lowers_level(session: Session, pilot: Pilot) -> None:
    """閾値を引き上げると、Lvは累計数から計算し直されること."""
    _set_fragments(session, BEAM, 8)
    assert TechnologyService.levels_by_tech(session, USER_ID) == {BEAM: 2}

    tech = session.get(MasterTechnology, BEAM)
    assert tech is not None
    tech.level_thresholds = [5, 10, 20]
    session.add(tech)
    session.commit()

    assert TechnologyService.levels_by_tech(session, USER_ID) == {BEAM: 1}


def test_grant_fragment_unknown_tech(session: Session, pilot: Pilot) -> None:
    """技術マスターに無い技術は付与できないこと."""
    with pytest.raises(LookupError):
        TechnologyService.grant_fragment(session, USER_ID, "no_such_tech")


# --- 購入条件 ---


def test_unlock_state_requires_blueprint_and_tech_level(
    session: Session, pilot: Pilot
) -> None:
    """設計図と必要な技術Lvがそろったときだけ購入できること."""
    _require(session, BEAM_RIFLE, [(BEAM, 2), (PSYCOMMU, 1)])
    _set_fragments(session, BEAM, 3)

    state = BlueprintService.get_unlock_state(
        session, USER_ID, BlueprintTargetType.WEAPON, "beam_rifle"
    )
    # 設計図も技術Lvも足りないときは両方の条件が出る。
    assert state.is_unlocked is False
    assert state.needs_blueprint is True
    assert state.unlock_hint is not None
    assert [
        (r.tech_id, r.required_lv, r.current_lv)
        for r in state.missing_tech_requirements
    ] == [
        (BEAM, 2, 1),
        (PSYCOMMU, 1, 0),
    ]

    BlueprintService.grant_blueprint(session, USER_ID, BEAM_RIFLE, BlueprintSource.DROP)
    session.commit()
    state = BlueprintService.get_unlock_state(
        session, USER_ID, BlueprintTargetType.WEAPON, "beam_rifle"
    )
    assert state.is_unlocked is False
    assert state.needs_blueprint is False
    assert state.unlock_hint is None
    assert len(state.missing_tech_requirements) == 2

    owned = session.exec(
        select(PlayerTechnology).where(PlayerTechnology.tech_id == BEAM)
    ).one()
    owned.fragment_count = 8
    session.add(owned)
    session.commit()
    _set_fragments(session, PSYCOMMU, 3)

    assert BlueprintService.can_purchase(
        session, USER_ID, BlueprintTargetType.WEAPON, "beam_rifle"
    )


def test_standard_issue_ignores_tech_requirements(
    session: Session, pilot: Pilot
) -> None:
    """標準配備品は技術Lvを問わず購入できること."""
    _require(session, BEAM_RIFLE, [(BEAM, 3)], is_standard_issue=True)

    state = BlueprintService.get_unlock_state(
        session, USER_ID, BlueprintTargetType.WEAPON, "beam_rifle"
    )

    assert state.is_unlocked is True
    assert state.missing_tech_requirements == ()


def test_unlock_states_query_count_with_requirements(
    session: Session, pilot: Pilot
) -> None:
    """必要な技術Lvがあっても、解放状態の取得が商品数によらず5回のクエリで済むこと."""
    target_ids = [m.id for m in session.exec(select(MasterMobileSuit)).all()]
    for target_id in target_ids:
        _require(session, f"mobile_suit:{target_id}", [(BEAM, 1), (PSYCOMMU, 2)])
    _set_fragments(session, BEAM, 3)

    with _recorded_queries(session) as statements:
        BlueprintService.get_unlock_states(
            session, USER_ID, BlueprintTargetType.MOBILE_SUIT, target_ids
        )

    assert len(target_ids) > 3
    assert len(statements) == 5


def test_format_missing_tech() -> None:
    """足りない技術Lvの文言に、必要Lvと現在Lvが入ること."""
    from app.models.models import TechRequirementStatus

    requirement = TechRequirementStatus(
        tech_id=PSYCOMMU, tech_name="サイコミュ技術", required_lv=2, current_lv=1
    )
    assert format_missing_tech(requirement) == "サイコミュ技術 Lv2 が必要（現在 Lv1）"


def test_weapon_listing_shows_missing_tech(
    client: TestClient, session: Session, pilot: Pilot, as_user: None
) -> None:
    """武器ショップの一覧に、足りない技術Lvが付くこと."""
    _require(session, BEAM_RIFLE, [(PSYCOMMU, 2)])
    BlueprintService.grant_blueprint(session, USER_ID, BEAM_RIFLE, BlueprintSource.DROP)
    session.commit()

    response = client.get("/api/shop/weapons")

    assert response.status_code == status.HTTP_200_OK
    listing = next(item for item in response.json() if item["id"] == "beam_rifle")
    assert listing["is_unlocked"] is False
    assert listing["unlock_hint"] is None
    assert listing["missing_tech_requirements"] == [
        {
            "tech_id": PSYCOMMU,
            "tech_name": "サイコミュ技術",
            "required_lv": 2,
            "current_lv": 0,
        }
    ]
    others = [item for item in response.json() if item["id"] != "beam_rifle"]
    assert all(item["missing_tech_requirements"] == [] for item in others)


def test_purchase_weapon_without_tech_level_is_forbidden(
    client: TestClient, session: Session, pilot: Pilot, as_user: None
) -> None:
    """技術Lvが足りない武器は購入できず、理由が返ること."""
    _require(session, BEAM_RIFLE, [(PSYCOMMU, 2)])
    BlueprintService.grant_blueprint(session, USER_ID, BEAM_RIFLE, BlueprintSource.DROP)
    session.commit()

    response = client.post("/api/shop/purchase/weapon/beam_rifle")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == (
        "技術Lvが足りません: サイコミュ技術 Lv2 が必要（現在 Lv0）"
    )

    _set_fragments(session, PSYCOMMU, 8)
    response = client.post("/api/shop/purchase/weapon/beam_rifle")
    assert response.status_code == status.HTTP_200_OK


def test_purchase_mobile_suit_without_tech_level_is_forbidden(
    client: TestClient, session: Session, pilot: Pilot, as_user: None
) -> None:
    """技術Lvが足りない機体は購入できないこと."""
    gundam = "mobile_suit:gundam"
    _require(session, gundam, [(BEAM, 1)])
    BlueprintService.grant_blueprint(session, USER_ID, gundam, BlueprintSource.DROP)
    session.commit()

    response = client.post("/api/shop/purchase/gundam")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "ビームジェネレータ技術 Lv1 が必要" in response.json()["detail"]

    _set_fragments(session, BEAM, 3)
    response = client.post("/api/shop/purchase/gundam")
    assert response.status_code == status.HTTP_200_OK


# --- 設計図設定での必要な技術Lv ---


def test_admin_saves_tech_requirements(client: TestClient, session: Session) -> None:
    """機体・武器の保存APIで、必要な技術Lvを設定・置換できること."""
    response = client.put(
        "/api/admin/weapons/beam_rifle",
        headers=ADMIN_HEADERS,
        json={
            "blueprint": {
                "is_standard_issue": False,
                "tech_requirements": [
                    {"tech_id": PSYCOMMU, "required_lv": 2},
                    {"tech_id": BEAM, "required_lv": 1},
                ],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["blueprint"]["tech_requirements"] == [
        {"tech_id": BEAM, "required_lv": 1},
        {"tech_id": PSYCOMMU, "required_lv": 2},
    ]

    # 未指定なら変更しない。
    response = client.put(
        "/api/admin/weapons/beam_rifle",
        headers=ADMIN_HEADERS,
        json={"blueprint": {"duplicate_credit_value": 10}},
    )
    assert len(response.json()["blueprint"]["tech_requirements"]) == 2

    response = client.put(
        "/api/admin/mobile-suits/gundam",
        headers=ADMIN_HEADERS,
        json={
            "blueprint": {"tech_requirements": [{"tech_id": BEAM, "required_lv": 3}]}
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["blueprint"]["tech_requirements"] == [
        {"tech_id": BEAM, "required_lv": 3}
    ]

    # 空の一覧で全て外せる。
    response = client.put(
        "/api/admin/weapons/beam_rifle",
        headers=ADMIN_HEADERS,
        json={"blueprint": {"tech_requirements": []}},
    )
    assert response.json()["blueprint"]["tech_requirements"] == []

    listed = client.get("/api/admin/mobile-suits", headers=ADMIN_HEADERS).json()
    gundam = next(ms for ms in listed if ms["id"] == "gundam")
    assert gundam["blueprint"]["tech_requirements"] == [
        {"tech_id": BEAM, "required_lv": 3}
    ]


def test_admin_creates_mobile_suit_with_tech_requirements(
    client: TestClient, session: Session
) -> None:
    """機体マスターの新規作成で、必要な技術Lvを設定できること."""
    ms = session.get(MasterMobileSuit, "gundam")
    assert ms is not None
    response = client.post(
        "/api/admin/mobile-suits",
        headers=ADMIN_HEADERS,
        json={
            "id": "test_new_ms",
            "name": "Test MS",
            "price": 1000,
            "description": "test",
            "weapon_slot_count": 4,
            "beam_generator_lv": 3,
            "specs": ms.specs,
            "blueprint": {
                "is_standard_issue": False,
                "tech_requirements": [{"tech_id": PSYCOMMU, "required_lv": 1}],
            },
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["blueprint"]["tech_requirements"] == [
        {"tech_id": PSYCOMMU, "required_lv": 1}
    ]


@pytest.mark.parametrize(
    "requirements",
    [
        [{"tech_id": "no_such_tech", "required_lv": 1}],
        [{"tech_id": BEAM, "required_lv": 4}],
        [{"tech_id": BEAM, "required_lv": 0}],
        [{"tech_id": BEAM, "required_lv": 1}, {"tech_id": BEAM, "required_lv": 2}],
    ],
)
def test_admin_rejects_invalid_tech_requirements(
    client: TestClient, session: Session, requirements: list[dict]
) -> None:
    """存在しない技術・最大Lv超え・0以下・重複は保存できないこと."""
    response = client.put(
        "/api/admin/weapons/beam_rifle",
        headers=ADMIN_HEADERS,
        json={"blueprint": {"tech_requirements": requirements}},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    session.expire_all()
    assert session.exec(select(BlueprintTechRequirement)).all() == []


def test_delete_master_removes_tech_requirements(
    client: TestClient, session: Session
) -> None:
    """機体・武器マスターを削除すると、必要な技術Lvも削除されること."""
    BlueprintService.save_master_blueprint_settings(
        session,
        BlueprintTargetType.WEAPON,
        "beam_rifle",
        800,
        MasterBlueprintSettingsInput(
            tech_requirements=[TechRequirement(tech_id=BEAM, required_lv=1)]
        ),
    )
    session.commit()

    response = client.delete("/api/admin/weapons/beam_rifle", headers=ADMIN_HEADERS)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert session.exec(select(BlueprintTechRequirement)).all() == []


# --- 技術マスターの管理 ---


def test_admin_technology_crud(client: TestClient, session: Session) -> None:
    """技術マスターを一覧・追加・編集・削除できること."""
    listed = client.get("/api/admin/technologies", headers=ADMIN_HEADERS).json()
    assert [t["id"] for t in listed] == [BEAM, PSYCOMMU]

    response = client.post(
        "/api/admin/technologies",
        headers=ADMIN_HEADERS,
        json={
            "id": "minovsky_craft_tech",
            "name": "ミノフスキー・クラフト技術",
            "level_thresholds": [5, 10],
            "overflow_credit_value": 300,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {
        "id": "minovsky_craft_tech",
        "name": "ミノフスキー・クラフト技術",
        "description": "",
        "level_thresholds": [5, 10],
        "overflow_credit_value": 300,
    }

    response = client.put(
        "/api/admin/technologies/minovsky_craft_tech",
        headers=ADMIN_HEADERS,
        json={"description": "説明", "level_thresholds": [4, 9, 12]},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["description"] == "説明"
    assert response.json()["level_thresholds"] == [4, 9, 12]
    assert response.json()["name"] == "ミノフスキー・クラフト技術"

    response = client.delete(
        "/api/admin/technologies/minovsky_craft_tech", headers=ADMIN_HEADERS
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert session.get(MasterTechnology, "minovsky_craft_tech") is None


@pytest.mark.parametrize("thresholds", [[], [0, 3], [3, 3], [8, 3], [-1]])
def test_admin_rejects_invalid_thresholds(
    client: TestClient, thresholds: list[int]
) -> None:
    """閾値は1要素以上の、正の整数の狭義単調増加でなければならないこと."""
    response = client.post(
        "/api/admin/technologies",
        headers=ADMIN_HEADERS,
        json={"id": "bad_tech", "name": "Bad", "level_thresholds": thresholds},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    response = client.put(
        f"/api/admin/technologies/{BEAM}",
        headers=ADMIN_HEADERS,
        json={"level_thresholds": thresholds},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_admin_rejects_invalid_or_duplicate_id(client: TestClient) -> None:
    """IDの形式が不正なら 422、重複なら 409 になること."""
    body = {"name": "X", "level_thresholds": [1]}
    response = client.post(
        "/api/admin/technologies", headers=ADMIN_HEADERS, json={"id": "Bad-Id", **body}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    response = client.post(
        "/api/admin/technologies", headers=ADMIN_HEADERS, json={"id": BEAM, **body}
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_admin_update_or_delete_missing_technology(client: TestClient) -> None:
    """存在しない技術の編集・削除は 404 になること."""
    response = client.put(
        "/api/admin/technologies/no_such_tech",
        headers=ADMIN_HEADERS,
        json={"name": "X"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response = client.delete(
        "/api/admin/technologies/no_such_tech", headers=ADMIN_HEADERS
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_admin_cannot_lower_max_level_below_requirement(
    client: TestClient, session: Session
) -> None:
    """設計図の必要Lvより最大Lvを下げる変更はできないこと."""
    _require(session, BEAM_RIFLE, [(BEAM, 3)])

    response = client.put(
        f"/api/admin/technologies/{BEAM}",
        headers=ADMIN_HEADERS,
        json={"level_thresholds": [3, 8]},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert BEAM_RIFLE in response.json()["detail"]


def test_admin_cannot_delete_referenced_technology(
    client: TestClient, session: Session
) -> None:
    """購入条件・ドロップテーブルから参照されている技術は削除できないこと."""
    _require(session, BEAM_RIFLE, [(BEAM, 1)])
    _make_table(session, [_tech_entry(PSYCOMMU)])

    for tech_id in (BEAM, PSYCOMMU):
        response = client.delete(
            f"/api/admin/technologies/{tech_id}", headers=ADMIN_HEADERS
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert session.get(MasterTechnology, tech_id) is not None


def test_delete_technology_removes_player_progress(
    client: TestClient, session: Session, pilot: Pilot
) -> None:
    """参照されていない技術を削除すると、プレイヤーの累計数も消えること."""
    _set_fragments(session, BEAM, 5)

    response = client.delete(f"/api/admin/technologies/{BEAM}", headers=ADMIN_HEADERS)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert session.exec(select(PlayerTechnology)).all() == []


# --- ドロップ ---


def test_roll_grants_tech_fragment(session: Session, pilot: Pilot) -> None:
    """技術断片のエントリーが当たると、断片が付与されること."""
    _set_fragments(session, BEAM, 2)
    _make_table(session, [_tech_entry(BEAM)])

    loot = _roll(session)
    session.commit()

    assert [item.model_dump() for item in loot] == [
        {
            "kind": "TECH_FRAGMENT",
            "blueprint_id": None,
            "target_type": None,
            "target_id": None,
            "is_new": False,
            "credits_awarded": 0,
            "tech_id": BEAM,
            "fragment_count": 3,
            "level": 1,
            "max_level": 3,
            "is_level_up": True,
            "fragments_to_next_level": 5,
        }
    ]


def test_roll_tech_fragment_after_max_level(session: Session, pilot: Pilot) -> None:
    """最大Lv後の断片は換金額が戦利品に入ること."""
    _set_fragments(session, BEAM, 15)
    _make_table(session, [_tech_entry(BEAM)])

    loot = _roll(session)

    assert loot[0].credits_awarded == OVERFLOW_CREDITS
    assert loot[0].fragments_to_next_level is None
    assert loot[0].is_level_up is False


def test_tech_fragment_is_not_filtered_by_faction(
    session: Session, pilot: Pilot
) -> None:
    """技術断片は勢力による絞り込みを受けないこと."""
    _require(session, GELGOOG, [])
    _make_table(session, [_blueprint_entry(GELGOOG, weight=100), _tech_entry(BEAM)])

    loot = _roll(session)

    # 連邦のパイロットにはジオン機の設計図が出ないため、断片だけが候補に残る。
    assert [item.kind for item in loot] == ["TECH_FRAGMENT"]


def test_tech_fragment_requires_win(session: Session, pilot: Pilot) -> None:
    """勝利時のみの技術断片は、敗北時に抽選対象にならないこと."""
    _make_table(session, [_tech_entry(BEAM, requires_win=True)])

    assert _roll(session, is_win=False) == []
    assert len(_roll(session, is_win=True)) == 1


def test_candidates_order_is_fixed(session: Session, pilot: Pilot) -> None:
    """候補の順序がエントリーの追加順によらず固定されること."""
    table = _make_table(
        session,
        [_tech_entry(PSYCOMMU), _blueprint_entry(BEAM_RIFLE), _tech_entry(BEAM)],
    )

    candidates = DropService._candidates(session, table, "FEDERATION", is_win=True)

    assert [(c.reward_type, c.blueprint_id, c.tech_id) for c in candidates] == [
        (DropRewardType.BLUEPRINT, BEAM_RIFLE, None),
        (DropRewardType.TECH_FRAGMENT, None, BEAM),
        (DropRewardType.TECH_FRAGMENT, None, PSYCOMMU),
    ]


def test_admin_drop_table_accepts_tech_entries(
    client: TestClient, session: Session
) -> None:
    """ドロップテーブルの保存APIで、技術断片のエントリーを保存・取得できること."""
    response = client.put(
        "/api/admin/drop-tables/batch",
        headers=ADMIN_HEADERS,
        json={
            "name": "定期バトル",
            "drop_rate": 0.5,
            "win_rate_multiplier": 1,
            "entries": [
                {"blueprint_id": BEAM_RIFLE, "weight": 2},
                {"reward_type": "TECH_FRAGMENT", "tech_id": BEAM, "weight": 3},
            ],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    entries = response.json()["entries"]
    assert entries[1] == {
        "reward_type": "TECH_FRAGMENT",
        "blueprint_id": None,
        "target_type": None,
        "target_id": None,
        "tech_id": BEAM,
        "target_name": "ビームジェネレータ技術",
        "faction": "",
        "is_standard_issue": False,
        "weight": 3,
        "requires_win": False,
    }
    assert entries[0]["reward_type"] == "BLUEPRINT"


@pytest.mark.parametrize(
    "entry",
    [
        {"reward_type": "TECH_FRAGMENT", "weight": 1},
        {
            "reward_type": "TECH_FRAGMENT",
            "tech_id": BEAM,
            "blueprint_id": BEAM_RIFLE,
            "weight": 1,
        },
        {"reward_type": "BLUEPRINT", "tech_id": BEAM, "weight": 1},
        {"reward_type": "TECH_FRAGMENT", "tech_id": "no_such_tech", "weight": 1},
    ],
)
def test_admin_drop_table_rejects_invalid_tech_entries(
    client: TestClient, entry: dict
) -> None:
    """種別とIDが合わない、または技術マスターに無いエントリーは保存できないこと."""
    response = client.put(
        "/api/admin/drop-tables/batch",
        headers=ADMIN_HEADERS,
        json={
            "name": "x",
            "drop_rate": 0.5,
            "win_rate_multiplier": 1,
            "entries": [entry],
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_admin_drop_table_rejects_duplicate_tech(client: TestClient) -> None:
    """同じ技術のエントリーを2つ入れられないこと."""
    entry = {"reward_type": "TECH_FRAGMENT", "tech_id": BEAM, "weight": 1}
    response = client.put(
        "/api/admin/drop-tables/batch",
        headers=ADMIN_HEADERS,
        json={
            "name": "x",
            "drop_rate": 0.5,
            "win_rate_multiplier": 1,
            "entries": [entry, entry],
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()["detail"] == f"Duplicate technologies: {BEAM}"


# --- 表示 ---


def test_loot_names_include_tech_name(session: Session) -> None:
    """技術断片の戦利品に技術名が付き、設計図の戦利品と混在できること."""
    tech_loot = LootItem(
        kind="TECH_FRAGMENT",
        tech_id=PSYCOMMU,
        fragment_count=1,
        level=0,
        max_level=3,
        fragments_to_next_level=2,
        credits_awarded=0,
    ).model_dump()
    legacy_blueprint_loot = {
        "kind": "BLUEPRINT",
        "blueprint_id": BEAM_RIFLE,
        "target_type": "WEAPON",
        "target_id": "beam_rifle",
        "is_new": True,
        "credits_awarded": 0,
    }

    [loot] = LootService.with_names(session, [[tech_loot, legacy_blueprint_loot]])

    assert loot is not None
    assert [item.target_name for item in loot] == ["サイコミュ技術", "Beam Rifle"]


def test_collection_shows_tech_requirements(session: Session, pilot: Pilot) -> None:
    """図鑑の設計図に、必要な技術Lvと現在Lvが付くこと."""
    _require(session, BEAM_RIFLE, [(BEAM, 2)])
    _set_fragments(session, BEAM, 3)

    items = BlueprintCollectionService.get_collection(session, USER_ID)

    beam_rifle = next(item for item in items if item.blueprint_id == BEAM_RIFLE)
    assert [r.model_dump() for r in beam_rifle.tech_requirements] == [
        {
            "tech_id": BEAM,
            "tech_name": "ビームジェネレータ技術",
            "required_lv": 2,
            "current_lv": 1,
        }
    ]


def test_get_my_technologies(
    client: TestClient, session: Session, pilot: Pilot, as_user: None
) -> None:
    """GET /api/technologies/me で、技術ごとの進捗と断片の入手先を取得できること."""
    _set_fragments(session, PSYCOMMU, 9)
    _make_table(session, [_tech_entry(PSYCOMMU, requires_win=True)])

    response = client.get("/api/technologies/me")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "tech_id": BEAM,
            "name": "ビームジェネレータ技術",
            "description": "高出力ビーム武器の開発に必要な技術",
            "level": 0,
            "max_level": 3,
            "fragment_count": 0,
            "next_level_threshold": 3,
            "fragments_to_next_level": 3,
            "overflow_credit_value": OVERFLOW_CREDITS,
            "obtainable_theaters": [],
        },
        {
            "tech_id": PSYCOMMU,
            "name": "サイコミュ技術",
            "description": "サイコミュ武器、サイコミュ搭載機体の開発に必要な技術",
            "level": 2,
            "max_level": 3,
            "fragment_count": 9,
            "next_level_threshold": 15,
            "fragments_to_next_level": 6,
            "overflow_credit_value": OVERFLOW_CREDITS,
            "obtainable_theaters": [
                {"label": ALL_THEATERS_LABEL, "requires_win": True}
            ],
        },
    ]


def test_get_my_technologies_requires_auth(client: TestClient) -> None:
    """未認証では技術Lvを取得できないこと."""
    response = client.get("/api/technologies/me")
    assert response.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    )

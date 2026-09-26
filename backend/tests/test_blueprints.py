"""設計図サービス・設計図APIのテスト."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi import status
from sqlalchemy import event
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.models.models import (
    BlueprintSource,
    BlueprintTargetType,
    MasterBlueprint,
    MasterMobileSuit,
    MasterWeapon,
    Pilot,
    PlayerBlueprint,
)
from app.services.blueprint_service import (
    DEFAULT_UNLOCK_HINT,
    BlueprintService,
    UnlockState,
)
from main import app

USER_ID = "test_blueprint_user"
GUNDAM_BLUEPRINT_ID = "mobile_suit:gundam"
BEAM_RIFLE_BLUEPRINT_ID = "weapon:beam_rifle"


@pytest.fixture(name="pilot")
def pilot_fixture(session: Session) -> Pilot:
    """設計図テスト用のパイロットを作成する."""
    pilot = Pilot(user_id=USER_ID, name="Blueprint Pilot", credits=1000)
    session.add(pilot)
    session.commit()
    session.refresh(pilot)
    return pilot


def _make_restricted(session: Session, blueprint_id: str) -> MasterBlueprint:
    blueprint = session.get(MasterBlueprint, blueprint_id)
    assert blueprint is not None
    blueprint.is_standard_issue = False
    session.add(blueprint)
    session.commit()
    return blueprint


def test_blueprint_id_for() -> None:
    """設計図IDが対象の種別と対象IDから決まること."""
    assert (
        BlueprintService.blueprint_id_for(BlueprintTargetType.MOBILE_SUIT, "gundam")
        == GUNDAM_BLUEPRINT_ID
    )
    assert (
        BlueprintService.blueprint_id_for(BlueprintTargetType.WEAPON, "beam_rifle")
        == BEAM_RIFLE_BLUEPRINT_ID
    )


def test_every_master_has_standard_blueprint(session: Session) -> None:
    """全ての機体・武器マスターに標準配備の設計図マスターがあること."""
    blueprints = {b.id: b for b in session.exec(select(MasterBlueprint)).all()}
    ms_ids = [m.id for m in session.exec(select(MasterMobileSuit)).all()]
    weapon_ids = [w.id for w in session.exec(select(MasterWeapon)).all()]

    expected_ids = {f"mobile_suit:{i}" for i in ms_ids} | {
        f"weapon:{i}" for i in weapon_ids
    }
    assert set(blueprints) == expected_ids
    assert all(b.is_standard_issue for b in blueprints.values())


def test_ensure_master_blueprint_keeps_existing(session: Session) -> None:
    """既存の設計図マスターは上書きしないこと."""
    blueprint = _make_restricted(session, GUNDAM_BLUEPRINT_ID)
    blueprint.duplicate_credit_value = 777
    session.add(blueprint)
    session.commit()

    result = BlueprintService.ensure_master_blueprint(
        session, BlueprintTargetType.MOBILE_SUIT, "gundam", 99999
    )

    assert result.is_standard_issue is False
    assert result.duplicate_credit_value == 777


def test_can_purchase_standard_issue(session: Session, pilot: Pilot) -> None:
    """標準配備品は設計図なしで購入できること."""
    assert BlueprintService.can_purchase(
        session, USER_ID, BlueprintTargetType.MOBILE_SUIT, "gundam"
    )


def test_can_purchase_requires_blueprint(session: Session, pilot: Pilot) -> None:
    """標準配備でない品は、設計図を所持したときだけ購入できること."""
    _make_restricted(session, GUNDAM_BLUEPRINT_ID)
    assert not BlueprintService.can_purchase(
        session, USER_ID, BlueprintTargetType.MOBILE_SUIT, "gundam"
    )

    BlueprintService.grant_blueprint(
        session, USER_ID, GUNDAM_BLUEPRINT_ID, BlueprintSource.DROP
    )
    session.commit()

    assert BlueprintService.can_purchase(
        session, USER_ID, BlueprintTargetType.MOBILE_SUIT, "gundam"
    )


def test_can_purchase_without_master_blueprint(session: Session, pilot: Pilot) -> None:
    """設計図マスターが無いアイテムは購入できる扱いになること."""
    assert BlueprintService.can_purchase(
        session, USER_ID, BlueprintTargetType.WEAPON, "no_such_weapon"
    )


def test_grant_new_blueprint(session: Session, pilot: Pilot) -> None:
    """未所持の設計図は所持記録が作られ、クレジットは変わらないこと."""
    battle_id = uuid.uuid4()

    result = BlueprintService.grant_blueprint(
        session, USER_ID, GUNDAM_BLUEPRINT_ID, BlueprintSource.DROP, battle_id
    )
    session.commit()

    assert result.is_new is True
    assert result.credits_awarded == 0
    owned = session.exec(
        select(PlayerBlueprint).where(PlayerBlueprint.user_id == USER_ID)
    ).one()
    assert owned.blueprint_id == GUNDAM_BLUEPRINT_ID
    assert owned.source == "DROP"
    assert owned.source_battle_id == battle_id
    session.refresh(pilot)
    assert pilot.credits == 1000


def test_grant_duplicate_blueprint_awards_credits(
    session: Session, pilot: Pilot
) -> None:
    """所持済みの設計図は換金額分のクレジットが加算されること."""
    blueprint = session.get(MasterBlueprint, GUNDAM_BLUEPRINT_ID)
    assert blueprint is not None
    blueprint.duplicate_credit_value = 250
    session.add(blueprint)
    session.commit()

    BlueprintService.grant_blueprint(
        session, USER_ID, GUNDAM_BLUEPRINT_ID, BlueprintSource.DROP
    )
    result = BlueprintService.grant_blueprint(
        session, USER_ID, GUNDAM_BLUEPRINT_ID, BlueprintSource.DROP
    )
    session.commit()

    assert result.is_new is False
    assert result.credits_awarded == 250
    session.refresh(pilot)
    assert pilot.credits == 1250
    owned = session.exec(
        select(PlayerBlueprint).where(PlayerBlueprint.user_id == USER_ID)
    ).all()
    assert len(owned) == 1


def test_grant_unknown_blueprint_raises(session: Session, pilot: Pilot) -> None:
    """存在しない設計図を付与しようとすると LookupError になること."""
    with pytest.raises(LookupError):
        BlueprintService.grant_blueprint(
            session, USER_ID, "weapon:no_such_weapon", BlueprintSource.DROP
        )


def test_grant_duplicate_without_pilot_raises(session: Session) -> None:
    """所持済みでもパイロットが無ければ LookupError になること."""
    session.add(
        PlayerBlueprint(
            user_id="ghost_user",
            blueprint_id=GUNDAM_BLUEPRINT_ID,
            source="MIGRATION",
        )
    )
    session.commit()

    with pytest.raises(LookupError):
        BlueprintService.grant_blueprint(
            session, "ghost_user", GUNDAM_BLUEPRINT_ID, BlueprintSource.DROP
        )


def test_get_player_blueprints_returns_only_own(session: Session, pilot: Pilot) -> None:
    """所持設計図一覧は本人の分だけを対象情報つきで返すこと."""
    BlueprintService.grant_blueprint(
        session, USER_ID, GUNDAM_BLUEPRINT_ID, BlueprintSource.MIGRATION
    )
    BlueprintService.grant_blueprint(
        session, USER_ID, BEAM_RIFLE_BLUEPRINT_ID, BlueprintSource.DROP
    )
    session.add(
        PlayerBlueprint(
            user_id="other_user",
            blueprint_id="mobile_suit:zaku_ii",
            source="DROP",
        )
    )
    session.commit()

    result = BlueprintService.get_player_blueprints(session, USER_ID)

    by_id = {r.blueprint_id: r for r in result}
    assert set(by_id) == {GUNDAM_BLUEPRINT_ID, BEAM_RIFLE_BLUEPRINT_ID}
    assert by_id[GUNDAM_BLUEPRINT_ID].target_type == "MOBILE_SUIT"
    assert by_id[GUNDAM_BLUEPRINT_ID].target_id == "gundam"
    assert by_id[GUNDAM_BLUEPRINT_ID].source == "MIGRATION"
    assert by_id[BEAM_RIFLE_BLUEPRINT_ID].target_type == "WEAPON"


def test_get_my_blueprints_api(client, session: Session, pilot: Pilot) -> None:
    """GET /api/blueprints/me でログイン中プレイヤーの所持設計図を取得できること."""
    BlueprintService.grant_blueprint(
        session, USER_ID, GUNDAM_BLUEPRINT_ID, BlueprintSource.MIGRATION
    )
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: USER_ID
    try:
        response = client.get("/api/blueprints/me")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["blueprint_id"] == GUNDAM_BLUEPRINT_ID
    assert data[0]["target_type"] == "MOBILE_SUIT"
    assert data[0]["target_id"] == "gundam"
    assert data[0]["source"] == "MIGRATION"
    assert data[0]["source_battle_id"] is None
    assert "acquired_at" in data[0]


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


def test_get_unlock_states(session: Session, pilot: Pilot) -> None:
    """解放状態が標準配備・設計図所持・未解放・設計図マスター無しで区別されること."""
    _make_restricted(session, GUNDAM_BLUEPRINT_ID)
    _make_restricted(session, "mobile_suit:gelgoog")
    _make_restricted(session, "mobile_suit:dom")
    BlueprintService.grant_blueprint(
        session, USER_ID, GUNDAM_BLUEPRINT_ID, BlueprintSource.DROP
    )
    session.add(
        PlayerBlueprint(
            user_id="other_user", blueprint_id="mobile_suit:dom", source="DROP"
        )
    )
    session.commit()

    states = BlueprintService.get_unlock_states(
        session,
        USER_ID,
        BlueprintTargetType.MOBILE_SUIT,
        ["zaku_ii", "gundam", "gelgoog", "dom", "no_such_ms"],
    )

    assert states["zaku_ii"] == UnlockState(
        is_standard_issue=True, is_unlocked=True, unlock_hint=None
    )
    assert states["gundam"] == UnlockState(
        is_standard_issue=False, is_unlocked=True, unlock_hint=None
    )
    assert states["gelgoog"] == UnlockState(
        is_standard_issue=False, is_unlocked=False, unlock_hint=DEFAULT_UNLOCK_HINT
    )
    # 他のプレイヤーの設計図では解放されない。
    assert states["dom"].is_unlocked is False
    assert states["no_such_ms"] == UnlockState(
        is_standard_issue=True, is_unlocked=True, unlock_hint=None
    )


def test_get_unlock_states_ignores_other_target_type(
    session: Session, pilot: Pilot
) -> None:
    """同じ対象IDでも、別の種別の設計図は解放状態に影響しないこと."""
    _make_restricted(session, BEAM_RIFLE_BLUEPRINT_ID)
    session.add(
        MasterBlueprint(
            id="mobile_suit:beam_rifle",
            target_type=BlueprintTargetType.MOBILE_SUIT.value,
            target_id="beam_rifle",
            is_standard_issue=False,
        )
    )
    session.commit()
    BlueprintService.grant_blueprint(
        session, USER_ID, "mobile_suit:beam_rifle", BlueprintSource.DROP
    )
    session.commit()

    states = BlueprintService.get_unlock_states(
        session, USER_ID, BlueprintTargetType.WEAPON, ["beam_rifle"]
    )

    assert states["beam_rifle"].is_unlocked is False


def test_get_unlock_states_query_count_is_constant(
    session: Session, pilot: Pilot
) -> None:
    """解放状態の取得が商品数によらず2回のクエリで済むこと."""
    target_ids = [m.id for m in session.exec(select(MasterMobileSuit)).all()]
    with _recorded_queries(session) as statements:
        BlueprintService.get_unlock_states(
            session, USER_ID, BlueprintTargetType.MOBILE_SUIT, target_ids
        )

    assert len(target_ids) > 2
    assert len(statements) == 2

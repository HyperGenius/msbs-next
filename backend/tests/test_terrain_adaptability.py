"""機体マスターの地形適正と環境タイプのプロファイルのテスト."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.models.models import (
    BattleEntry,
    MasterMobileSuit,
    MasterMobileSuitSpec,
    MasterTheater,
    MobileSuit,
    Pilot,
    Weapon,
)
from app.services.mobile_suit_service import MobileSuitService
from app.services.theater_service import TheaterService
from main import app

GOUF_TERRAIN = {
    "SPACE": "C",
    "GROUND": "A",
    "COLONY": "A",
    "UNDERWATER": "C",
    "FOREST": "S",
}


@pytest.fixture
def pilot(session: Session) -> Pilot:
    """テスト用パイロット."""
    pilot = Pilot(
        user_id="terrain_test_user",
        name="Test Pilot",
        level=1,
        exp=0,
        credits=100000,
    )
    session.add(pilot)
    session.commit()
    session.refresh(pilot)
    return pilot


def _owned_suit(
    session: Session, user_id: str, name: str, master_id: str | None
) -> MobileSuit:
    """ショップ購入と同じく、地形適正を設定しない所持機体を作る."""
    ms = MobileSuit(
        user_id=user_id,
        name=name,
        master_mobile_suit_id=master_id,
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        weapons=[Weapon(id="w", name="W", power=100, range=400, accuracy=60)],
        side="PLAYER",
    )
    session.add(ms)
    session.commit()
    session.refresh(ms)
    return ms


# --- 機体マスター ---


def test_master_spec_terrain_defaults_to_empty() -> None:
    """地形適正は省略できる."""
    spec = MasterMobileSuitSpec(max_hp=100, armor=10, mobility=1.0, weapons=[])
    assert spec.terrain_adaptability == {}


def test_master_spec_rejects_invalid_grade() -> None:
    """S/A/B/C/D 以外のランクは受け付けない."""
    with pytest.raises(ValidationError):
        MasterMobileSuitSpec(
            max_hp=100,
            armor=10,
            mobility=1.0,
            weapons=[],
            terrain_adaptability={"FOREST": "X"},
        )


def test_seed_master_has_terrain(session: Session) -> None:
    """シードデータの機体マスターに地形適正が入っている."""
    gouf = session.get(MasterMobileSuit, "gouf")
    assert gouf is not None
    assert gouf.specs["terrain_adaptability"] == GOUF_TERRAIN


# --- エントリーのスナップショット ---


def test_snapshot_uses_master_terrain(session: Session, pilot: Pilot) -> None:
    """所持機体の列ではなく、機体マスターの地形適正を使う."""
    ms = _owned_suit(session, pilot.user_id, "Gouf", "gouf")
    assert ms.terrain_adaptability.get("FOREST") is None

    snapshot = MobileSuitService.build_entry_snapshot(session, ms)

    assert snapshot["terrain_adaptability"] == GOUF_TERRAIN


def test_snapshot_falls_back_to_master_name(session: Session, pilot: Pilot) -> None:
    """master_mobile_suit_id が無い機体は、機体名でマスターを引く."""
    ms = _owned_suit(session, pilot.user_id, "Gouf", None)

    snapshot = MobileSuitService.build_entry_snapshot(session, ms)

    assert snapshot["terrain_adaptability"] == GOUF_TERRAIN


def test_snapshot_without_master_is_empty(session: Session, pilot: Pilot) -> None:
    """マスターを引けない機体は、全環境で既定ランクになる."""
    ms = _owned_suit(session, pilot.user_id, "Zaku II (Starter)", None)

    snapshot = MobileSuitService.build_entry_snapshot(session, ms)

    assert snapshot["terrain_adaptability"] == {}


def test_entry_api_snapshot_has_master_terrain(
    client: TestClient, session: Session, pilot: Pilot
) -> None:
    """POST /api/entries のスナップショットに機体マスターの地形適正が入る."""
    ms = _owned_suit(session, pilot.user_id, "Gouf", "gouf")

    app.dependency_overrides[get_current_user] = lambda: pilot.user_id
    try:
        response = client.post("/api/entries", json={"mobile_suit_id": str(ms.id)})
        assert response.status_code == status.HTTP_200_OK
        # 同じルームへの再エントリーはスナップショットを上書きする。
        response = client.post("/api/entries", json={"mobile_suit_id": str(ms.id)})
        assert response.status_code == status.HTTP_200_OK
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    entries = session.exec(
        select(BattleEntry).where(BattleEntry.user_id == pilot.user_id)
    ).all()
    assert len(entries) == 1
    assert entries[0].mobile_suit_snapshot["terrain_adaptability"] == GOUF_TERRAIN


# --- API レスポンス ---


def test_shop_listing_includes_terrain(
    client: TestClient, session: Session, pilot: Pilot
) -> None:
    """ショップの機体情報に地形適正が含まれる."""
    app.dependency_overrides[get_current_user] = lambda: pilot.user_id
    try:
        response = client.get("/api/shop/listings")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_200_OK
    listings = {item["id"]: item for item in response.json()}
    assert listings["gouf"]["specs"]["terrain_adaptability"] == GOUF_TERRAIN


def test_garage_uses_master_terrain(
    client: TestClient, session: Session, pilot: Pilot
) -> None:
    """ガレージの機体情報は機体マスターの地形適正を返す."""
    _owned_suit(session, pilot.user_id, "Gouf", "gouf")

    app.dependency_overrides[get_current_user] = lambda: pilot.user_id
    try:
        response = client.get("/api/mobile_suits")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]["terrain_adaptability"] == GOUF_TERRAIN


# --- 環境タイプのプロファイル ---


def test_environment_profile_from_master(session: Session) -> None:
    """環境タイプのマスターからプロファイルを作る."""
    profile = TheaterService.resolve_environment_profile(session, "FOREST")

    assert profile is not None
    assert profile.environment_id == "FOREST"
    assert profile.sensor_range_multiplier == pytest.approx(0.8)
    assert profile.ranged_accuracy_penalty == pytest.approx(0.2)
    assert profile.ranged_penalty_ref_distance == pytest.approx(400.0)
    assert profile.default_obstacle_density == "DENSE"
    assert profile.default_terrain_grade == "A"


@pytest.mark.parametrize("environment_id", [None, "UNKNOWN"])
def test_environment_profile_missing(
    session: Session, environment_id: str | None
) -> None:
    """環境タイプが無ければ None を返す."""
    assert TheaterService.resolve_environment_profile(session, environment_id) is None


def test_battlefield_for_theater(session: Session) -> None:
    """戦域が障害物密度を指定したときだけ BattleField に入れる."""
    jungle = session.get(MasterTheater, "southeast_asia_jungle")
    assert jungle is not None
    assert jungle.obstacle_density is None
    assert "obstacle_density" not in (
        TheaterService.battlefield_for(jungle).model_fields_set
    )

    jungle.obstacle_density = "SPARSE"
    assert TheaterService.battlefield_for(jungle).obstacle_density == "SPARSE"

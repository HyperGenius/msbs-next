"""管理者用のプレイヤーのパイロット・所有機 API（読み取り専用、Issue #705）のテスト."""

import os

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# テスト用APIキーを強制的に設定（conftest より先に上書きするため setdefault ではなく直接代入）
os.environ["ADMIN_API_KEY"] = "test_admin_key_12345"

from app.models.models import MobileSuit, Pilot
from app.services.pilot_service import PilotService
from main import app

HEADERS = {"X-API-Key": "test_admin_key_12345"}


@pytest.fixture(name="client_admin")
def client_admin_fixture(session):
    """管理者テスト用クライアント（DBセッションオーバーライド付き）."""
    from app.db import get_session

    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def _add_suit(session, user_id: str, name: str) -> MobileSuit:
    suit = MobileSuit(
        user_id=user_id,
        name=name,
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        weapons=[],
        master_mobile_suit_id="zaku_ii",
    )
    session.add(suit)
    session.commit()
    session.refresh(suit)
    return suit


@pytest.fixture(name="player")
def player_fixture(session):
    """所有機を2機持つプレイヤーのパイロット."""
    pilot = Pilot(user_id="user_amuro", name="Amuro", level=5, is_npc=False)
    session.add(pilot)
    session.commit()
    session.refresh(pilot)
    return pilot


def test_list_requires_auth(client_admin):
    """APIキーが不正なら 401 を返すこと."""
    response = client_admin.get("/api/admin/players", headers={"X-API-Key": "wrong"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_returns_only_players_with_suit_count(client_admin, session, player):
    """NPC を含めず、所有機の数を返すこと."""
    PilotService(session).create_npc_pilot("Npc Pilot", "AGGRESSIVE")
    _add_suit(session, player.user_id, "Gundam")

    response = client_admin.get("/api/admin/players", headers=HEADERS)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert [entry["name"] for entry in data] == ["Amuro"]
    assert data[0]["user_id"] == "user_amuro"
    assert data[0]["mobile_suit_count"] == 1


def test_list_filters_by_name_case_insensitive(client_admin, session, player):
    """名前の部分一致で、大文字小文字を区別せずに絞り込むこと."""
    session.add(Pilot(user_id="user_char", name="Char", is_npc=False))
    session.commit()

    response = client_admin.get(
        "/api/admin/players", headers=HEADERS, params={"name": "amu"}
    )

    assert [entry["name"] for entry in response.json()] == ["Amuro"]


def test_list_escapes_like_wildcards(client_admin, session, player):
    """名前の % と _ をワイルドカードとして扱わないこと."""
    session.add(Pilot(user_id="user_pct", name="100%", is_npc=False))
    session.commit()

    response = client_admin.get(
        "/api/admin/players", headers=HEADERS, params={"name": "%"}
    )

    assert [entry["name"] for entry in response.json()] == ["100%"]


def test_list_respects_limit(client_admin, session, player):
    """件数を limit までに絞ること."""
    session.add(Pilot(user_id="user_bright", name="Bright", is_npc=False))
    session.commit()

    response = client_admin.get(
        "/api/admin/players", headers=HEADERS, params={"limit": 1}
    )

    assert [entry["name"] for entry in response.json()] == ["Amuro"]


def test_mobile_suits_lists_owned_suits_by_name(client_admin, session, player):
    """所有機を名前順に返し、出撃機体の印を付けること."""
    gundam = _add_suit(session, player.user_id, "Gundam")
    _add_suit(session, player.user_id, "Guncannon")
    _add_suit(session, "user_other", "Other")
    player.active_mobile_suit_id = gundam.id
    session.add(player)
    session.commit()

    response = client_admin.get(
        f"/api/admin/players/{player.id}/mobile-suits", headers=HEADERS
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert [(s["name"], s["is_active"]) for s in data] == [
        ("Guncannon", False),
        ("Gundam", True),
    ]
    assert data[1]["id"] == str(gundam.id)
    assert data[1]["master_mobile_suit_id"] == "zaku_ii"


def test_mobile_suits_rejects_npc_pilot(client_admin, session):
    """NPC のパイロットは 404 を返すこと."""
    npc = PilotService(session).create_npc_pilot("Npc Pilot", "AGGRESSIVE")

    response = client_admin.get(
        f"/api/admin/players/{npc.id}/mobile-suits", headers=HEADERS
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_endpoints_do_not_write(client_admin, session, player):
    """一覧の取得で DB を書き換えないこと（active_mobile_suit_id を設定しない）."""
    _add_suit(session, player.user_id, "Gundam")

    client_admin.get("/api/admin/players", headers=HEADERS)
    client_admin.get(f"/api/admin/players/{player.id}/mobile-suits", headers=HEADERS)

    session.refresh(player)
    assert player.active_mobile_suit_id is None

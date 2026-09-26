"""管理者専用 NPC(Pilot) CRUD API のユニットテスト."""

import os

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# テスト用APIキーを強制的に設定（conftest より先に上書きするため setdefault ではなく直接代入）
os.environ["ADMIN_API_KEY"] = "test_admin_key_12345"

from app.models.models import MobileSuit
from app.services.pilot_service import PilotService
from main import app

ADMIN_KEY = "test_admin_key_12345"
HEADERS = {"X-API-Key": ADMIN_KEY}


@pytest.fixture(name="client_admin")
def client_admin_fixture(session):
    """管理者テスト用クライアント（DBセッションオーバーライド付き）."""
    from app.db import get_session

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="npc_pilot")
def npc_pilot_fixture(session):
    """テスト用NPCパイロットを1体作成する."""
    pilot_service = PilotService(session)
    pilot = pilot_service.create_npc_pilot("Test NPC", "AGGRESSIVE")
    return pilot


@pytest.fixture(name="npc_pilot_with_suit")
def npc_pilot_with_suit_fixture(session, npc_pilot):
    """テスト用NPCパイロットに機体を1体紐付ける."""
    suit = MobileSuit(
        user_id=npc_pilot.user_id,
        name="Test NPC Suit",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        weapons=[],
        side="ENEMY",
        personality="AGGRESSIVE",
    )
    session.add(suit)
    session.commit()
    session.refresh(suit)
    return npc_pilot, suit


# ===================== 認証テスト =====================


def test_list_requires_auth(client_admin):
    """認証なしで一覧取得するとき 401/422 が返ること."""
    response = client_admin.get("/api/admin/npcs")
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, 422)


def test_list_wrong_key(client_admin):
    """不正なAPIキーで 401 が返ること."""
    response = client_admin.get("/api/admin/npcs", headers={"X-API-Key": "wrong_key"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===================== 一覧取得テスト =====================


def test_list_npcs_returns_only_npc_pilots(client_admin, npc_pilot, session):
    """is_npc=False の通常パイロットは一覧に含まれないこと."""
    from app.models.models import Pilot

    session.add(Pilot(user_id="player-1", name="Player One", is_npc=False))
    session.commit()

    response = client_admin.get("/api/admin/npcs", headers=HEADERS)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    names = [entry["name"] for entry in data]
    assert "Test NPC" in names
    assert "Player One" not in names


def test_list_npcs_includes_mobile_suit_count(client_admin, npc_pilot_with_suit):
    """所有機体数が一覧レスポンスに反映されること."""
    pilot, _suit = npc_pilot_with_suit
    response = client_admin.get("/api/admin/npcs", headers=HEADERS)
    assert response.status_code == status.HTTP_200_OK
    entry = next(e for e in response.json() if e["id"] == str(pilot.id))
    assert entry["mobile_suit_count"] == 1


def test_list_npcs_filter_by_personality(client_admin, session):
    """性格タイプで絞り込めること."""
    pilot_service = PilotService(session)
    pilot_service.create_npc_pilot("Aggro NPC", "AGGRESSIVE")
    pilot_service.create_npc_pilot("Sniper NPC", "SNIPER")

    response = client_admin.get(
        "/api/admin/npcs", headers=HEADERS, params={"personality": "SNIPER"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(e["npc_personality"] == "SNIPER" for e in data)
    assert any(e["name"] == "Sniper NPC" for e in data)


def test_list_npcs_filter_by_level_range(client_admin, session):
    """レベル範囲で絞り込めること."""
    pilot_service = PilotService(session)
    low = pilot_service.create_npc_pilot("Low Level NPC", "AGGRESSIVE")
    low.level = 2
    session.add(low)
    high = pilot_service.create_npc_pilot("High Level NPC", "AGGRESSIVE")
    high.level = 20
    session.add(high)
    session.commit()

    response = client_admin.get(
        "/api/admin/npcs",
        headers=HEADERS,
        params={"min_level": 10, "max_level": 30},
    )
    assert response.status_code == status.HTTP_200_OK
    names = [e["name"] for e in response.json()]
    assert "High Level NPC" in names
    assert "Low Level NPC" not in names


def test_list_npcs_ace_only_filter(client_admin, session):
    """ace_only フラグでエース由来NPCを絞り込めること（名前一致判定）."""
    pilot_service = PilotService(session)
    pilot_service.create_npc_pilot("Char Aznable", "AGGRESSIVE")
    pilot_service.create_npc_pilot("Random Grunt", "AGGRESSIVE")

    response = client_admin.get(
        "/api/admin/npcs", headers=HEADERS, params={"ace_only": True}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(e["is_ace"] for e in data)
    assert any(e["name"] == "Char Aznable" for e in data)
    assert not any(e["name"] == "Random Grunt" for e in data)

    response = client_admin.get(
        "/api/admin/npcs", headers=HEADERS, params={"ace_only": False}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(not e["is_ace"] for e in data)
    assert any(e["name"] == "Random Grunt" for e in data)
    assert not any(e["name"] == "Char Aznable" for e in data)


def test_count_owned_mobile_suits_by_user_id(session, npc_pilot_with_suit):
    """複数NPCの所有機体数を一括取得できること（一覧表示のN+1回避用）."""
    pilot, suit = npc_pilot_with_suit
    other_suit = MobileSuit(
        user_id=pilot.user_id,
        name="Second Suit",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        weapons=[],
        side="ENEMY",
    )
    session.add(other_suit)
    session.commit()

    counts = PilotService.count_owned_mobile_suits_by_user_id(
        session, [pilot.user_id, "npc-nonexistent"]
    )
    assert counts[pilot.user_id] == 2
    assert "npc-nonexistent" not in counts
    assert PilotService.count_owned_mobile_suits_by_user_id(session, []) == {}


# ===================== 詳細取得テスト =====================


def test_get_npc_detail(client_admin, npc_pilot_with_suit):
    """NPC詳細取得で所有機体一覧が含まれること."""
    pilot, suit = npc_pilot_with_suit
    response = client_admin.get(f"/api/admin/npcs/{pilot.id}", headers=HEADERS)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(pilot.id)
    assert len(data["mobile_suits"]) == 1
    assert data["mobile_suits"][0]["id"] == str(suit.id)


def test_get_npc_detail_not_found(client_admin):
    """存在しないNPC idの場合 404 が返ること."""
    import uuid

    response = client_admin.get(f"/api/admin/npcs/{uuid.uuid4()}", headers=HEADERS)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_npc_detail_excludes_player_pilot(client_admin, session):
    """is_npc=False のパイロットidを指定した場合 404 が返ること."""
    from app.models.models import Pilot

    player = Pilot(user_id="player-2", name="Player Two", is_npc=False)
    session.add(player)
    session.commit()
    session.refresh(player)

    response = client_admin.get(f"/api/admin/npcs/{player.id}", headers=HEADERS)
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ===================== 更新テスト =====================


def test_update_npc_stats(client_admin, npc_pilot):
    """NPCのexp/credits/level等を更新できること."""
    response = client_admin.put(
        f"/api/admin/npcs/{npc_pilot.id}",
        headers=HEADERS,
        json={"level": 10, "exp": 500, "credits": 99999, "sht": 30},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["level"] == 10
    assert data["exp"] == 500
    assert data["credits"] == 99999
    assert data["sht"] == 30


def test_update_npc_not_found(client_admin):
    """存在しないNPC idを更新しようとした場合 404 が返ること."""
    import uuid

    response = client_admin.put(
        f"/api/admin/npcs/{uuid.uuid4()}", headers=HEADERS, json={"level": 5}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_npc_mobile_suit(client_admin, npc_pilot_with_suit):
    """NPC所有機体のステータスを更新できること."""
    pilot, suit = npc_pilot_with_suit
    response = client_admin.put(
        f"/api/admin/npcs/{pilot.id}/mobile-suits/{suit.id}",
        headers=HEADERS,
        json={"max_hp": 1200, "armor": 70},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["max_hp"] == 1200
    assert data["armor"] == 70


def test_update_npc_mobile_suit_not_owned(client_admin, npc_pilot, session):
    """他のNPCが所有する機体を更新しようとした場合 404 が返ること."""
    other_suit = MobileSuit(
        user_id="npc-other",
        name="Other NPC Suit",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        weapons=[],
        side="ENEMY",
    )
    session.add(other_suit)
    session.commit()
    session.refresh(other_suit)

    response = client_admin.put(
        f"/api/admin/npcs/{npc_pilot.id}/mobile-suits/{other_suit.id}",
        headers=HEADERS,
        json={"max_hp": 1200},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def _weapon_payload(weapon_id: str = "npc_beam_rifle", **overrides) -> dict:
    return {
        "id": weapon_id,
        "name": "Beam Rifle",
        "power": 200,
        "range": 500,
        "accuracy": 80,
        "type": "BEAM",
        **overrides,
    }


def test_get_npc_detail_includes_full_spec(client_admin, npc_pilot_with_suit):
    """NPC詳細の機体に武装・耐性・戦術などの全項目が含まれること."""
    pilot, _suit = npc_pilot_with_suit
    response = client_admin.get(f"/api/admin/npcs/{pilot.id}", headers=HEADERS)
    assert response.status_code == status.HTTP_200_OK
    ms = response.json()["mobile_suits"][0]
    for key in (
        "sensor_range",
        "beam_resistance",
        "physical_resistance",
        "max_en",
        "en_recovery",
        "melee_aptitude",
        "accuracy_bonus",
        "tactics",
        "missing_parts",
        "weapons",
    ):
        assert key in ms


def test_update_npc_mobile_suit_full_spec(client_admin, npc_pilot_with_suit, session):
    """武装・耐性・戦術・欠損部位を含めて更新でき、DBに反映されること."""
    pilot, suit = npc_pilot_with_suit
    response = client_admin.put(
        f"/api/admin/npcs/{pilot.id}/mobile-suits/{suit.id}",
        headers=HEADERS,
        json={
            "name": "Custom Dom",
            "beam_resistance": 0.2,
            "max_en": 1500,
            "melee_aptitude": 1.3,
            "tactics": {"priority": "WEAKEST", "range": "MELEE"},
            "missing_parts": ["LEFT_ARM"],
            "weapons": [_weapon_payload(cooldown_sec=2.5)],
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Custom Dom"
    assert data["beam_resistance"] == 0.2
    assert data["max_en"] == 1500
    assert data["melee_aptitude"] == 1.3
    assert data["tactics"] == {"priority": "WEAKEST", "range": "MELEE"}
    assert data["missing_parts"] == ["LEFT_ARM"]
    assert data["weapons"][0]["id"] == "npc_beam_rifle"
    assert data["weapons"][0]["cooldown_sec"] == 2.5

    session.refresh(suit)
    assert suit.name == "Custom Dom"
    assert suit.missing_parts == ["LEFT_ARM"]
    assert suit.weapons[0]["name"] == "Beam Rifle"


def test_update_npc_mobile_suit_max_hp_resets_current_hp_and_parts(
    client_admin, npc_pilot_with_suit, session
):
    """最大HPを変更すると current_hp が揃い、parts が再生成対象になること."""
    pilot, suit = npc_pilot_with_suit
    suit.current_hp = 300
    suit.normalize_parts()
    session.add(suit)
    session.commit()

    response = client_admin.put(
        f"/api/admin/npcs/{pilot.id}/mobile-suits/{suit.id}",
        headers=HEADERS,
        json={"max_hp": 1000},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["current_hp"] == 1000

    session.refresh(suit)
    assert suit.parts == {}


def test_update_npc_mobile_suit_rejects_empty_weapons(
    client_admin, npc_pilot_with_suit
):
    """武装を空にする更新は 422 になること."""
    pilot, suit = npc_pilot_with_suit
    response = client_admin.put(
        f"/api/admin/npcs/{pilot.id}/mobile-suits/{suit.id}",
        headers=HEADERS,
        json={"weapons": []},
    )
    assert response.status_code == 422


def test_update_npc_mobile_suit_rejects_invalid_missing_parts(
    client_admin, npc_pilot_with_suit
):
    """不正な部位名を欠損部位に指定すると 422 になること."""
    pilot, suit = npc_pilot_with_suit
    response = client_admin.put(
        f"/api/admin/npcs/{pilot.id}/mobile-suits/{suit.id}",
        headers=HEADERS,
        json={"missing_parts": ["TAIL"]},
    )
    assert response.status_code == 422


def test_update_npc_mobile_suit_rejects_player_suit(client_admin, npc_pilot, session):
    """プレイヤー所有機は NPC API から更新できないこと."""
    player_suit = MobileSuit(
        user_id="player-1",
        name="Player Suit",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        weapons=[],
        side="PLAYER",
    )
    session.add(player_suit)
    session.commit()
    session.refresh(player_suit)

    response = client_admin.put(
        f"/api/admin/npcs/{npc_pilot.id}/mobile-suits/{player_suit.id}",
        headers=HEADERS,
        json={"weapons": [_weapon_payload()]},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ===================== 機体追加テスト =====================


@pytest.fixture(name="master_suit")
def master_suit_fixture(session):
    """テスト用の機体マスターを1件作成する."""
    from app.models.models import MasterMobileSuit

    master = MasterMobileSuit(
        id="test_dom",
        name="Dom",
        price=1000,
        description="test",
        specs={
            "max_hp": 950,
            "armor": 60,
            "mobility": 1.2,
            "beam_resistance": 0.05,
            "melee_aptitude": 1.2,
            "missing_parts": [],
            "weapons": [
                {
                    "id": "giant_bazooka",
                    "name": "Giant Bazooka",
                    "power": 250,
                    "range": 450,
                    "accuracy": 70,
                }
            ],
        },
    )
    session.add(master)
    session.commit()
    return master


def test_create_npc_mobile_suit_from_master(
    client_admin, npc_pilot, master_suit, session
):
    """機体マスターを指定して NPC に機体を追加できること."""
    response = client_admin.post(
        f"/api/admin/npcs/{npc_pilot.id}/mobile-suits",
        headers=HEADERS,
        json={"master_mobile_suit_id": "test_dom"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Dom (NPC)"
    assert data["max_hp"] == 950
    assert data["current_hp"] == 950
    assert data["beam_resistance"] == 0.05
    assert data["melee_aptitude"] == 1.2
    assert data["weapons"][0]["id"] == "giant_bazooka"
    assert data["personality"] == "AGGRESSIVE"
    assert data["pilot_name"] == npc_pilot.name
    assert data["tactics"]["range"] == "MELEE"

    owned = PilotService.get_npc_owned_mobile_suits(session, npc_pilot.user_id)
    assert len(owned) == 1
    assert owned[0].side == "ENEMY"


def test_create_npc_mobile_suit_master_not_found(client_admin, npc_pilot):
    """存在しない機体マスターを指定すると 404 になること."""
    response = client_admin.post(
        f"/api/admin/npcs/{npc_pilot.id}/mobile-suits",
        headers=HEADERS,
        json={"master_mobile_suit_id": "no_such_suit"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_npc_mobile_suit_pilot_not_found(client_admin, master_suit):
    """存在しない NPC を指定すると 404 になること."""
    import uuid

    response = client_admin.post(
        f"/api/admin/npcs/{uuid.uuid4()}/mobile-suits",
        headers=HEADERS,
        json={"master_mobile_suit_id": "test_dom"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

"""管理者専用エースパイロット マスターデータ CRUD API のユニットテスト."""

import copy
import os

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import delete

# テスト用APIキーを強制的に設定
os.environ["ADMIN_API_KEY"] = "test_admin_key_12345"

from app.core import gamedata as gd
from app.engine.simulation import _resolve_flanking_skill_level
from app.models.models import AcePilot, MobileSuit, Pilot
from app.services.matching_service import MatchingService
from main import _resolve_npc_pilot_stats, app

ADMIN_KEY = "test_admin_key_12345"
HEADERS = {"X-API-Key": ADMIN_KEY}
ENDPOINT = "/api/admin/ace-pilots"

SAMPLE_ACE = {
    "id": "ace_test_pilot",
    "name": "テストの鬼",
    "pilot_name": "Test Pilot",
    "description": "テスト用エース",
    "personality": "SNIPER",
    "mobile_suit": {
        "name": "Test Gelgoog",
        "max_hp": 1250,
        "armor": 85,
        "mobility": 2.1,
        "sensor_range": 750.0,
        "beam_resistance": 0.2,
        "physical_resistance": 0.1,
        "max_en": 1800,
        "en_recovery": 180,
        "weapons": [
            {
                "id": "ace_test_beam_rifle",
                "name": "Test Beam Rifle",
                "power": 300,
                "range": 650,
                "accuracy": 88,
                "type": "BEAM",
                "optimal_range": 420.0,
                "decay_rate": 0.05,
                "en_cost": 90,
            }
        ],
        "tactics": {"priority": "STRONGEST", "range": "RANGED"},
    },
    "bounty_exp": 600,
    "bounty_credits": 1500,
    "stats": {"sht": 14, "mel": 7, "intel": 12, "ref": 11, "tou": 8, "luk": 9},
    "skills": {"flanking": 1},
}


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


# ===================== 認証 =====================


def test_list_requires_auth(client_admin):
    """認証なしで一覧取得すると 401 が返ること."""
    response = client_admin.get(ENDPOINT)
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, 422)


# ===================== 一覧 =====================


def test_list_returns_seeded_aces(client_admin):
    """移行済みの5体のエースが一覧で返ること."""
    response = client_admin.get(ENDPOINT, headers=HEADERS)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    ids = {a["id"] for a in data}
    assert ids == {
        "ace_char_aznable",
        "ace_ramba_ral",
        "ace_yazan_gable",
        "ace_amuro_ray",
        "ace_haman_karn",
    }
    char = next(a for a in data if a["id"] == "ace_char_aznable")
    assert char["mobile_suit"]["mobility"] == 3.0
    assert char["stats"]["ref"] == 15
    assert char["skills"] == {"flanking": 3}
    # JSON列にはデフォルト値を省略して保存しているが、レスポンスでは補完されること
    assert char["mobile_suit"]["weapons"][0]["en_cost"] == 0


# ===================== 作成 =====================


def test_create_ace(client_admin):
    """新規エースを追加でき、ゲームロジック側のキャッシュにも反映されること."""
    assert gd.get_ace_pilot_by_id("ace_test_pilot") is None

    response = client_admin.post(ENDPOINT, json=SAMPLE_ACE, headers=HEADERS)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["pilot_name"] == "Test Pilot"

    ace = gd.get_ace_pilot_by_id("ace_test_pilot")
    assert ace is not None
    assert ace["mobile_suit"]["weapons"][0].en_cost == 90


def test_saved_weapons_store_only_non_default_fields(client_admin, session):
    """武器JSONは移行データと同じく既定値と異なる項目のみ保存されること."""
    client_admin.post(ENDPOINT, json=SAMPLE_ACE, headers=HEADERS)
    client_admin.put(
        f"{ENDPOINT}/ace_char_aznable",
        json={"mobile_suit": SAMPLE_ACE["mobile_suit"]},
        headers=HEADERS,
    )

    # decay_rate=0.05 は既定値と同じため保存されない
    expected_keys = set(SAMPLE_ACE["mobile_suit"]["weapons"][0]) - {"decay_rate"}
    for ace_id in ("ace_test_pilot", "ace_char_aznable"):
        record = session.get(AcePilot, ace_id)
        assert record is not None
        session.refresh(record)
        assert set(record.mobile_suit["weapons"][0]) == expected_keys


def test_create_duplicate_id_returns_409(client_admin):
    """既存IDで追加すると 409 が返ること."""
    payload = {**SAMPLE_ACE, "id": "ace_char_aznable"}
    response = client_admin.post(ENDPOINT, json=payload, headers=HEADERS)
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.parametrize(
    ("override", "path"),
    [
        ({"id": "Invalid-ID"}, None),
        ({"personality": "BERSERKER"}, None),
        ({"skills": {"unknown_skill": 1}}, None),
        ({"skills": {"flanking": 4}}, None),
        ({"weapons": []}, "mobile_suit"),
        ({"missing_parts": ["TAIL"]}, "mobile_suit"),
    ],
)
def test_create_invalid_returns_422(client_admin, override, path):
    """不正な入力は 422 が返ること."""
    payload = copy.deepcopy(SAMPLE_ACE)
    if path is None:
        payload.update(override)
    else:
        payload[path].update(override)
    response = client_admin.post(ENDPOINT, json=payload, headers=HEADERS)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===================== 更新 =====================


def test_update_ace(client_admin):
    """既存エースを部分更新でき、ゲームロジック側に反映されること."""
    response = client_admin.put(
        f"{ENDPOINT}/ace_char_aznable",
        json={"bounty_exp": 999, "stats": {**SAMPLE_ACE["stats"], "sht": 20}},
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["bounty_exp"] == 999
    assert data["stats"]["sht"] == 20
    # 未指定のフィールドは維持されること
    assert data["name"] == "赤い彗星"

    ace = gd.get_ace_pilot_by_id("ace_char_aznable")
    assert ace is not None
    assert ace["bounty_exp"] == 999


def test_update_not_found_returns_404(client_admin):
    """存在しないIDを更新すると 404 が返ること."""
    response = client_admin.put(
        f"{ENDPOINT}/ace_unknown", json={"bounty_exp": 1}, headers=HEADERS
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_invalid_personality_returns_422(client_admin):
    """不正な性格で更新すると 422 が返ること."""
    response = client_admin.put(
        f"{ENDPOINT}/ace_char_aznable",
        json={"personality": "BERSERKER"},
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===================== 削除 =====================


def test_delete_ace(client_admin):
    """エースを削除でき、ゲームロジック側から参照できなくなること."""
    response = client_admin.delete(f"{ENDPOINT}/ace_haman_karn", headers=HEADERS)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert gd.get_ace_pilot_by_id("ace_haman_karn") is None

    response = client_admin.delete(f"{ENDPOINT}/ace_haman_karn", headers=HEADERS)
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ===================== ゲームロジックとの結合 =====================


def _make_ace_unit(ace_id: str, personality: str) -> MobileSuit:
    return MobileSuit(
        name="Ace Unit",
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=2.0,
        side="ENEMY",
        personality=personality,
        is_ace=True,
        ace_id=ace_id,
    )


def test_deleted_ace_falls_back_to_personality(client_admin):
    """マスターから削除されたエースの生成済み機体は personality ベースで動作すること."""
    unit = _make_ace_unit("ace_ramba_ral", "AGGRESSIVE")
    assert _resolve_flanking_skill_level(unit, False, None) == 3
    assert str(unit.id) in _resolve_npc_pilot_stats([unit])

    client_admin.delete(f"{ENDPOINT}/ace_ramba_ral", headers=HEADERS)

    # フランキング: AGGRESSIVE のフォールバック (Lv.1)
    assert _resolve_flanking_skill_level(unit, False, None) == 1
    # パイロットステータス: 解決されず simulation 側の personality 自動解決に委ねる
    assert _resolve_npc_pilot_stats([unit]) == {}


def test_create_ace_pilot_returns_none_when_master_empty(session):
    """ace_pilots が空の場合はエースを生成しないこと."""
    session.exec(delete(AcePilot))
    session.commit()
    gd.invalidate_ace_pilots_cache()

    assert MatchingService(session)._create_ace_pilot() is None


def test_npc_ace_flag_follows_master(client_admin, session):
    """NPC一覧の is_ace 判定が ace_pilots マスターの pilot_name に追従すること."""
    pilot = Pilot(user_id="npc-ace-test", name="Test Pilot", is_npc=True)
    session.add(pilot)
    session.commit()

    def is_ace() -> bool:
        data = client_admin.get("/api/admin/npcs", headers=HEADERS).json()
        return next(e for e in data if e["user_id"] == "npc-ace-test")["is_ace"]

    assert is_ace() is False
    client_admin.post(ENDPOINT, json=SAMPLE_ACE, headers=HEADERS)
    assert is_ace() is True

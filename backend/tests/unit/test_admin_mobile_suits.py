"""管理者専用マスター機体 CRUD API のユニットテスト."""

import json
import os

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# テスト用APIキーを強制的に設定（.env からの load_dotenv より後に評価される conftest より
# 先に上書きするため setdefault ではなく直接代入を使用）
os.environ["ADMIN_API_KEY"] = "test_admin_key_12345"

from app.core import gamedata as gd
from main import app

ADMIN_KEY = "test_admin_key_12345"
HEADERS = {"X-API-Key": ADMIN_KEY}

SAMPLE_MS = {
    "id": "test_gm",
    "name": "RGM-79 GM (Test)",
    "price": 500,
    "faction": "FEDERATION",
    "description": "テスト用GM。",
    "specs": {
        "max_hp": 750,
        "armor": 45,
        "mobility": 1.1,
        "sensor_range": 520.0,
        "beam_resistance": 0.1,
        "physical_resistance": 0.15,
        "melee_aptitude": 0.9,
        "shooting_aptitude": 1.1,
        "accuracy_bonus": 2.0,
        "evasion_bonus": 0.0,
        "acceleration_bonus": 1.0,
        "turning_bonus": 1.0,
        "weapons": [
            {
                "id": "test_beam_spray_gun",
                "name": "Test Beam Spray Gun",
                "power": 120,
                "range": 450,
                "accuracy": 65,
                "type": "BEAM",
                "optimal_range": 320.0,
                "decay_rate": 0.09,
                "is_melee": False,
            }
        ],
    },
}


@pytest.fixture(autouse=True)
def patch_data_dir(monkeypatch: pytest.MonkeyPatch):
    """各テスト前にキャッシュをリセットして DB シードが反映されるようにする."""
    # DB からロードするため _DATA_DIR パッチは不要になったが、
    # backgrounds.json 用に _DATA_DIR は残す。
    # キャッシュのリセットのみ行う。
    monkeypatch.setattr(gd, "_shop_listings_cache", None)
    monkeypatch.setattr(gd, "_cache_expires_at", None)

    yield

    # テスト後にキャッシュをリセット
    monkeypatch.setattr(gd, "_shop_listings_cache", None)
    monkeypatch.setattr(gd, "_cache_expires_at", None)


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


# ===================== 認証テスト =====================


def test_list_requires_auth(client_admin):
    """認証なしで一覧取得するとき 422 が返ること（ヘッダーなし＝FastAPIバリデーションエラー）."""
    response = client_admin.get("/api/admin/mobile-suits")
    # X-API-Key ヘッダーが必須のため、未指定時は FastAPI が 422 を返す
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, 422)


def test_list_wrong_key(client_admin):
    """不正なAPIキーで 401 が返ること."""
    response = client_admin.get(
        "/api/admin/mobile-suits", headers={"X-API-Key": "wrong_key"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===================== GET 一覧 =====================


def test_list_master_mobile_suits(client_admin):
    """GET /api/admin/mobile-suits が全機体を返すこと."""
    response = client_admin.get("/api/admin/mobile-suits", headers=HEADERS)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # 各エントリーのフィールド確認
    first = data[0]
    assert "id" in first
    assert "name" in first
    assert "price" in first
    assert "specs" in first
    assert "weapons" in first["specs"]


# ===================== POST 新規追加 =====================


def test_create_master_mobile_suit(client_admin):
    """POST /api/admin/mobile-suits で新規機体を追加できること."""
    response = client_admin.post(
        "/api/admin/mobile-suits", json=SAMPLE_MS, headers=HEADERS
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == "test_gm"
    assert data["name"] == "RGM-79 GM (Test)"
    assert data["specs"]["max_hp"] == 750

    # GET で確認
    list_response = client_admin.get("/api/admin/mobile-suits", headers=HEADERS)
    ids = [item["id"] for item in list_response.json()]
    assert "test_gm" in ids


def test_create_duplicate_id_returns_409(client_admin):
    """既存 id を登録しようとすると 409 が返ること."""
    # 最初の追加
    client_admin.post("/api/admin/mobile-suits", json=SAMPLE_MS, headers=HEADERS)
    # 重複追加
    response = client_admin.post(
        "/api/admin/mobile-suits", json=SAMPLE_MS, headers=HEADERS
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_invalid_id_returns_422(client_admin):
    """スネークケース以外の id は 422 が返ること."""
    invalid = {**SAMPLE_MS, "id": "Invalid-ID"}
    response = client_admin.post(
        "/api/admin/mobile-suits", json=invalid, headers=HEADERS
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_empty_weapons_returns_422(client_admin):
    """Weapons が空の場合は 422 が返ること."""
    no_weapons = json.loads(json.dumps(SAMPLE_MS))
    no_weapons["id"] = "no_weapons_ms"
    no_weapons["specs"]["weapons"] = []
    response = client_admin.post(
        "/api/admin/mobile-suits", json=no_weapons, headers=HEADERS
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===================== PUT 更新 =====================


def test_update_master_mobile_suit(client_admin):
    """PUT /api/admin/mobile-suits/{id} で機体を更新できること."""
    # 先に追加
    client_admin.post("/api/admin/mobile-suits", json=SAMPLE_MS, headers=HEADERS)

    update_payload = {
        "name": "RGM-79 GM (Updated)",
        "price": 600,
    }
    response = client_admin.put(
        "/api/admin/mobile-suits/test_gm",
        json=update_payload,
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "RGM-79 GM (Updated)"
    assert data["price"] == 600


def test_update_nonexistent_returns_404(client_admin):
    """存在しない id を更新しようとすると 404 が返ること."""
    response = client_admin.put(
        "/api/admin/mobile-suits/nonexistent_id",
        json={"name": "Ghost"},
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_empty_weapons_returns_422(client_admin):
    """specs.weapons を空にしようとすると 422 が返ること."""
    client_admin.post("/api/admin/mobile-suits", json=SAMPLE_MS, headers=HEADERS)

    update_with_empty_weapons = {
        "specs": {**SAMPLE_MS["specs"], "weapons": []},
    }
    response = client_admin.put(
        "/api/admin/mobile-suits/test_gm",
        json=update_with_empty_weapons,
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===================== DELETE 削除 =====================


def test_delete_master_mobile_suit(client_admin):
    """DELETE /api/admin/mobile-suits/{id} で機体を削除できること."""
    client_admin.post("/api/admin/mobile-suits", json=SAMPLE_MS, headers=HEADERS)

    response = client_admin.delete("/api/admin/mobile-suits/test_gm", headers=HEADERS)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # 削除後は一覧にない
    list_response = client_admin.get("/api/admin/mobile-suits", headers=HEADERS)
    ids = [item["id"] for item in list_response.json()]
    assert "test_gm" not in ids


def test_delete_nonexistent_returns_404(client_admin):
    """存在しない id を削除しようとすると 404 が返ること."""
    response = client_admin.delete(
        "/api/admin/mobile-suits/nonexistent_id", headers=HEADERS
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_referenced_returns_409(client_admin, session):
    """ショップ在庫で参照されている機体を削除しようとすると 409 が返ること."""
    from app.models.models import MobileSuit, Vector3, Weapon

    # 先にマスターに追加
    client_admin.post("/api/admin/mobile-suits", json=SAMPLE_MS, headers=HEADERS)

    # DB に同名機体を登録（ショップ在庫に存在する状態を再現）
    owned_ms = MobileSuit(
        name=SAMPLE_MS["name"],
        max_hp=750,
        current_hp=750,
        armor=45,
        mobility=1.1,
        position=Vector3(x=0, y=0, z=0),
        weapons=[Weapon(id="w1", name="Weapon", power=100, range=400, accuracy=60)],
        side="PLAYER",
        user_id="user_test",
    )
    session.add(owned_ms)
    session.commit()

    response = client_admin.delete("/api/admin/mobile-suits/test_gm", headers=HEADERS)
    assert response.status_code == status.HTTP_409_CONFLICT


# ===================== DB 永続化テスト =====================


def test_create_persists_to_db(client_admin, session):
    """POST で追加した機体が DB に書き込まれること."""
    client_admin.post("/api/admin/mobile-suits", json=SAMPLE_MS, headers=HEADERS)

    from app.models.models import MasterMobileSuit

    record = session.get(MasterMobileSuit, "test_gm")
    assert record is not None
    assert record.name == SAMPLE_MS["name"]


def test_delete_persists_to_db(client_admin, session):
    """DELETE した機体が DB からも消えること."""
    from sqlmodel import select

    client_admin.post("/api/admin/mobile-suits", json=SAMPLE_MS, headers=HEADERS)
    client_admin.delete("/api/admin/mobile-suits/test_gm", headers=HEADERS)

    from app.models.models import MasterMobileSuit

    # select で最新状態を問い合わせる（identity map のキャッシュを回避）
    session.expire_all()
    record = session.exec(
        select(MasterMobileSuit).where(MasterMobileSuit.id == "test_gm")
    ).first()
    assert record is None

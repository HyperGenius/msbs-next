"""管理者専用マスター武器 CRUD API のユニットテスト."""

import json
import os
from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# テスト用APIキーを強制的に設定
os.environ["ADMIN_API_KEY"] = "test_admin_key_12345"

from app.core import gamedata as gd
from main import app

ADMIN_KEY = "test_admin_key_12345"
HEADERS = {"X-API-Key": ADMIN_KEY}

SAMPLE_WEAPON = {
    "id": "test_beam_rifle",
    "name": "Test Beam Rifle",
    "price": 800,
    "description": "テスト用ビームライフル。",
    "weapon": {
        "id": "test_beam_rifle",
        "name": "Test Beam Rifle",
        "power": 150,
        "range": 500,
        "accuracy": 75,
        "type": "BEAM",
        "weapon_type": "RANGED",
        "optimal_range": 320.0,
        "decay_rate": 0.09,
        "is_melee": False,
        "max_ammo": None,
        "en_cost": 10,
        "cool_down_turn": 0,
        "cooldown_sec": 1.0,
        "fire_arc_deg": 30.0,
    },
}


@pytest.fixture(autouse=True)
def patch_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """各テスト前にマスターデータを一時ディレクトリにコピーして隔離する."""
    # オリジナルのマスターデータを読み込む
    original_dir = Path(gd._DATA_DIR)
    orig_json = original_dir / "weapons.json"
    with open(orig_json, encoding="utf-8") as f:
        original_data = json.load(f)

    # 一時ディレクトリにコピー
    tmp_json = tmp_path / "weapons.json"
    with open(tmp_json, mode="w", encoding="utf-8") as f:
        json.dump(original_data, f, ensure_ascii=False, indent=2)

    # gamedata の _DATA_DIR とキャッシュを差し替える
    monkeypatch.setattr(gd, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(gd, "_weapon_shop_listings_cache", None)

    yield

    # テスト後にキャッシュをリセット
    monkeypatch.setattr(gd, "_weapon_shop_listings_cache", None)


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


def test_list_weapons_requires_auth(client_admin):
    """認証なしで一覧取得するとき 401 か 422 が返ること."""
    response = client_admin.get("/api/admin/weapons")
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, 422)


def test_list_weapons_wrong_key(client_admin):
    """不正なAPIキーで 401 が返ること."""
    response = client_admin.get(
        "/api/admin/weapons", headers={"X-API-Key": "wrong_key"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===================== GET 一覧 =====================


def test_list_master_weapons(client_admin):
    """GET /api/admin/weapons が全武器を返すこと."""
    response = client_admin.get("/api/admin/weapons", headers=HEADERS)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # 各エントリーのフィールド確認
    first = data[0]
    assert "id" in first
    assert "name" in first
    assert "price" in first
    assert "description" in first
    assert "weapon" in first


# ===================== POST 新規追加 =====================


def test_create_master_weapon(client_admin):
    """POST /api/admin/weapons で新規武器を追加できること."""
    response = client_admin.post(
        "/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == "test_beam_rifle"
    assert data["name"] == "Test Beam Rifle"
    assert data["weapon"]["power"] == 150

    # GET で確認
    list_response = client_admin.get("/api/admin/weapons", headers=HEADERS)
    ids = [item["id"] for item in list_response.json()]
    assert "test_beam_rifle" in ids


def test_create_duplicate_id_returns_409(client_admin):
    """既存 id を登録しようとすると 409 が返ること."""
    # 最初の追加
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)
    # 重複追加
    response = client_admin.post(
        "/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_invalid_id_returns_422(client_admin):
    """スネークケース以外の id は 422 が返ること."""
    invalid = {**SAMPLE_WEAPON, "id": "Invalid-ID"}
    response = client_admin.post(
        "/api/admin/weapons", json=invalid, headers=HEADERS
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===================== PUT 更新 =====================


def test_update_master_weapon(client_admin):
    """PUT /api/admin/weapons/{id} で武器を更新できること."""
    # 先に追加
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)

    update_payload = {
        "name": "Test Beam Rifle (Updated)",
        "price": 900,
    }
    response = client_admin.put(
        "/api/admin/weapons/test_beam_rifle",
        json=update_payload,
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Test Beam Rifle (Updated)"
    assert data["price"] == 900


def test_update_weapon_stats(client_admin):
    """PUT /api/admin/weapons/{id} で weapon サブフィールドを更新できること."""
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)

    updated_weapon = {**SAMPLE_WEAPON["weapon"], "power": 200}
    update_payload = {"weapon": updated_weapon}
    response = client_admin.put(
        "/api/admin/weapons/test_beam_rifle",
        json=update_payload,
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["weapon"]["power"] == 200


def test_update_nonexistent_returns_404(client_admin):
    """存在しない id を更新しようとすると 404 が返ること."""
    response = client_admin.put(
        "/api/admin/weapons/nonexistent_id",
        json={"name": "Ghost"},
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ===================== DELETE 削除 =====================


def test_delete_master_weapon(client_admin):
    """DELETE /api/admin/weapons/{id} で武器を削除できること."""
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)

    response = client_admin.delete("/api/admin/weapons/test_beam_rifle", headers=HEADERS)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # 削除後は一覧にない
    list_response = client_admin.get("/api/admin/weapons", headers=HEADERS)
    ids = [item["id"] for item in list_response.json()]
    assert "test_beam_rifle" not in ids


def test_delete_nonexistent_returns_404(client_admin):
    """存在しない id を削除しようとすると 404 が返ること."""
    response = client_admin.delete(
        "/api/admin/weapons/nonexistent_id", headers=HEADERS
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_referenced_returns_409(client_admin, session):
    """パイロットのインベントリで参照されている武器を削除しようとすると 409 が返ること."""
    from app.models.models import Pilot

    # 先にマスターに追加
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)

    # DB にインベントリに武器IDを持つパイロットを登録
    pilot = Pilot(
        user_id="user_test_weapon",
        name="Test Pilot",
        faction="FEDERATION",
        inventory={"test_beam_rifle": 1},
    )
    session.add(pilot)
    session.commit()

    response = client_admin.delete(
        "/api/admin/weapons/test_beam_rifle", headers=HEADERS
    )
    assert response.status_code == status.HTTP_409_CONFLICT


# ===================== JSON 永続化テスト =====================


def test_create_persists_to_json(client_admin, tmp_path):
    """POST で追加した武器が JSON ファイルに書き込まれること."""
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)

    # gamedata._DATA_DIR は monkeypatch で tmp_path に差し替え済み
    json_path = gd._DATA_DIR / "weapons.json"
    with open(json_path, encoding="utf-8") as f:
        saved = json.load(f)

    ids = [item["id"] for item in saved]
    assert "test_beam_rifle" in ids


def test_delete_persists_to_json(client_admin, tmp_path):
    """DELETE した武器が JSON ファイルからも消えること."""
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)
    client_admin.delete("/api/admin/weapons/test_beam_rifle", headers=HEADERS)

    json_path = gd._DATA_DIR / "weapons.json"
    with open(json_path, encoding="utf-8") as f:
        saved = json.load(f)

    ids = [item["id"] for item in saved]
    assert "test_beam_rifle" not in ids

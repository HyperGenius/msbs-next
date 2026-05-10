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
    "id": "test_beam_cannon",
    "name": "Test Beam Cannon",
    "price": 600,
    "description": "テスト用ビームカノン。",
    "weapon": {
        "id": "test_beam_cannon",
        "name": "Test Beam Cannon",
        "power": 250,
        "range": 550,
        "accuracy": 70,
        "type": "BEAM",
        "weapon_type": "RANGED",
        "optimal_range": 400.0,
        "decay_rate": 0.06,
        "is_melee": False,
        "max_ammo": None,
        "en_cost": 30,
        "cool_down_turn": 0,
        "cooldown_sec": 2.0,
        "fire_arc_deg": 30.0,
    },
}


@pytest.fixture(autouse=True)
def patch_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """各テスト前にマスターデータを一時ディレクトリにコピーして隔離する."""
    original_dir = Path(gd._DATA_DIR)
    orig_json = original_dir / "weapons.json"
    with open(orig_json, encoding="utf-8") as f:
        original_data = json.load(f)

    tmp_json = tmp_path / "weapons.json"
    with open(tmp_json, mode="w", encoding="utf-8") as f:
        json.dump(original_data, f, ensure_ascii=False, indent=2)

    # mobile_suits.json も一時ディレクトリにコピー（他テストとの干渉防止）
    orig_ms_json = original_dir / "mobile_suits.json"
    with open(orig_ms_json, encoding="utf-8") as f:
        ms_data = json.load(f)
    tmp_ms_json = tmp_path / "mobile_suits.json"
    with open(tmp_ms_json, mode="w", encoding="utf-8") as f:
        json.dump(ms_data, f, ensure_ascii=False, indent=2)

    # backgrounds.json も一時ディレクトリにコピー
    orig_bg_json = original_dir / "backgrounds.json"
    if orig_bg_json.exists():
        with open(orig_bg_json, encoding="utf-8") as f:
            bg_data = json.load(f)
        tmp_bg_json = tmp_path / "backgrounds.json"
        with open(tmp_bg_json, mode="w", encoding="utf-8") as f:
            json.dump(bg_data, f, ensure_ascii=False, indent=2)

    monkeypatch.setattr(gd, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(gd, "_weapon_shop_listings_cache", None)
    monkeypatch.setattr(gd, "_shop_listings_cache", None)

    yield

    monkeypatch.setattr(gd, "_weapon_shop_listings_cache", None)
    monkeypatch.setattr(gd, "_shop_listings_cache", None)


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
    """認証なしで一覧取得するとき 422 or 401 が返ること."""
    response = client_admin.get("/api/admin/weapons")
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, 422)


def test_list_wrong_key(client_admin):
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
    assert "weapon" in first
    assert "power" in first["weapon"]
    assert "range" in first["weapon"]
    assert "accuracy" in first["weapon"]


# ===================== POST 新規追加 =====================


def test_create_master_weapon(client_admin):
    """POST /api/admin/weapons で新規武器を追加できること."""
    response = client_admin.post(
        "/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == "test_beam_cannon"
    assert data["name"] == "Test Beam Cannon"
    assert data["weapon"]["power"] == 250

    # GET で確認
    list_response = client_admin.get("/api/admin/weapons", headers=HEADERS)
    ids = [item["id"] for item in list_response.json()]
    assert "test_beam_cannon" in ids


def test_create_duplicate_id_returns_409(client_admin):
    """既存 id を登録しようとすると 409 が返ること."""
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)
    response = client_admin.post(
        "/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_invalid_id_returns_422(client_admin):
    """スネークケース以外の id は 422 が返ること."""
    invalid = {**SAMPLE_WEAPON, "id": "Invalid-Weapon-ID"}
    response = client_admin.post(
        "/api/admin/weapons", json=invalid, headers=HEADERS
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===================== PUT 更新 =====================


def test_update_master_weapon(client_admin):
    """PUT /api/admin/weapons/{id} で武器を更新できること."""
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)

    update_payload = {
        "name": "Test Beam Cannon (Updated)",
        "price": 750,
    }
    response = client_admin.put(
        "/api/admin/weapons/test_beam_cannon",
        json=update_payload,
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Test Beam Cannon (Updated)"
    assert data["price"] == 750


def test_update_weapon_stats(client_admin):
    """PUT で武器スペックを更新できること."""
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)

    updated_weapon = {**SAMPLE_WEAPON["weapon"], "power": 999}
    update_payload = {"weapon": updated_weapon}
    response = client_admin.put(
        "/api/admin/weapons/test_beam_cannon",
        json=update_payload,
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["weapon"]["power"] == 999


def test_update_nonexistent_returns_404(client_admin):
    """存在しない id を更新しようとすると 404 が返ること."""
    response = client_admin.put(
        "/api/admin/weapons/nonexistent_id",
        json={"name": "Ghost Weapon"},
        headers=HEADERS,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ===================== DELETE 削除 =====================


def test_delete_master_weapon(client_admin):
    """DELETE /api/admin/weapons/{id} で武器を削除できること."""
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)

    response = client_admin.delete(
        "/api/admin/weapons/test_beam_cannon", headers=HEADERS
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # 削除後は一覧にない
    list_response = client_admin.get("/api/admin/weapons", headers=HEADERS)
    ids = [item["id"] for item in list_response.json()]
    assert "test_beam_cannon" not in ids


def test_delete_nonexistent_returns_404(client_admin):
    """存在しない id を削除しようとすると 404 が返ること."""
    response = client_admin.delete(
        "/api/admin/weapons/nonexistent_id", headers=HEADERS
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_referenced_returns_409(client_admin, session):
    """player_weapons テーブルで参照されている武器を削除しようとすると 409 が返ること."""
    from app.models.models import PlayerWeapon

    # 先にマスターに追加
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)

    # player_weapons テーブルに参照行を追加
    pw = PlayerWeapon(
        user_id="user_test",
        master_weapon_id="test_beam_cannon",
        base_snapshot=SAMPLE_WEAPON["weapon"],
        custom_stats={},
    )
    session.add(pw)
    session.commit()

    response = client_admin.delete(
        "/api/admin/weapons/test_beam_cannon", headers=HEADERS
    )
    assert response.status_code == status.HTTP_409_CONFLICT


# ===================== JSON 永続化テスト =====================


def test_create_persists_to_json(client_admin, tmp_path):
    """POST で追加した武器が JSON ファイルに書き込まれること."""
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)

    json_path = gd._DATA_DIR / "weapons.json"
    with open(json_path, encoding="utf-8") as f:
        saved = json.load(f)

    ids = [item["id"] for item in saved]
    assert "test_beam_cannon" in ids


def test_delete_persists_to_json(client_admin, tmp_path):
    """DELETE した武器が JSON ファイルからも消えること."""
    client_admin.post("/api/admin/weapons", json=SAMPLE_WEAPON, headers=HEADERS)
    client_admin.delete("/api/admin/weapons/test_beam_cannon", headers=HEADERS)

    json_path = gd._DATA_DIR / "weapons.json"
    with open(json_path, encoding="utf-8") as f:
        saved = json.load(f)

    ids = [item["id"] for item in saved]
    assert "test_beam_cannon" not in ids

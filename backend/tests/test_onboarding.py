"""パイロット登録（オンボーディング）のAPIテスト."""

import uuid

from fastapi import status

from app.core.auth import get_current_user
from app.models.models import MobileSuit, Pilot
from main import app


def test_register_pilot_federation_success(client, session):
    """連邦軍パイロットの登録が成功し、GM Trainerが付与されることをテスト."""
    test_user_id = "test_register_fed"
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post(
            "/api/pilots/register",
            json={"name": "Amuro Ray", "faction": "FEDERATION"},
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "pilot" in data
        assert "mobile_suit_id" in data
        assert "message" in data

        pilot = data["pilot"]
        assert pilot["name"] == "Amuro Ray"
        assert pilot["faction"] == "FEDERATION"
        assert pilot["credits"] == 1000

        # 機体が作成されていることを確認
        ms_id = uuid.UUID(data["mobile_suit_id"])
        ms = session.get(MobileSuit, ms_id)
        assert ms is not None
        assert "GM Trainer" in ms.name
        assert ms.user_id == test_user_id
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_register_pilot_zeon_success(client, session):
    """ジオン軍パイロットの登録が成功し、Zaku II Trainerが付与されることをテスト."""
    test_user_id = "test_register_zeon"
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post(
            "/api/pilots/register",
            json={"name": "Char Aznable", "faction": "ZEON"},
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        pilot = data["pilot"]
        assert pilot["name"] == "Char Aznable"
        assert pilot["faction"] == "ZEON"

        ms_id = uuid.UUID(data["mobile_suit_id"])
        ms = session.get(MobileSuit, ms_id)
        assert ms is not None
        assert "Zaku II Trainer" in ms.name
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_register_pilot_trainer_stats_equal(client, session):
    """連邦・ジオン練習機のステータスが完全に同一であることをテスト."""
    # 連邦パイロット
    fed_user_id = "test_stats_fed"
    app.dependency_overrides[get_current_user] = lambda: fed_user_id
    res_fed = client.post(
        "/api/pilots/register",
        json={"name": "Fed Pilot", "faction": "FEDERATION"},
    )
    assert res_fed.status_code == status.HTTP_200_OK
    ms_fed = session.get(MobileSuit, uuid.UUID(res_fed.json()["mobile_suit_id"]))

    # ジオンパイロット
    zeon_user_id = "test_stats_zeon"
    app.dependency_overrides[get_current_user] = lambda: zeon_user_id
    res_zeon = client.post(
        "/api/pilots/register",
        json={"name": "Zeon Pilot", "faction": "ZEON"},
    )
    assert res_zeon.status_code == status.HTTP_200_OK
    ms_zeon = session.get(MobileSuit, uuid.UUID(res_zeon.json()["mobile_suit_id"]))

    # ステータスが同一であることを確認
    assert ms_fed.max_hp == ms_zeon.max_hp
    assert ms_fed.armor == ms_zeon.armor
    assert ms_fed.mobility == ms_zeon.mobility

    app.dependency_overrides.pop(get_current_user, None)


def test_register_pilot_duplicate_error(client, session):
    """既存のパイロットが存在する場合に登録失敗することをテスト."""
    test_user_id = "test_register_dup"
    pilot = Pilot(
        user_id=test_user_id,
        name="Existing",
        level=1,
        exp=0,
        credits=1000,
        faction="FEDERATION",
    )
    session.add(pilot)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post(
            "/api/pilots/register",
            json={"name": "New Pilot", "faction": "ZEON"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_register_pilot_invalid_faction(client, session):
    """無効な勢力を指定した場合にエラーになることをテスト."""
    test_user_id = "test_register_invalid_faction"
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post(
            "/api/pilots/register",
            json={"name": "Test Pilot", "faction": "INVALID"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid faction" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_register_pilot_invalid_name_too_short(client, session):
    """短すぎるパイロット名でエラーになることをテスト."""
    test_user_id = "test_register_short_name"
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post(
            "/api/pilots/register",
            json={"name": "A", "faction": "FEDERATION"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "2 and 15 characters" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)

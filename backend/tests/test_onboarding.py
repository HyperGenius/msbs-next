"""パイロット登録（オンボーディング）のAPIテスト."""

import uuid

from fastapi import status

from app.core.auth import get_current_user
from app.models.models import MobileSuit, Pilot
from main import app

# テスト用の有効なリクエストボディのベース
_BASE_REGISTER_BODY = {
    "faction": "FEDERATION",
    "background": "ACADEMY_ELITE",
    "bonus_dex": 2,
    "bonus_int": 1,
    "bonus_ref": 1,
    "bonus_tou": 1,
}


def test_register_pilot_federation_success(client, session):
    """連邦軍パイロットの登録が成功し、GM Trainerが付与されることをテスト."""
    test_user_id = "test_register_fed"
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post(
            "/api/pilots/register",
            json={"name": "Amuro Ray", **_BASE_REGISTER_BODY},
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "pilot" in data
        assert "mobile_suit_id" in data
        assert "message" in data

        pilot = data["pilot"]
        assert pilot["name"] == "Amuro Ray"
        assert pilot["faction"] == "FEDERATION"
        assert pilot["background"] == "ACADEMY_ELITE"
        assert pilot["credits"] == 1000

        # 経歴 + ボーナスによる初期ステータスの確認 (ACADEMY_ELITE: DEX=10, bonus=2 → 12)
        assert pilot["dex"] == 12
        assert pilot["intel"] == 9
        assert pilot["ref"] == 13
        assert pilot["tou"] == 11

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
            json={
                "name": "Char Aznable",
                "faction": "ZEON",
                "background": "STREET_SURVIVOR",
                "bonus_dex": 1,
                "bonus_int": 1,
                "bonus_ref": 2,
                "bonus_tou": 1,
            },
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        pilot = data["pilot"]
        assert pilot["name"] == "Char Aznable"
        assert pilot["faction"] == "ZEON"
        assert pilot["background"] == "STREET_SURVIVOR"

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
        json={"name": "Fed Pilot", **_BASE_REGISTER_BODY},
    )
    assert res_fed.status_code == status.HTTP_200_OK
    ms_fed = session.get(MobileSuit, uuid.UUID(res_fed.json()["mobile_suit_id"]))

    # ジオンパイロット
    zeon_user_id = "test_stats_zeon"
    app.dependency_overrides[get_current_user] = lambda: zeon_user_id
    res_zeon = client.post(
        "/api/pilots/register",
        json={
            "name": "Zeon Pilot",
            "faction": "ZEON",
            "background": "EX_MECHANIC",
            "bonus_dex": 0,
            "bonus_int": 2,
            "bonus_ref": 2,
            "bonus_tou": 1,
        },
    )
    assert res_zeon.status_code == status.HTTP_200_OK
    ms_zeon = session.get(MobileSuit, uuid.UUID(res_zeon.json()["mobile_suit_id"]))

    # 機体ステータスが同一であることを確認（経歴は機体に影響しない）
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
        background="ACADEMY_ELITE",
    )
    session.add(pilot)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post(
            "/api/pilots/register",
            json={"name": "New Pilot", "faction": "ZEON", **_BASE_REGISTER_BODY, "faction": "ZEON"},
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
            json={
                "name": "Test Pilot",
                "faction": "INVALID",
                "background": "ACADEMY_ELITE",
                "bonus_dex": 2,
                "bonus_int": 1,
                "bonus_ref": 1,
                "bonus_tou": 1,
            },
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
            json={"name": "A", **_BASE_REGISTER_BODY},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "2 and 15 characters" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_register_pilot_invalid_background(client, session):
    """無効な経歴を指定した場合にエラーになることをテスト."""
    test_user_id = "test_register_invalid_bg"
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post(
            "/api/pilots/register",
            json={
                "name": "Test Pilot",
                "faction": "FEDERATION",
                "background": "INVALID_BACKGROUND",
                "bonus_dex": 2,
                "bonus_int": 1,
                "bonus_ref": 1,
                "bonus_tou": 1,
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid background" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_register_pilot_invalid_bonus_total(client, session):
    """ボーナスポイントの合計が5でない場合にエラーになることをテスト."""
    test_user_id = "test_register_invalid_bonus"
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post(
            "/api/pilots/register",
            json={
                "name": "Test Pilot",
                "faction": "FEDERATION",
                "background": "ACADEMY_ELITE",
                "bonus_dex": 3,
                "bonus_int": 1,
                "bonus_ref": 1,
                "bonus_tou": 1,
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "5" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_register_pilot_negative_bonus(client, session):
    """ボーナスポイントに負の値を指定した場合にエラーになることをテスト."""
    test_user_id = "test_register_negative_bonus"
    app.dependency_overrides[get_current_user] = lambda: test_user_id

    try:
        response = client.post(
            "/api/pilots/register",
            json={
                "name": "Test Pilot",
                "faction": "FEDERATION",
                "background": "ACADEMY_ELITE",
                "bonus_dex": -1,
                "bonus_int": 2,
                "bonus_ref": 3,
                "bonus_tou": 1,
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "non-negative" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


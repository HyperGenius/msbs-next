"""機体一覧フィルタリングのテスト."""

from fastapi import status

from app.core.auth import get_current_user
from app.models.models import MobileSuit, Pilot
from main import app


def test_get_mobile_suits_returns_only_user_suits(client, session):
    """ログインユーザーの機体のみが返却されることをテスト."""
    # ユーザー1とそのパイロット、機体を作成
    user1_id = "test_user_1"
    pilot1 = Pilot(
        user_id=user1_id,
        name="Pilot 1",
        level=1,
        exp=0,
        credits=1000,
    )
    session.add(pilot1)

    ms1_user1 = MobileSuit(
        user_id=user1_id,
        name="Gundam 1",
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=1.0,
    )
    ms2_user1 = MobileSuit(
        user_id=user1_id,
        name="Gundam 2",
        max_hp=120,
        current_hp=120,
        armor=12,
        mobility=1.1,
    )
    session.add(ms1_user1)
    session.add(ms2_user1)

    # ユーザー2とそのパイロット、機体を作成
    user2_id = "test_user_2"
    pilot2 = Pilot(
        user_id=user2_id,
        name="Pilot 2",
        level=1,
        exp=0,
        credits=1000,
    )
    session.add(pilot2)

    ms1_user2 = MobileSuit(
        user_id=user2_id,
        name="Zaku 1",
        max_hp=80,
        current_hp=80,
        armor=8,
        mobility=0.9,
    )
    session.add(ms1_user2)

    # NPC機体を作成（user_id が None）
    npc_ms = MobileSuit(
        user_id=None,
        name="NPC Gundam",
        max_hp=150,
        current_hp=150,
        armor=15,
        mobility=1.2,
    )
    session.add(npc_ms)

    session.commit()

    # ユーザー1として認証
    app.dependency_overrides[get_current_user] = lambda: user1_id

    try:
        response = client.get("/api/mobile_suits")
        assert response.status_code == status.HTTP_200_OK

        mobile_suits = response.json()
        assert len(mobile_suits) == 2  # ユーザー1の機体のみ

        # 返された機体がユーザー1のものであることを確認
        suit_names = [ms["name"] for ms in mobile_suits]
        assert "Gundam 1" in suit_names
        assert "Gundam 2" in suit_names
        assert "Zaku 1" not in suit_names
        assert "NPC Gundam" not in suit_names

        # user_idが正しいことを確認
        for ms in mobile_suits:
            assert ms["user_id"] == user1_id
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_mobile_suits_excludes_npc_suits(client, session):
    """NPC機体（user_id=NULL）が含まれないことをテスト."""
    user_id = "test_user_3"
    pilot = Pilot(
        user_id=user_id,
        name="Pilot 3",
        level=1,
        exp=0,
        credits=1000,
    )
    session.add(pilot)

    # ユーザーの機体を作成
    user_ms = MobileSuit(
        user_id=user_id,
        name="User Gundam",
        max_hp=100,
        current_hp=100,
        armor=10,
        mobility=1.0,
    )
    session.add(user_ms)

    # NPC機体を複数作成
    for i in range(3):
        npc_ms = MobileSuit(
            user_id=None,
            name=f"NPC Enemy {i}",
            max_hp=100,
            current_hp=100,
            armor=10,
            mobility=1.0,
        )
        session.add(npc_ms)

    session.commit()

    # 認証
    app.dependency_overrides[get_current_user] = lambda: user_id

    try:
        response = client.get("/api/mobile_suits")
        assert response.status_code == status.HTTP_200_OK

        mobile_suits = response.json()
        assert len(mobile_suits) == 1  # ユーザーの機体のみ
        assert mobile_suits[0]["name"] == "User Gundam"
        assert mobile_suits[0]["user_id"] == user_id
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_mobile_suits_requires_authentication(client, session):
    """認証なしでアクセスすると401エラーが返ることをテスト."""
    response = client.get("/api/mobile_suits")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_mobile_suits_returns_empty_list_for_no_suits(client, session):
    """機体を所有していないユーザーの場合、空のリストが返ることをテスト."""
    user_id = "test_user_no_suits"
    pilot = Pilot(
        user_id=user_id,
        name="Pilot No Suits",
        level=1,
        exp=0,
        credits=1000,
    )
    session.add(pilot)
    session.commit()

    # 認証
    app.dependency_overrides[get_current_user] = lambda: user_id

    try:
        response = client.get("/api/mobile_suits")
        assert response.status_code == status.HTTP_200_OK

        mobile_suits = response.json()
        assert len(mobile_suits) == 0
        assert mobile_suits == []
    finally:
        app.dependency_overrides.pop(get_current_user, None)

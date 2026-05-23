"""フレンド機能のテスト."""

from unittest.mock import AsyncMock, patch

from app.core.auth import get_current_user
from app.models.models import Friendship, Pilot
from main import app

# --- Tests ---


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_send_friend_request(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """フレンドリクエストを送信できる."""
    app.dependency_overrides[get_current_user] = lambda: "user_a"
    try:
        response = client.post(
            "/api/friends/request",
            json={"friend_user_id": "user_b"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user_a"
        assert data["friend_user_id"] == "user_b"
        assert data["status"] == "PENDING"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_accept_friend_request(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """フレンドリクエストを承認できる."""
    friendship = Friendship(
        user_id="user_a",
        friend_user_id="user_b",
        status="PENDING",
    )
    session.add(friendship)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_b"
    try:
        response = client.post(
            "/api/friends/accept",
            json={"friend_user_id": "user_a"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ACCEPTED"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_reject_friend_request(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """フレンドリクエストを拒否できる."""
    friendship = Friendship(
        user_id="user_a",
        friend_user_id="user_b",
        status="PENDING",
    )
    session.add(friendship)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_b"
    try:
        response = client.post(
            "/api/friends/reject",
            json={"friend_user_id": "user_a"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "リクエストを拒否しました"

        # DBから削除されていることを確認
        from sqlmodel import select

        result = session.exec(select(Friendship)).all()
        assert len(result) == 0
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_list_friends(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """フレンド一覧を取得できる."""
    friendship = Friendship(
        user_id="user_a",
        friend_user_id="user_b",
        status="ACCEPTED",
    )
    session.add(friendship)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"
    try:
        response = client.get("/api/friends/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "ACCEPTED"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_remove_friend(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """フレンドを解除できる."""
    friendship = Friendship(
        user_id="user_a",
        friend_user_id="user_b",
        status="ACCEPTED",
    )
    session.add(friendship)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"
    try:
        response = client.delete("/api/friends/user_b")
        assert response.status_code == 200
        assert response.json()["message"] == "フレンドを解除しました"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_list_pending_requests(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """受信中のフレンドリクエスト一覧を取得できる."""
    f1 = Friendship(user_id="user_c", friend_user_id="user_a", status="PENDING")
    f2 = Friendship(user_id="user_d", friend_user_id="user_a", status="PENDING")
    session.add(f1)
    session.add(f2)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"
    try:
        response = client.get("/api/friends/requests")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_cannot_friend_self(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """自分自身にフレンドリクエストは送れない."""
    app.dependency_overrides[get_current_user] = lambda: "user_a"
    try:
        response = client.post(
            "/api/friends/request",
            json={"friend_user_id": "user_a"},
        )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_duplicate_friend_request(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """既にリクエスト済みの場合はエラーになる."""
    friendship = Friendship(
        user_id="user_a",
        friend_user_id="user_b",
        status="PENDING",
    )
    session.add(friendship)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"
    try:
        response = client.post(
            "/api/friends/request",
            json={"friend_user_id": "user_b"},
        )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_friend_response_includes_pilot_name(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """フレンド情報にパイロット名が含まれる."""
    pilot = Pilot(user_id="user_b", name="Amuro Ray")
    session.add(pilot)
    friendship = Friendship(
        user_id="user_a",
        friend_user_id="user_b",
        status="ACCEPTED",
    )
    session.add(friendship)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"
    try:
        response = client.get("/api/friends/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["pilot_name"] == "Amuro Ray"
    finally:
        app.dependency_overrides.pop(get_current_user, None)

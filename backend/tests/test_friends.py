"""フレンド機能のテスト."""

from unittest.mock import AsyncMock, patch

from app.models.models import Friendship, Pilot


# --- Helper ---


def _override_auth(client, user_id: str):  # noqa: ANN001, ANN202
    """テスト用に認証をオーバーライドする."""
    from app.core.auth import get_current_user

    from main import app

    app.dependency_overrides[get_current_user] = lambda: user_id
    return client


# --- Tests ---


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_send_friend_request(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """フレンドリクエストを送信できる."""
    from app.core.auth import get_current_user

    from main import app

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.post(
        "/api/friends/request",
        json={"friend_user_id": "user_b"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user_a"
    assert data["friend_user_id"] == "user_b"
    assert data["status"] == "PENDING"

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_accept_friend_request(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """フレンドリクエストを承認できる."""
    from app.core.auth import get_current_user

    from main import app

    # まずリクエストを作成
    friendship = Friendship(
        user_id="user_a",
        friend_user_id="user_b",
        status="PENDING",
    )
    session.add(friendship)
    session.commit()

    # user_b として承認
    app.dependency_overrides[get_current_user] = lambda: "user_b"

    response = client.post(
        "/api/friends/accept",
        json={"friend_user_id": "user_a"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACCEPTED"

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_reject_friend_request(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """フレンドリクエストを拒否できる."""
    from app.core.auth import get_current_user

    from main import app

    friendship = Friendship(
        user_id="user_a",
        friend_user_id="user_b",
        status="PENDING",
    )
    session.add(friendship)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_b"

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

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_list_friends(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """フレンド一覧を取得できる."""
    from app.core.auth import get_current_user

    from main import app

    # ACCEPTED なフレンドを作成
    friendship = Friendship(
        user_id="user_a",
        friend_user_id="user_b",
        status="ACCEPTED",
    )
    session.add(friendship)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.get("/api/friends/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "ACCEPTED"

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_remove_friend(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """フレンドを解除できる."""
    from app.core.auth import get_current_user

    from main import app

    friendship = Friendship(
        user_id="user_a",
        friend_user_id="user_b",
        status="ACCEPTED",
    )
    session.add(friendship)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.delete("/api/friends/user_b")
    assert response.status_code == 200
    assert response.json()["message"] == "フレンドを解除しました"

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_list_pending_requests(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """受信中のフレンドリクエスト一覧を取得できる."""
    from app.core.auth import get_current_user

    from main import app

    f1 = Friendship(user_id="user_c", friend_user_id="user_a", status="PENDING")
    f2 = Friendship(user_id="user_d", friend_user_id="user_a", status="PENDING")
    session.add(f1)
    session.add(f2)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.get("/api/friends/requests")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_cannot_friend_self(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """自分自身にフレンドリクエストは送れない."""
    from app.core.auth import get_current_user

    from main import app

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.post(
        "/api/friends/request",
        json={"friend_user_id": "user_a"},
    )
    assert response.status_code == 400

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_duplicate_friend_request(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """既にリクエスト済みの場合はエラーになる."""
    from app.core.auth import get_current_user

    from main import app

    friendship = Friendship(
        user_id="user_a",
        friend_user_id="user_b",
        status="PENDING",
    )
    session.add(friendship)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.post(
        "/api/friends/request",
        json={"friend_user_id": "user_b"},
    )
    assert response.status_code == 400

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_friend_response_includes_pilot_name(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """フレンド情報にパイロット名が含まれる."""
    from app.core.auth import get_current_user

    from main import app

    # パイロットを作成
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

    response = client.get("/api/friends/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["pilot_name"] == "Amuro Ray"

    app.dependency_overrides.clear()

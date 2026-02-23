"""チーム機能のテスト."""

from unittest.mock import AsyncMock, patch

from app.models.models import BattleRoom, MobileSuit, Team, TeamMember, Weapon

# --- Tests ---


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_create_team(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """チームを作成できる."""
    from app.core.auth import get_current_user
    from main import app

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.post("/api/teams/create", json={"name": "Alpha Team"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Alpha Team"
    assert data["owner_user_id"] == "user_a"
    assert data["status"] == "FORMING"
    assert len(data["members"]) == 1
    assert data["members"][0]["user_id"] == "user_a"

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_invite_member(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """チームにメンバーを招待できる."""
    from app.core.auth import get_current_user
    from main import app

    # チームを作成
    team = Team(owner_user_id="user_a", name="Test Team")
    session.add(team)
    session.flush()
    member = TeamMember(team_id=team.id, user_id="user_a")
    session.add(member)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.post(
        f"/api/teams/{team.id}/invite",
        json={"user_id": "user_b"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["members"]) == 2

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_invite_limit(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """チームの上限（3人）を超える招待はエラーになる."""
    from app.core.auth import get_current_user
    from main import app

    team = Team(owner_user_id="user_a", name="Full Team")
    session.add(team)
    session.flush()
    for uid in ["user_a", "user_b", "user_c"]:
        session.add(TeamMember(team_id=team.id, user_id=uid))
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.post(
        f"/api/teams/{team.id}/invite",
        json={"user_id": "user_d"},
    )
    assert response.status_code == 400
    assert "上限" in response.json()["detail"]

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_set_ready_toggle(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """Ready 状態をトグルできる."""
    from app.core.auth import get_current_user
    from main import app

    team = Team(owner_user_id="user_a", name="Ready Team")
    session.add(team)
    session.flush()
    m1 = TeamMember(team_id=team.id, user_id="user_a", is_ready=False)
    m2 = TeamMember(team_id=team.id, user_id="user_b", is_ready=False)
    session.add(m1)
    session.add(m2)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    # Ready をON
    response = client.post(f"/api/teams/{team.id}/ready")
    assert response.status_code == 200
    data = response.json()
    me = [m for m in data["members"] if m["user_id"] == "user_a"][0]
    assert me["is_ready"] is True
    assert data["status"] == "FORMING"  # まだ全員 Ready ではない

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_all_ready_updates_team_status(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """全員 Ready でチームステータスが READY になる."""
    from app.core.auth import get_current_user
    from main import app

    team = Team(owner_user_id="user_a", name="All Ready Team")
    session.add(team)
    session.flush()
    m1 = TeamMember(team_id=team.id, user_id="user_a", is_ready=True)
    m2 = TeamMember(team_id=team.id, user_id="user_b", is_ready=False)
    session.add(m1)
    session.add(m2)
    session.commit()

    # user_b が Ready に
    app.dependency_overrides[get_current_user] = lambda: "user_b"

    response = client.post(f"/api/teams/{team.id}/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_leave_team(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """チームを離脱できる."""
    from app.core.auth import get_current_user
    from main import app

    team = Team(owner_user_id="user_a", name="Leave Team")
    session.add(team)
    session.flush()
    m1 = TeamMember(team_id=team.id, user_id="user_a")
    m2 = TeamMember(team_id=team.id, user_id="user_b")
    session.add(m1)
    session.add(m2)
    session.commit()

    # user_b が離脱
    app.dependency_overrides[get_current_user] = lambda: "user_b"

    response = client.delete(f"/api/teams/{team.id}/leave")
    assert response.status_code == 200
    assert response.json()["message"] == "チームを離脱しました"

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_owner_leave_disbands_team(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """オーナーが離脱するとチームが解散される."""
    from app.core.auth import get_current_user
    from main import app

    team = Team(owner_user_id="user_a", name="Disband Team")
    session.add(team)
    session.flush()
    m1 = TeamMember(team_id=team.id, user_id="user_a")
    m2 = TeamMember(team_id=team.id, user_id="user_b")
    session.add(m1)
    session.add(m2)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.delete(f"/api/teams/{team.id}/leave")
    assert response.status_code == 200
    assert response.json()["message"] == "チームを解散しました"

    # チームが DISBANDED になっていることを確認
    session.refresh(team)
    assert team.status == "DISBANDED"

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_get_current_team(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """現在のチームを取得できる."""
    from app.core.auth import get_current_user
    from main import app

    team = Team(owner_user_id="user_a", name="Current Team")
    session.add(team)
    session.flush()
    m = TeamMember(team_id=team.id, user_id="user_a")
    session.add(m)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.get("/api/teams/current")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Current Team"

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_get_current_team_none(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """チーム未所属の場合 null が返る."""
    from app.core.auth import get_current_user
    from main import app

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.get("/api/teams/current")
    assert response.status_code == 200
    assert response.json() is None

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_team_entry(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """チーム単位でエントリーできる."""
    from datetime import UTC, datetime, timedelta

    from app.core.auth import get_current_user
    from main import app

    # ルームを作成
    room = BattleRoom(
        status="OPEN",
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session.add(room)

    # チームを作成（READY 状態）
    team = Team(owner_user_id="user_a", name="Entry Team", status="READY")
    session.add(team)
    session.flush()
    m1 = TeamMember(team_id=team.id, user_id="user_a", is_ready=True)
    m2 = TeamMember(team_id=team.id, user_id="user_b", is_ready=True)
    session.add(m1)
    session.add(m2)

    # 機体を作成
    ms_a = MobileSuit(
        user_id="user_a",
        name="Gundam",
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.0,
        weapons=[Weapon(id="w1", name="Beam Rifle", power=100, range=500, accuracy=80)],
    )
    ms_b = MobileSuit(
        user_id="user_b",
        name="GM",
        max_hp=800,
        current_hp=800,
        armor=40,
        mobility=1.2,
        side="PLAYER",
        weapons=[Weapon(id="w2", name="Machine Gun", power=60, range=400, accuracy=70)],
    )
    session.add(ms_a)
    session.add(ms_b)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.post(
        "/api/teams/entry",
        json={"team_id": str(team.id), "mobile_suit_id": str(ms_a.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert "entry_ids" in data
    assert len(data["entry_ids"]) == 2

    app.dependency_overrides.clear()


@patch("app.core.auth.verify_clerk_token", new_callable=AsyncMock)
def test_cannot_create_team_if_already_in_one(mock_verify, client, session):  # noqa: ANN001, ANN201, ARG001
    """既にチームに所属している場合は新しいチームを作成できない."""
    from app.core.auth import get_current_user
    from main import app

    team = Team(owner_user_id="user_a", name="Existing Team")
    session.add(team)
    session.flush()
    m = TeamMember(team_id=team.id, user_id="user_a")
    session.add(m)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: "user_a"

    response = client.post("/api/teams/create", json={"name": "New Team"})
    assert response.status_code == 400
    assert "既にチームに所属" in response.json()["detail"]

    app.dependency_overrides.clear()

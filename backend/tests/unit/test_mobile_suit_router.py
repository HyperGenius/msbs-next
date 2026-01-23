"""Unit tests for mobile suit router."""

from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


@patch("app.routers.mobile_suits.mobile_suit_service.get_all_mobile_suits")
@patch("app.routers.mobile_suits.get_supabase")
def test_get_mobile_suits_endpoint(
    mock_get_supabase: MagicMock, mock_get_all: MagicMock
) -> None:
    """Test GET /api/mobile_suits endpoint."""
    # Setup mocks
    mock_supabase = MagicMock()
    mock_get_supabase.return_value = mock_supabase

    mock_get_all.return_value = [
        {
            "id": "uuid1",
            "name": "Gundam",
            "max_hp": 1500,
            "armor": 100,
            "mobility": 1.2,
        },
        {"id": "uuid2", "name": "Zaku", "max_hp": 1000, "armor": 50, "mobility": 1.0},
    ]

    # Execute
    response = client.get("/api/mobile_suits")

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Gundam"
    assert data[1]["name"] == "Zaku"


@patch("app.routers.mobile_suits.mobile_suit_service.update_mobile_suit")
@patch("app.routers.mobile_suits.get_supabase")
def test_update_mobile_suit_endpoint(
    mock_get_supabase: MagicMock, mock_update: MagicMock
) -> None:
    """Test PUT /api/mobile_suits/{ms_id} endpoint."""
    # Setup mocks
    mock_supabase = MagicMock()
    mock_get_supabase.return_value = mock_supabase

    mock_update.return_value = {
        "id": "uuid1",
        "name": "Updated Gundam",
        "max_hp": 1600,
        "armor": 120,
        "mobility": 1.3,
    }

    # Execute
    update_data = {
        "name": "Updated Gundam",
        "max_hp": 1600,
        "armor": 120,
        "mobility": 1.3,
    }
    response = client.put("/api/mobile_suits/uuid1", json=update_data)

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Gundam"
    assert data["max_hp"] == 1600
    assert data["armor"] == 120
    assert data["mobility"] == 1.3


@patch("app.routers.mobile_suits.mobile_suit_service.update_mobile_suit")
@patch("app.routers.mobile_suits.get_supabase")
def test_update_mobile_suit_partial(
    mock_get_supabase: MagicMock, mock_update: MagicMock
) -> None:
    """Test PUT /api/mobile_suits/{ms_id} with partial update."""
    # Setup mocks
    mock_supabase = MagicMock()
    mock_get_supabase.return_value = mock_supabase

    mock_update.return_value = {
        "id": "uuid1",
        "name": "Gundam",
        "max_hp": 1800,
        "armor": 100,
        "mobility": 1.2,
    }

    # Execute - only update max_hp
    update_data = {"max_hp": 1800}
    response = client.put("/api/mobile_suits/uuid1", json=update_data)

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["max_hp"] == 1800


@patch("app.routers.mobile_suits.mobile_suit_service.update_mobile_suit")
@patch("app.routers.mobile_suits.get_supabase")
def test_update_mobile_suit_not_found(
    mock_get_supabase: MagicMock, mock_update: MagicMock
) -> None:
    """Test PUT /api/mobile_suits/{ms_id} when mobile suit doesn't exist."""
    # Setup mocks
    mock_supabase = MagicMock()
    mock_get_supabase.return_value = mock_supabase

    mock_update.side_effect = HTTPException(
        status_code=404, detail="Mobile Suit not found"
    )

    # Execute
    update_data = {"name": "Updated Gundam"}
    response = client.put("/api/mobile_suits/nonexistent", json=update_data)

    # Verify
    assert response.status_code == 404
    assert "Mobile Suit not found" in response.json()["detail"]

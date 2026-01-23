"""Unit tests for mobile suit service."""

from unittest.mock import MagicMock, Mock

import pytest
from fastapi import HTTPException

from app.models.models import MobileSuitUpdate
from app.services.mobile_suit_service import get_all_mobile_suits, update_mobile_suit


def test_get_all_mobile_suits_success() -> None:
    """Test successful retrieval of all mobile suits."""
    # Mock Supabase client
    mock_supabase = MagicMock()
    mock_response = Mock()
    mock_response.data = [
        {
            "id": "uuid1",
            "name": "Gundam",
            "max_hp": 1500,
            "armor": 100,
            "mobility": 1.2,
        },
        {"id": "uuid2", "name": "Zaku", "max_hp": 1000, "armor": 50, "mobility": 1.0},
    ]

    mock_supabase.table.return_value.select.return_value.execute.return_value = (
        mock_response
    )

    # Execute
    result = get_all_mobile_suits(mock_supabase)

    # Verify
    assert len(result) == 2
    assert result[0]["name"] == "Gundam"
    assert result[1]["name"] == "Zaku"
    mock_supabase.table.assert_called_once_with("mobile_suits")


def test_get_all_mobile_suits_error() -> None:
    """Test error handling when fetching mobile suits fails."""
    # Mock Supabase client to raise an exception
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.execute.side_effect = (
        Exception("Database error")
    )

    # Execute and verify
    with pytest.raises(HTTPException) as exc_info:
        get_all_mobile_suits(mock_supabase)

    assert exc_info.value.status_code == 500
    assert "Failed to fetch mobile suits" in exc_info.value.detail


def test_update_mobile_suit_success() -> None:
    """Test successful mobile suit update."""
    # Mock Supabase client
    mock_supabase = MagicMock()

    # Mock existence check
    mock_exists_response = Mock()
    mock_exists_response.data = [{"id": "uuid1"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        mock_exists_response
    )

    # Mock update
    mock_update_response = Mock()
    mock_update_response.data = [
        {
            "id": "uuid1",
            "name": "Updated Gundam",
            "max_hp": 1600,
            "armor": 120,
            "mobility": 1.3,
        }
    ]
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        mock_update_response
    )

    # Execute
    update_data = MobileSuitUpdate(
        name="Updated Gundam", max_hp=1600, armor=120, mobility=1.3
    )
    result = update_mobile_suit(mock_supabase, "uuid1", update_data)

    # Verify
    assert result["name"] == "Updated Gundam"
    assert result["max_hp"] == 1600
    assert result["armor"] == 120
    assert result["mobility"] == 1.3


def test_update_mobile_suit_not_found() -> None:
    """Test update when mobile suit doesn't exist."""
    # Mock Supabase client
    mock_supabase = MagicMock()

    # Mock existence check - no data found
    mock_exists_response = Mock()
    mock_exists_response.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        mock_exists_response
    )

    # Execute and verify
    update_data = MobileSuitUpdate(name="Updated Gundam")
    with pytest.raises(HTTPException) as exc_info:
        update_mobile_suit(mock_supabase, "nonexistent-uuid", update_data)

    assert exc_info.value.status_code == 404
    assert "Mobile Suit not found" in exc_info.value.detail


def test_update_mobile_suit_no_fields() -> None:
    """Test update when no fields are provided."""
    # Mock Supabase client
    mock_supabase = MagicMock()

    # Execute and verify
    update_data = MobileSuitUpdate()
    with pytest.raises(HTTPException) as exc_info:
        update_mobile_suit(mock_supabase, "uuid1", update_data)

    assert exc_info.value.status_code == 400
    assert "No fields to update" in exc_info.value.detail


def test_update_mobile_suit_partial_update() -> None:
    """Test partial mobile suit update (only some fields)."""
    # Mock Supabase client
    mock_supabase = MagicMock()

    # Mock existence check
    mock_exists_response = Mock()
    mock_exists_response.data = [{"id": "uuid1"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        mock_exists_response
    )

    # Mock update
    mock_update_response = Mock()
    mock_update_response.data = [
        {"id": "uuid1", "name": "Gundam", "max_hp": 1700, "armor": 100, "mobility": 1.2}
    ]
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        mock_update_response
    )

    # Execute - only update max_hp
    update_data = MobileSuitUpdate(max_hp=1700)
    result = update_mobile_suit(mock_supabase, "uuid1", update_data)

    # Verify
    assert result["max_hp"] == 1700
    # Other fields should remain unchanged
    assert result["name"] == "Gundam"
    assert result["armor"] == 100

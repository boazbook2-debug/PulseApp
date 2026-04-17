import os
import pytest
from unittest.mock import patch, MagicMock


def test_connect_button_redirects_to_oura():
    """Connect button URL must point to Oura's OAuth authorization endpoint."""
    from auth import get_auth_url
    with patch.dict(os.environ, {"OURA_CLIENT_ID": "test_client_id"}):
        url = get_auth_url()
    assert "cloud.ouraring.com/oauth/authorize" in url
    assert "test_client_id" in url


def test_access_token_saved_in_supabase():
    """After successful OAuth the access token must be stored in Supabase."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with patch("database.get_client", return_value=mock_client):
        from database import save_user
        save_user("test@example.com", "access_123", "refresh_456", "Test User")

    insert_call = mock_client.table.return_value.insert.call_args
    assert insert_call is not None
    inserted_data = insert_call[0][0]
    assert inserted_data["oura_access_token"] == "access_123"
    assert inserted_data["email"] == "test@example.com"


def test_saved_token_calls_oura_personal_info():
    """Saved access token must successfully call Oura personal info endpoint and return user name."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"full_name": "Boaz Test", "email": "boaz@example.com"}
    mock_response.raise_for_status = MagicMock()

    with patch("auth.requests.get", return_value=mock_response) as mock_get:
        from auth import get_user_info
        user = get_user_info("access_123")

    mock_get.assert_called_once()
    call_kwargs = mock_get.call_args
    assert "Authorization" in call_kwargs[1]["headers"]
    assert call_kwargs[1]["headers"]["Authorization"] == "Bearer access_123"
    assert user["full_name"] == "Boaz Test"

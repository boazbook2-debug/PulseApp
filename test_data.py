import pytest
from unittest.mock import patch, MagicMock


def test_fetch_returns_data_keyed_by_date():
    """fetch_all_oura_data returns a dict keyed by date strings."""
    mock_sleep = [{"day": "2026-04-01", "score": 85, "contributors": {"restfulness": 80, "timing": 70}}]
    mock_readiness = [{"day": "2026-04-01", "score": 90, "contributors": {}, "temperature_deviation": 0.1}]
    mock_activity = [{"day": "2026-04-01", "score": 75, "steps": 8000, "active_calories": 400,
                      "total_calories": 2200, "equivalent_walking_distance": 6000}]

    def fake_get(endpoint, token, start, end):
        if endpoint == "daily_sleep":
            return mock_sleep
        if endpoint == "daily_readiness":
            return mock_readiness
        if endpoint == "daily_activity":
            return mock_activity
        return []

    with patch("oura_fetcher._get", side_effect=fake_get):
        from oura_fetcher import fetch_all_oura_data
        result = fetch_all_oura_data("fake_token")

    assert "2026-04-01" in result
    assert result["2026-04-01"]["sleep_score"] == 85
    assert result["2026-04-01"]["readiness_score"] == 90
    assert result["2026-04-01"]["steps"] == 8000


def test_save_oura_data_inserts_new_record():
    """save_oura_data inserts a new row when none exists for that user+date."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

    with patch("database.get_client", return_value=mock_client):
        from database import save_oura_data
        save_oura_data("user-123", "2026-04-01", {"sleep_score": 85, "steps": 8000})

    mock_client.table.return_value.insert.assert_called_once()


def test_save_oura_data_updates_existing_record():
    """save_oura_data updates the row when one already exists for that user+date."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{"id": 1}]

    with patch("database.get_client", return_value=mock_client):
        from database import save_oura_data
        save_oura_data("user-123", "2026-04-01", {"sleep_score": 90})

    mock_client.table.return_value.update.assert_called_once()

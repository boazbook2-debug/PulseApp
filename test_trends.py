import pytest
from unittest.mock import patch, MagicMock


SAMPLE_ROWS = [
    {"date": f"2026-03-{str(d).zfill(2)}", "sleep_score": 75 + d, "readiness_score": 70 + d,
     "activity_score": 80, "total_sleep_duration": 28800, "hrv_average": 90 + d,
     "resting_heart_rate": 48, "steps": 8000, "spo2_average": 96.0,
     "stress_day_summary": "normal", "resilience_level": "solid"}
    for d in range(1, 16)
]


def test_detect_trends_returns_list():
    """detect_trends returns a list of trend dicts."""
    mock_choice = MagicMock()
    mock_choice.message.content = '[{"headline":"Test","description":"Desc","category":"Sleep","direction":"positive","metrics_involved":["sleep_score"]}]'
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("trend_detector.Groq") as MockClient, \
         patch.dict("os.environ", {"GROQ_API_KEY": "test_key"}):
        MockClient.return_value.chat.completions.create.return_value = mock_completion
        from trend_detector import detect_trends
        result = detect_trends(SAMPLE_ROWS)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["headline"] == "Test"


def test_detect_trends_returns_empty_for_no_data():
    """detect_trends returns empty list when no rows provided."""
    from trend_detector import detect_trends
    result = detect_trends([])
    assert result == []


def test_detect_trends_each_has_required_fields():
    """Each trend has headline, description, category, direction."""
    mock_choice = MagicMock()
    mock_choice.message.content = '''[
        {"headline":"H1","description":"D1","category":"Sleep","direction":"positive","metrics_involved":["sleep_score"]},
        {"headline":"H2","description":"D2","category":"Cardiovascular","direction":"negative","metrics_involved":["hrv_average"]}
    ]'''
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("trend_detector.Groq") as MockClient, \
         patch.dict("os.environ", {"GROQ_API_KEY": "test_key"}):
        MockClient.return_value.chat.completions.create.return_value = mock_completion
        from trend_detector import detect_trends
        result = detect_trends(SAMPLE_ROWS)

    for trend in result:
        assert "headline" in trend
        assert "description" in trend
        assert "category" in trend
        assert "direction" in trend

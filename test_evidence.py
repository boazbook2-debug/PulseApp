"""Tests for evidence label mapping and personal baseline calculation."""
import pytest
from unittest.mock import MagicMock, patch


# ── Evidence label tests ───────────────────────────────────────────────────────

from pubmed import get_evidence_label, EVIDENCE_LABELS


def test_evidence_label_slider_0():
    label, strength = get_evidence_label(0)
    assert "Meta" in label or "Systematic" in label


def test_evidence_label_slider_2():
    label, _ = get_evidence_label(2)
    assert "Randomised" in label or "RCT" in label or "Controlled" in label


def test_evidence_label_slider_4():
    label, _ = get_evidence_label(4)
    assert "Observational" in label or "cohort" in label.lower()


def test_evidence_label_slider_6():
    label, _ = get_evidence_label(6)
    assert label  # any non-empty string


def test_evidence_label_slider_8():
    label, _ = get_evidence_label(8)
    assert "Emerging" in label or "Exploratory" in label or "Speculative" in label


def test_evidence_label_slider_10():
    # 10 falls in the (8, 11) bucket
    label, strength = get_evidence_label(10)
    assert label  # non-empty


def test_evidence_label_above_range():
    label, strength = get_evidence_label(99)
    assert label == "Research"
    assert strength == ""


def test_evidence_label_all_slider_positions():
    """All 0-10 slider values must return a non-empty label string."""
    for v in range(11):
        label, strength = get_evidence_label(v)
        assert isinstance(label, str) and label


# ── Baseline calculation tests ─────────────────────────────────────────────────

from database import get_user_baselines, get_history_stats


def _mock_client(rows=None, count=0):
    """Helper: returns a mock Supabase client that yields given rows."""
    mock = MagicMock()
    execute = MagicMock()
    execute.data = rows or []
    execute.count = count
    mock.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = execute
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value = execute
    mock.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = execute
    return mock


def test_get_user_baselines_averages_correctly():
    rows = [
        {"readiness_score": 80, "sleep_score": 85, "hrv_average": 40,
         "resting_heart_rate": 55, "deep_sleep_duration": 5400, "total_sleep_duration": 27000},
        {"readiness_score": 70, "sleep_score": 75, "hrv_average": 30,
         "resting_heart_rate": 60, "deep_sleep_duration": 3600, "total_sleep_duration": 25200},
        # None for hrv_average — should be excluded from average
        {"readiness_score": 90, "sleep_score": 90, "hrv_average": None,
         "resting_heart_rate": 50, "deep_sleep_duration": 7200, "total_sleep_duration": 28800},
    ]
    with patch("database.get_client", return_value=_mock_client(rows=rows)):
        result = get_user_baselines("user-1")

    assert result["readiness_score"] == pytest.approx(80.0)
    assert result["sleep_score"] == pytest.approx(83.33, rel=0.01)
    # hrv_average: only two valid values (40 + 30) / 2 = 35
    assert result["hrv_average"] == pytest.approx(35.0)
    assert result["resting_heart_rate"] == pytest.approx(55.0)


def test_get_user_baselines_empty_returns_empty_dict():
    with patch("database.get_client", return_value=_mock_client(rows=[])):
        result = get_user_baselines("user-nobody")
    assert result == {}


def test_get_user_baselines_exception_returns_empty_dict():
    mock = MagicMock()
    mock.table.side_effect = RuntimeError("DB offline")
    with patch("database.get_client", return_value=mock):
        result = get_user_baselines("user-1")
    assert result == {}


def test_get_history_stats_returns_correct_values():
    """Mocking the two separate queries: earliest date + count."""
    earliest_execute = MagicMock()
    earliest_execute.data = [{"date": "2023-03-15"}]

    count_execute = MagicMock()
    count_execute.data = []
    count_execute.count = 847

    mock = MagicMock()
    # First call (earliest): table.select.eq.order.limit.execute
    mock.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = earliest_execute
    # Second call (count): table.select.eq.execute
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value = count_execute

    with patch("database.get_client", return_value=mock):
        result = get_history_stats("user-1")

    assert result["earliest_date"] == "2023-03-15"
    assert result["total_days"] == 847


def test_get_history_stats_no_data():
    with patch("database.get_client", return_value=_mock_client(rows=[], count=0)):
        result = get_history_stats("user-nobody")
    assert result["total_days"] == 0
    assert result["earliest_date"] is None

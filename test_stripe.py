"""Tests for Stripe integration — session verification and database access helpers."""
import pytest
from unittest.mock import MagicMock, patch


# ── stripe_handler tests ───────────────────────────────────────────────────────

from stripe_handler import verify_session


def _mock_paid_session(email="boaz@test.com", subscription_id="sub_123"):
    session = MagicMock()
    session.payment_status = "paid"
    session.customer_details.email = email
    session.subscription = subscription_id
    return session


def test_verify_session_paid_returns_email():
    with patch("stripe.checkout.Session.retrieve", return_value=_mock_paid_session()):
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_abc"}):
            result = verify_session("cs_test_123")
    assert result["email"] == "boaz@test.com"


def test_verify_session_paid_returns_subscription_id():
    with patch("stripe.checkout.Session.retrieve", return_value=_mock_paid_session()):
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_abc"}):
            result = verify_session("cs_test_123")
    assert result["subscription_id"] == "sub_123"


def test_verify_session_unpaid_returns_empty():
    session = MagicMock()
    session.payment_status = "unpaid"
    with patch("stripe.checkout.Session.retrieve", return_value=session):
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_abc"}):
            result = verify_session("cs_test_123")
    assert result == {}


# ── database access tests ──────────────────────────────────────────────────────

from database import get_user_access, set_paid


def _db_mock(rows=None):
    mock = MagicMock()
    ex = MagicMock()
    ex.data = rows or []
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value = ex
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value = ex
    return mock


def test_get_user_access_paid_returns_true():
    rows = [{"is_paid": True}]
    with patch("database.get_client", return_value=_db_mock(rows=rows)):
        assert get_user_access("boaz@test.com") is True


def test_get_user_access_unpaid_returns_false():
    rows = [{"is_paid": False}]
    with patch("database.get_client", return_value=_db_mock(rows=rows)):
        assert get_user_access("boaz@test.com") is False


def test_get_user_access_no_user_returns_false():
    with patch("database.get_client", return_value=_db_mock(rows=[])):
        assert get_user_access("nobody@test.com") is False


def test_set_paid_calls_update():
    mock = _db_mock()
    with patch("database.get_client", return_value=mock):
        set_paid("boaz@test.com", "sub_abc")
    call_args = mock.table.return_value.update.call_args.args[0]
    assert call_args["is_paid"] is True
    assert call_args["subscription_id"] == "sub_abc"

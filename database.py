import os
from supabase import create_client


def get_client():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    return create_client(url, key)


def save_user(email, access_token, refresh_token, oura_user_name):
    client = get_client()
    existing = client.table("users").select("id").eq("email", email).execute()
    if existing.data:
        client.table("users").update({
            "oura_access_token": access_token,
            "oura_refresh_token": refresh_token,
            "oura_user_name": oura_user_name,
        }).eq("email", email).execute()
        return existing.data[0]["id"]
    else:
        result = client.table("users").insert({
            "email": email,
            "oura_access_token": access_token,
            "oura_refresh_token": refresh_token,
            "oura_user_name": oura_user_name,
        }).execute()
        return result.data[0]["id"]


def get_user_by_email(email):
    client = get_client()
    result = client.table("users").select("*").eq("email", email).execute()
    return result.data[0] if result.data else None


def save_oura_data(user_id, date, data: dict):
    client = get_client()
    existing = client.table("oura_data").select("id").eq("user_id", user_id).eq("date", date).execute()
    payload = {"user_id": user_id, "date": date, **data}
    if existing.data:
        client.table("oura_data").update(payload).eq("user_id", user_id).eq("date", date).execute()
    else:
        client.table("oura_data").insert(payload).execute()


def get_oura_data(user_id):
    client = get_client()
    result = client.table("oura_data").select("*").eq("user_id", user_id).order("date", desc=True).execute()
    return result.data


_BASELINE_COLS = (
    "readiness_score,sleep_score,hrv_average,resting_heart_rate,"
    "deep_sleep_duration,total_sleep_duration"
)


def get_user_baselines(user_id: str) -> dict:
    """Return all-time per-metric averages for a user. Excludes None values."""
    try:
        client = get_client()
        result = client.table("oura_data").select(_BASELINE_COLS).eq("user_id", user_id).execute()
        if not result.data:
            return {}
        baselines = {}
        for key in _BASELINE_COLS.split(","):
            key = key.strip()
            vals = [r[key] for r in result.data if r.get(key) is not None]
            if vals:
                baselines[key] = sum(vals) / len(vals)
        return baselines
    except Exception:
        return {}


def get_history_stats(user_id: str) -> dict:
    """Return earliest_date (str) and total_days (int) for a user's oura data."""
    try:
        client = get_client()
        earliest = client.table("oura_data").select("date").eq("user_id", user_id).order("date").limit(1).execute()
        count_result = client.table("oura_data").select("date", count="exact").eq("user_id", user_id).execute()
        earliest_date = earliest.data[0]["date"] if earliest.data else None
        total_days = count_result.count or 0
        return {"earliest_date": earliest_date, "total_days": total_days}
    except Exception:
        return {"earliest_date": None, "total_days": 0}


def get_user_access(email: str) -> bool:
    """Return True if user has paid access."""
    try:
        client = get_client()
        result = client.table("users").select("is_paid").eq("email", email).execute()
        return bool(result.data and result.data[0].get("is_paid"))
    except Exception:
        return False


def set_paid(email: str, subscription_id: str) -> None:
    """Mark a user as paid. Creates a partial row if the user hasn't connected Oura yet."""
    from datetime import datetime, timezone
    try:
        client = get_client()
        now = datetime.now(timezone.utc).isoformat()
        existing = client.table("users").select("id").eq("email", email).execute()
        if existing.data:
            client.table("users").update({
                "is_paid": True,
                "subscription_id": subscription_id,
                "paid_at": now,
            }).eq("email", email).execute()
        else:
            client.table("users").insert({
                "email": email,
                "is_paid": True,
                "subscription_id": subscription_id,
                "paid_at": now,
            }).execute()
    except Exception:
        pass

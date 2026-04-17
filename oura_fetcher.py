import requests
from datetime import date
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    _HAS_TENACITY = True
except ImportError:
    _HAS_TENACITY = False

OURA_BASE = "https://api.ouraring.com/v2/usercollection"


def _get(endpoint, access_token, start_date, end_date):
    for attempt in range(3):
        try:
            resp = requests.get(
                f"{OURA_BASE}/{endpoint}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"start_date": start_date, "end_date": end_date},
                timeout=30,
            )
            if resp.status_code in (401, 403):
                return []  # Scope not granted — skip silently
            if resp.status_code == 429:
                import time; time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json().get("data", [])
        except requests.exceptions.Timeout:
            if attempt == 2:
                return []
    return []


def fetch_all_oura_data(access_token):
    end = date.today().isoformat()
    start = "2015-01-01"  # Oura Ring launched in 2015 — captures full history

    daily = {}

    def merge(day_key, data_dict):
        if day_key not in daily:
            daily[day_key] = {}
        daily[day_key].update({k: v for k, v in data_dict.items() if v is not None})

    # Daily Sleep scores + contributors
    for r in _get("daily_sleep", access_token, start, end):
        d = r.get("day")
        if not d:
            continue
        c = r.get("contributors") or {}
        merge(d, {
            "sleep_score": r.get("score"),
            "restfulness": c.get("restfulness"),
            "sleep_timing": c.get("timing"),
        })

    # Sleep detailed — durations, HRV, HR, breath
    for r in _get("sleep", access_token, start, end):
        d = r.get("day")
        if not d:
            continue
        total = r.get("total_sleep_duration") or 0
        deep = r.get("deep_sleep_duration") or 0
        light = r.get("light_sleep_duration") or 0
        rem = r.get("rem_sleep_duration") or 0
        merge(d, {
            "total_sleep_duration": total,
            "sleep_efficiency": r.get("efficiency"),
            "sleep_latency": r.get("latency"),
            "deep_sleep_duration": deep,
            "deep_sleep_percentage": round(deep / total * 100, 1) if total else None,
            "light_sleep_duration": light,
            "light_sleep_percentage": round(light / total * 100, 1) if total else None,
            "rem_sleep_duration": rem,
            "rem_sleep_percentage": round(rem / total * 100, 1) if total else None,
            "awake_time": r.get("awake_time"),
            "nightly_movement": r.get("restless_periods"),
            "average_breath": r.get("average_breath"),
            "breathing_regularity": r.get("average_breath"),
            "hrv_average": r.get("average_hrv"),
            "resting_heart_rate": r.get("lowest_heart_rate"),
            "lowest_heart_rate": r.get("lowest_heart_rate"),
            "bedtime_start": r.get("bedtime_start"),
            "bedtime_end": r.get("bedtime_end"),
        })

    # Daily Readiness
    for r in _get("daily_readiness", access_token, start, end):
        d = r.get("day")
        if not d:
            continue
        c = r.get("contributors") or {}
        merge(d, {
            "readiness_score": r.get("score"),
            "temperature_deviation": r.get("temperature_deviation"),
            "temperature_trend_deviation": r.get("temperature_trend_deviation"),
            "skin_temperature_deviation": r.get("temperature_deviation"),
            "skin_temperature_trend_deviation": r.get("temperature_trend_deviation"),
            "hrv_balance": c.get("hrv_balance"),
            "recovery_index": c.get("recovery_index"),
            "sleep_balance": c.get("sleep_balance"),
            "activity_balance": c.get("activity_balance"),
            "previous_day_activity": c.get("previous_day_activity"),
        })

    # Daily Activity
    for r in _get("daily_activity", access_token, start, end):
        d = r.get("day")
        if not d:
            continue
        merge(d, {
            "activity_score": r.get("score"),
            "steps": r.get("steps"),
            "distance": r.get("equivalent_walking_distance"),
            "active_calories": r.get("active_calories"),
            "total_calories": r.get("total_calories"),
            "target_calories": r.get("target_calories"),
            "high_activity_time": r.get("high_activity_time"),
            "medium_activity_time": r.get("medium_activity_time"),
            "low_activity_time": r.get("low_activity_time"),
            "sedentary_time": r.get("sedentary_time"),
            "resting_time": r.get("resting_time"),
            "non_wear_time": r.get("non_wear_time"),
            "average_met": r.get("average_met_minutes"),
            "inactivity_alerts": r.get("inactivity_alerts"),
            "meters_to_target": r.get("meters_to_target"),
        })

    # Daily SpO2
    for r in _get("daily_spo2", access_token, start, end):
        d = r.get("day")
        if not d:
            continue
        merge(d, {
            "spo2_average": (r.get("spo2_percentage") or {}).get("average"),
            "breathing_disturbance_index": r.get("breathing_disturbance_index"),
        })

    # Daily Stress
    for r in _get("daily_stress", access_token, start, end):
        d = r.get("day")
        if not d:
            continue
        merge(d, {
            "stress_high": r.get("stress_high"),
            "recovery_high": r.get("recovery_high"),
            "stress_day_summary": r.get("day_summary"),
        })

    # Daily Resilience
    for r in _get("daily_resilience", access_token, start, end):
        d = r.get("day")
        if not d:
            continue
        c = r.get("contributors") or {}
        merge(d, {
            "resilience_level": r.get("level"),
            "resilience_sleep_recovery": c.get("sleep_recovery"),
            "resilience_daytime_recovery": c.get("daytime_recovery"),
            "resilience_stress": c.get("stress"),
        })

    # Cardiovascular Age
    for r in _get("daily_cardiovascular_age", access_token, start, end):
        d = r.get("day")
        if not d:
            continue
        merge(d, {"cardiovascular_age": r.get("vascular_age")})

    # VO2 Max
    for r in _get("vO2_max", access_token, start, end):
        d = r.get("day")
        if not d:
            continue
        merge(d, {"vo2_max": r.get("vo2_max")})

    return daily

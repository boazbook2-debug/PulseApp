import json
from groq import Groq
from pulse_config import get_secret

METRICS_TO_ANALYSE = [
    "date",
    # Sleep
    "sleep_score", "total_sleep_duration", "sleep_efficiency", "sleep_latency",
    "restfulness", "sleep_timing", "light_sleep_duration", "light_sleep_percentage",
    "deep_sleep_duration", "deep_sleep_percentage", "rem_sleep_duration",
    "rem_sleep_percentage", "awake_time", "nightly_movement", "breathing_regularity",
    "spo2_average", "breathing_disturbance_index", "average_breath",
    "bedtime_start", "bedtime_end",
    # Cardiovascular
    "resting_heart_rate", "hrv_average", "lowest_heart_rate",
    "daytime_hr_average", "cardiovascular_age", "vo2_max",
    # Readiness
    "readiness_score", "hrv_balance", "recovery_index", "temperature_deviation",
    "temperature_trend_deviation", "sleep_balance", "activity_balance",
    "previous_day_activity",
    # Activity
    "activity_score", "steps", "distance", "active_calories", "total_calories",
    "target_calories", "high_activity_time", "medium_activity_time",
    "low_activity_time", "sedentary_time", "resting_time", "non_wear_time",
    "average_met", "inactivity_alerts", "meters_to_target",
    # Body Temperature
    "skin_temperature_deviation", "skin_temperature_trend_deviation",
    # Stress & Recovery
    "stress_high", "recovery_high", "stress_day_summary", "resilience_level",
    "resilience_sleep_recovery", "resilience_daytime_recovery", "resilience_stress",
]

SYSTEM_PROMPT = """You are a health intelligence analyst specialising in interpreting wearable biometric data. You analyse personal Oura Ring data and identify meaningful patterns, correlations, and trends.

Your job is to look at the user's historical Oura data and surface genuine observations — things that are actually present in their numbers, not generic health advice.

Rules:
- Only surface trends that are actually supported by the user's data
- Never make medical claims or diagnoses
- Never give medical advice
- Always phrase observations as patterns you notice, not facts about their health
- Be specific — reference actual numbers from their data
- Be honest about uncertainty — if a pattern is weak or based on limited data say so
- Focus on relationships between metrics, not just individual scores

Output format — return a JSON array of trend objects. Each trend must have:
- headline: a plain English headline describing the observation (max 12 words, no jargon)
- description: 2-3 sentences explaining in plain language
- metrics_involved: list of which Oura metrics are part of this trend
- data_points: the specific numbers from the data that support this observation
- confidence: low / medium / high based on how consistent and clear the pattern is
- time_period: how many days of data this is based on
- category: one of Sleep, Cardiovascular, Activity, Recovery, Stress, Temperature

Return only the JSON array. No preamble, no explanation outside the JSON. The application will parse your response directly."""

USER_PROMPT_TEMPLATE = """Here is {days} days of biometric data from my Oura Ring. Durations are in minutes.

{data_table}

Identify 5 to 7 meaningful health trends or patterns actually present in this data. Be specific with numbers."""


def _format_data(rows):
    available = [m for m in METRICS_TO_ANALYSE if any(r.get(m) is not None for r in rows)]
    lines = [", ".join(available)]
    for r in rows:
        vals = []
        for m in available:
            v = r.get(m)
            if v is None:
                vals.append("—")
            elif m in ("total_sleep_duration", "deep_sleep_duration", "light_sleep_duration",
                       "rem_sleep_duration", "awake_time", "sleep_latency", "high_activity_time",
                       "medium_activity_time", "low_activity_time", "sedentary_time",
                       "resting_time", "stress_high", "recovery_high"):
                vals.append(f"{int(v)//60}min")
            elif m in ("bedtime_start", "bedtime_end"):
                vals.append(str(v)[11:16] if v else "—")
            else:
                vals.append(str(v))
        lines.append(", ".join(vals))
    return "\n".join(lines)


def detect_trends(rows):
    if not rows:
        return []

    data_rows = [r for r in rows if r.get("sleep_score")][:30]
    if not data_rows:
        return []

    data_table = _format_data(data_rows)
    client = Groq(api_key=get_secret("GROQ_API_KEY"))
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=3000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                days=len(data_rows),
                data_table=data_table,
            )},
        ],
    )

    raw = completion.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)

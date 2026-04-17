# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Pulse** — a personal health intelligence platform for Boaz and his parents (3 users max).
Connects to Oura Ring, pulls biometric data, detects health trends via Claude API, and links trends to PubMed research papers.
Repo: https://github.com/boazbook2-debug/claude-site-1 (private)

## Stack

- Python, Streamlit, Supabase, Oura API, PubMed API, Anthropic Claude API
- Deploy: Railway or Streamlit Cloud

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
pytest test_auth.py
```

## Environment Variables

Never hardcode secrets. All loaded via `.env` (see `.env.example`):
- `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET`
- `SUPABASE_URL`, `SUPABASE_KEY`
- `ANTHROPIC_API_KEY`

## Supabase Tables

**users:** id, email, oura_access_token, oura_refresh_token, oura_user_name, stripe_customer_id, subscription_status, created_at

**oura_data:** id, user_id (→ users.id), date, created_at, plus all metrics below:

Sleep: sleep_score, total_sleep_duration, sleep_efficiency, sleep_latency, restfulness, sleep_timing, light_sleep_duration, light_sleep_percentage, deep_sleep_duration, deep_sleep_percentage, rem_sleep_duration, rem_sleep_percentage, awake_time, nightly_movement, breathing_regularity, spo2_average, breathing_disturbance_index, average_breath, bedtime_start, bedtime_end

Cardiovascular: resting_heart_rate, hrv_average, cardiovascular_age, vo2_max, daytime_hr_average, lowest_heart_rate

Readiness: readiness_score, hrv_balance, recovery_index, temperature_deviation, temperature_trend_deviation, sleep_balance, activity_balance, previous_day_activity

Activity: activity_score, steps, distance, active_calories, total_calories, high_activity_time, medium_activity_time, low_activity_time, sedentary_time, resting_time, non_wear_time, average_met, inactivity_alerts, target_calories, meters_to_target

Body Temperature: skin_temperature_deviation, skin_temperature_trend_deviation

Stress & Recovery: stress_high, recovery_high, stress_day_summary, resilience_level, resilience_sleep_recovery, resilience_daytime_recovery, resilience_stress

## Session Progress

- [x] Session 1 — Oura OAuth (app.py, auth.py, database.py, test_auth.py)
- [x] Session 2 — Pull & store Oura data (oura_fetcher.py, test_data.py)
- [x] Session 3 — Trend detection via Claude API (trend_detector.py, test_trends.py)
- [x] Session 4 — PubMed integration
- [x] Session 5 — Speculation slider + evidence metrics
- [x] Session 6 — Deploy to Railway + Stripe payments
  - Pricing page → Stripe checkout ($25/month)
  - Stripe webhook → auto-create user in Supabase + grant access
  - User then connects Oura Ring and sees dashboard
  - Add stripe_customer_id and subscription_status to users table

## Build Rules

- One feature at a time
- After each feature write tests in `test_[feature].py`, run them, fix all failures before moving on
- Keep code simple and readable
- Never crash — always show a clear error message
- Never log or expose tokens
- Never make medical claims — always show disclaimer

# Pulse — Complete AI Build Prompt

Paste this entire prompt into any AI coding assistant (Claude Code, Cursor, Windsurf, etc.) to recreate Pulse from scratch, production-ready and ready to generate revenue.

---

## What You Are Building

**Pulse** is a personal health intelligence SaaS. It connects to a user's Oura Ring via OAuth, pulls their complete biometric history, uses AI (Groq/Llama) to detect health trends in their data, and links each trend to peer-reviewed PubMed research papers. Users pay $25/month to access their personal data analysis. Research mode (exploring the science without personal data) is free.

**Revenue model:** Stripe subscription, $25/month. Free tier = Research mode. Paid tier = Personal Data mode with AI trend detection.

**Target users:** Oura Ring wearers who take their health seriously. Small, high-intent audience.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend + backend | Python, Streamlit (>=1.40.0) |
| Database | Supabase (PostgreSQL) |
| AI | Groq API (llama-3.3-70b-versatile) |
| Wearable | Oura Ring API v2 (OAuth 2.0) |
| Research | PubMed/NCBI E-utilities API |
| Payments | Stripe (subscription, $25/month) |
| Deploy | Streamlit Cloud (free tier works) |

---

## Environment Variables

Create a `.env` file and add all of these to Streamlit Cloud secrets:

```
OURA_CLIENT_ID=your_oura_client_id
OURA_CLIENT_SECRET=your_oura_client_secret
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
GROQ_API_KEY=your_groq_api_key
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_PRICE_ID=price_your_stripe_price_id
STREAMLIT_URL=https://your-app.streamlit.app
```

Never hardcode secrets. Load via `python-dotenv` locally, Streamlit secrets in production.

---

## Supabase Database Schema

Create these two tables exactly. Run in Supabase SQL editor:

```sql
-- Users table
create table users (
  id uuid default gen_random_uuid() primary key,
  email text unique not null,
  oura_access_token text,
  oura_refresh_token text,
  oura_user_name text,
  is_paid boolean default false,
  subscription_id text,
  paid_at timestamptz,
  created_at timestamptz default now()
);

-- Oura biometric data (one row per user per day)
create table oura_data (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references users(id) on delete cascade,
  date date not null,
  created_at timestamptz default now(),

  -- Sleep
  sleep_score integer,
  total_sleep_duration integer,       -- seconds
  sleep_efficiency integer,
  sleep_latency integer,
  restfulness integer,
  sleep_timing integer,
  light_sleep_duration integer,
  light_sleep_percentage numeric,
  deep_sleep_duration integer,
  deep_sleep_percentage numeric,
  rem_sleep_duration integer,
  rem_sleep_percentage numeric,
  awake_time integer,
  nightly_movement integer,
  breathing_regularity numeric,
  spo2_average numeric,
  breathing_disturbance_index numeric,
  average_breath numeric,
  bedtime_start text,
  bedtime_end text,

  -- Cardiovascular
  resting_heart_rate integer,
  lowest_heart_rate integer,
  hrv_average numeric,
  cardiovascular_age integer,
  vo2_max numeric,
  daytime_hr_average numeric,

  -- Readiness
  readiness_score integer,
  hrv_balance integer,
  recovery_index integer,
  temperature_deviation numeric,
  temperature_trend_deviation numeric,
  skin_temperature_deviation numeric,
  skin_temperature_trend_deviation numeric,
  sleep_balance integer,
  activity_balance integer,
  previous_day_activity integer,

  -- Activity
  activity_score integer,
  steps integer,
  distance numeric,
  active_calories integer,
  total_calories integer,
  target_calories integer,
  high_activity_time integer,
  medium_activity_time integer,
  low_activity_time integer,
  sedentary_time integer,
  resting_time integer,
  non_wear_time integer,
  average_met numeric,
  inactivity_alerts integer,
  meters_to_target numeric,

  -- Stress & Recovery
  stress_high integer,
  recovery_high integer,
  stress_day_summary text,
  resilience_level text,
  resilience_sleep_recovery numeric,
  resilience_daytime_recovery numeric,
  resilience_stress numeric,

  unique(user_id, date)
);
```

---

## File Structure

```
app.py                  # Main Streamlit app — all pages, routing, UI
auth.py                 # Oura OAuth helpers
database.py             # All Supabase operations
oura_fetcher.py         # Pulls all Oura API endpoints, merges to daily dict
trend_detector.py       # Groq AI call — detects patterns in biometric data
pubmed.py               # PubMed E-utilities search
stripe_handler.py       # Stripe checkout session creation + webhook verification
design.py               # CSS design system applied once at startup
requirements.txt        # Dependencies
.env                    # Local secrets (never commit)
.env.example            # Template showing which vars are needed
```

---

## Design System

Dark theme. Premium. Medical-grade aesthetic. NOT a wellness app.

**Colors:**
- Background: `#080808`
- Surface: `#111111`
- Border: `rgba(255,255,255,0.06)`
- Text primary: `#F0F0F0`
- Text secondary: `#888888`
- Text muted: `#555555`
- Accent green: `#00C896` (evidence, health, positive)
- Accent purple: `#7C6AF7` (AI, intelligence, insights)
- Accent yellow: `#F0C040` (medium evidence, moderate)
- Accent red: `#E05050` (speculative, concerning)

**Typography:**
- UI font: Plus Jakarta Sans (Google Fonts) — weights 400, 500, 600, 700
- Data/mono font: JetBrains Mono (Google Fonts) — weights 400, 500
- Apply globally: `font-family: 'Plus Jakarta Sans', system-ui, sans-serif`

**Key CSS rules (apply via `st.markdown` in `apply_design_system()`):**
```css
/* Remove all Streamlit chrome */
#MainMenu, footer, header { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stVerticalBlock"] > div { gap: 0 !important; }

/* Dark background everywhere */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background: #080808 !important;
}
```

**Component patterns:**
- Cards: `background:#111111; border:1px solid rgba(255,255,255,0.06); border-radius:12px; padding:24px`
- Hover on cards: `transform:translateY(-4px); border-color:rgba(255,255,255,0.18)`
- Primary CTA: gradient `linear-gradient(135deg,#00C896,#7C6AF7)` with glow animation
- All internal links: always use `target="_self"` — never open new tabs
- All `<a>` tags must have `target="_self"` for internal navigation

---

## Page Architecture & Routing

Routing is done via `st.query_params` and `st.session_state`. No Streamlit multipage.

```python
# Routing logic (at bottom of app.py)
params = st.query_params

# OAuth callback
if "code" in params:
    handle_oauth_callback()

# Page routing
if just_connected:
    render_connect_success()
elif params.get("page") == "pricing":
    render_pricing_page()
elif params.get("page") == "privacy":
    render_privacy_page()
elif params.get("page") == "terms":
    render_terms_page()
elif session_state.get("nav_page") == "connect":
    render_connect_page()
elif session_state.get("modal_slug"):
    render_modal(slug, mode)
elif not connected:
    render_landing_page()   # Cold traffic landing page
else:
    render_navbar()
    render_mode_toggle()
    render_slider()
    render_homepage()
```

**Back button pattern:** ALL pages use `<a href="?back=1" target="_self">← Back</a>`. The router catches `params.get("back") == "1"`, clears `nav_page`, `modal_slug`, `modal_mode` from session state, and reruns.

---

## Page 1: Landing Page (non-connected visitors)

This is the conversion engine. Every element exists to get the user to click "Connect Oura Ring".

**Structure:**
1. **Sticky header** (60px, `position:sticky;top:0;z-index:600;backdrop-filter:blur(12px)`)
   - Left: "Pulse" logo
   - Center: nav links — "How it works", "Research", "Pricing"
   - Right: "Connect Oura Ring →" button — green `#00C896`, always visible
   - `data-track="header-cta"` attribute

2. **Hero section** (centered, `padding:80px 24px`)
   - Eyebrow: "Personal Health Intelligence" — small uppercase teal pill
   - H1: "Your Oura Ring knows things your doctor doesn't."
   - Subhead: "Pulse connects your complete biometric history to peer-reviewed science. See what your body is actually telling you."
   - Primary CTA: gradient glowing button — "Connect your Oura Ring — free →"
   - Below button: "No credit card required to start"
   - Social proof strip: "Connected to 50,000+ PubMed papers · Analysing HRV, sleep, readiness, stress & more"

3. **Problem section** (3-column grid)
   - H2: "You have the data. You don't have the answers."
   - Column 1: "Numbers without meaning" — Oura shows scores, doesn't explain them
   - Column 2: "Research not written for you" — PubMed has 35M papers, none personalised to your HRV
   - Column 3: "Clinics cost $5,000/year" — longevity clinics have experts, you don't have access
   - Below grid: green highlighted callout — "Pulse bridges all three."

4. **How it works** (3 numbered steps, `id="how-it-works"`)
   - 01 (green): Connect your Oura Ring — 30 seconds, read-only OAuth
   - 02 (purple): We analyse your complete history — every day since you started
   - 03 (yellow): Read what the science says about your body specifically

5. **Research preview** (3 example cards, `id="research"`)
   - H2: "Try it free — no Oura required"
   - Show 3 hardcoded research topic cards with real content
   - Secondary button: "Explore all research topics →" links to `?mode=research`

6. **Pricing section** (`id="pricing"`)
   - Anchor line above price: "Longevity clinics charge $5,000/year for this level of insight."
   - Single plan card: $25/month, green accent border
   - Feature list with green checkmarks — 5 specific benefits
   - CTA: "Start for free — upgrade when ready →" (connects Oura first, paywall after)
   - Trust line: "Cancel anytime · No contracts · Your data stays yours"

7. **Final CTA** (centered, full-width dark section)
   - H2: "Stop looking at numbers. Start understanding them."
   - Sub: "Your data has been collecting since you first wore your ring. It's waiting to be analysed."
   - Single gradient CTA button

8. **Footer** — minimal: logo, Privacy Policy, Terms of Service links

---

## Page 2: Oura Connect Page

Shown when user clicks "Connect Oura Ring" from landing or nav.

- Centered layout, logo only in header (no nav)
- Back arrow below header: `← Back`
- H1: "Connect your biology to the science behind it"
- Trust signals: "Read-only access · We never sell your data · Disconnect anytime from Oura app"
- Large OAuth button linking to `get_auth_url()` — `target="_self"`
- 3 benefit cards below: Pattern detection / Research links / Personal context

---

## Page 3: Connection Success (shown immediately after OAuth)

Shown once after `?code=` callback is processed. Auto-advances after data sync.

```python
def render_connect_success():
    # Show spinner + status messages while:
    # 1. fetch_all_oura_data(access_token) — pulls ALL endpoints since 2015
    # 2. save_oura_data(user_id, day, metrics) — saves each day to Supabase
    # 3. detect_trends(rows) — AI analysis
    # Then: session_state.mode = "personal", st.rerun()
```

Progress steps shown to user:
- "Fetching Oura data…"
- "Saving X days…"
- "Detecting trends…"
- "Analysis complete ✓"

---

## Page 4: Dashboard (connected users)

**Navbar** (sticky, 64px):
- Left: search input
- Center: "Pulse" logo
- Right: if not connected → "Connect Oura Ring" button; if connected → user dropdown (Sync Ring / Sign out)

**Free-tier banner** (shown between navbar and content until paid):
```
🔬 You're viewing research insights. Connect payment to unlock your personal Oura analysis.  [Upgrade $25/month]
```
Thin green-tinted bar, full width, `data-track="upgrade-banner"`.

**Mode toggle** (pill tabs):
- "Research" | "Your Data"
- Research is always free
- "Your Data" triggers paywall if not paid

**Speculation slider** (0–10):
- Left label: "Evidence-based"
- Right label: "Speculative"
- Thumb color interpolates: green (0) → yellow (5) → red (10)
- Controls which topic zone is shown (0=RCTs/meta-analyses, 9=frontier science)
- No numbers displayed on slider — just the gradient track and thumb

**Topic cards** (3×N grid):
- Each card: evidence badge, headline, description snippet, paper count, indirect citations
- Hover: lift effect, border brightens
- Click: opens modal with full detail

**Research mode**: shows `TOPIC_ZONES[slider_value]` — 10 topics per zone, 10 zones (0–9)
**Personal mode** (paid only): shows AI-detected trends from user's data

---

## Page 5: Topic/Trend Detail Modal

Opens when user clicks a card. Replaces homepage (session state, not a real modal).

```python
# Session state approach:
st.session_state["modal_slug"] = slug
st.session_state["modal_mode"] = "research"  # or "personal"
st.rerun()
```

**Modal layout:**
- Top bar: `← Back` (HTML link to `?back=1`) | "RESEARCH" or "YOUR DATA" badge
- Hero: evidence pill → H1 headline → description
- Stats strip: Research Papers | Indirect Citations | Relevancy Score (3 cards)
- "What the science says" — AI-generated 3-paragraph summary (Groq, cached 24h)
- Paper cards grid (2 columns) — fetched from PubMed, each with: title, journal, year, evidence score
- Footer

---

## Page 6: Pricing Page

Pre-generates Stripe checkout URL at page load — embeds as `<a href>` link (not Streamlit button).

```python
def render_pricing_page():
    try:
        _cta_href = create_checkout_session(email)  # returns Stripe hosted URL
    except Exception as e:
        _cta_href = ""
        _error = str(e)
    # Render HTML with <a href="{_cta_href}" target="_self">
```

- Anchor: "Longevity clinics charge $5,000/year"
- Price: $25/month (JetBrains Mono, large)
- Feature list
- Glowing gradient CTA button — "Get Started →"
- If Stripe fails: show error text clearly, button shows "Checkout unavailable"

---

## Page 7: Paywall Teaser (inside dashboard, unpaid)

Shown when unpaid user enters "Your Data" mode. Uses loss-aversion copy.

```
Your data is ready to analyse

You're leaving [X days of data since YYYY-MM-DD] unanalysed.

Longevity clinics charge $5,000/year for this level of insight.
Pulse surfaces AI-detected trends — linked to peer-reviewed science.

[50k+ papers] | [X days tracked] | [14 metrics analysed]

[Unlock my personal insights — $25/month →]

Cancel anytime · No contracts · Your data stays yours
```

Show user's actual day count and start date. This creates ownership feeling — their data is already there waiting.

---

## auth.py

```python
OURA_AUTH_URL = "https://cloud.ouraring.com/oauth/authorize"
OURA_TOKEN_URL = "https://api.ouraring.com/oauth/token"
OURA_PERSONAL_INFO_URL = "https://api.ouraring.com/v2/usercollection/personal_info"
REDIRECT_URI = os.environ.get("STREAMLIT_URL", "http://localhost:8501")
SCOPES = "email personal daily heartrate session tag spo2 ring_configuration workout stress"

def get_auth_url():
    # Build OAuth URL with client_id, redirect_uri, scopes, prompt=consent

def exchange_code_for_tokens(code):
    # POST to OURA_TOKEN_URL with grant_type=authorization_code
    # Auth: HTTP Basic (client_id, client_secret)

def get_user_info(access_token):
    # GET OURA_PERSONAL_INFO_URL with Bearer token
    # Returns: email, full_name
```

**Critical:** REDIRECT_URI must exactly match what's registered in Oura developer console. Only register `https://your-app.streamlit.app` — do NOT register localhost (Oura rejects http:// non-HTTPS URIs).

---

## oura_fetcher.py

Fetches ALL endpoints, merges into `{date: {metric: value}}` dict.

```python
ENDPOINTS = [
    "daily_sleep",      # sleep_score, restfulness, timing
    "sleep",            # total_sleep_duration, deep/light/rem, HRV, HR, efficiency
    "daily_readiness",  # readiness_score, temperature, HRV balance, recovery_index
    "daily_activity",   # steps, calories, activity score, sedentary time
    "daily_spo2",       # spo2_average, breathing_disturbance_index
    "daily_stress",     # stress_high, recovery_high, day_summary
    "daily_resilience", # resilience_level, sleep_recovery, daytime_recovery
    "daily_cardiovascular_age",  # vascular_age
    "vO2_max",          # vo2_max
]

# Start date: "2015-01-01" (Oura launched in 2015, captures full history)
# Retry logic: 3 attempts, 30s timeout, exponential backoff on 429
# Silently skip 401/403 (scope not granted for that endpoint)
```

---

## trend_detector.py

```python
def detect_trends(rows: list[dict]) -> list[dict]:
    """
    Takes list of oura_data rows (dicts with all metrics).
    Calls Groq API (llama-3.3-70b-versatile) with last 30 days of data.
    Returns list of trend dicts:
    {
        "headline": str,          # Short, specific finding
        "description": str,       # 1-2 sentence explanation
        "category": str,          # "Sleep", "HRV", "Readiness", etc.
        "confidence": str,        # "high", "medium", "low"
        "metrics_involved": list, # ["hrv_average", "sleep_score"]
        "data_points": dict,      # {"avg_hrv": 42, "trend": "declining"}
        "time_period": int,       # days analysed
    }
    
    Prompt Groq with: last 30 rows, instruction to find 3-5 genuine patterns,
    return JSON array. Parse response, add slugs.
    """
```

---

## pubmed.py

```python
NCBI_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_SUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

def search_pubmed(query: str, slider_value: int = 2, max_results: int = 6) -> list[dict]:
    """
    Search PubMed for papers relevant to query.
    slider_value 0-3: add "randomized controlled trial" filter
    slider_value 4-7: no filter
    slider_value 8-10: broader terms
    Returns list of: {title, authors, journal, date, pmid, url}
    """

def get_evidence_label(spec_val: int) -> tuple[str, str]:
    """Returns (label, description) based on slider position.
    0-2: "Randomised Controlled Trials"
    3-4: "Cohort Studies & Clinical Evidence"
    5-6: "Observational & Mechanistic Studies"
    7-8: "Emerging Research & Case Studies"
    9-10: "Emerging & Exploratory Research"
    """
```

---

## stripe_handler.py

```python
def create_checkout_session(email: str) -> str:
    """Create Stripe Checkout session, return hosted URL."""
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    base_url = os.environ.get("STREAMLIT_URL", "https://your-app.streamlit.app")
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": os.environ["STRIPE_PRICE_ID"], "quantity": 1}],
        customer_email=email or None,
        success_url=f"{base_url}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base_url}?page=pricing",
    )
    return session.url

def verify_session(session_id: str) -> dict:
    """Retrieve session. If paid, return {email, subscription_id}."""
    session = stripe.checkout.Session.retrieve(session_id)
    if session.payment_status == "paid":
        return {"email": session.customer_details.email, "subscription_id": session.subscription}
    return {}
```

**Stripe setup:**
1. Create product: "Pulse Subscription" at $25/month recurring
2. Copy Price ID (starts with `price_`) → `STRIPE_PRICE_ID`
3. Use live key `sk_live_...` for production

**Payment flow:**
- User clicks "Get Started" → Stripe hosted checkout in same tab (`target="_self"`)
- After payment: Stripe redirects to `?session_id=xxx`
- App calls `verify_session()`, calls `set_paid(email, subscription_id)`, sets `is_paid=True`

---

## database.py Key Functions

```python
def save_user(email, access_token, refresh_token, name) -> str:
    """Upsert user, return user_id (uuid)."""

def get_user_by_email(email) -> dict | None:
    """Return user row or None."""

def save_oura_data(user_id, date, data: dict):
    """Upsert oura_data row. Use .update() if exists, .insert() if not."""

def get_oura_data(user_id) -> list[dict]:
    """Return all rows ordered by date desc."""

def get_user_baselines(user_id) -> dict:
    """Return per-metric averages: {metric: float}"""

def get_history_stats(user_id) -> dict:
    """Return {earliest_date: str, total_days: int}"""

def get_user_access(email) -> bool:
    """Return users.is_paid"""

def set_paid(email, subscription_id):
    """Set is_paid=True, subscription_id, paid_at=now()"""
```

---

## OAuth Callback (critical — get this right)

```python
# At TOP of app.py, before any rendering
params = st.query_params

if "code" in params and "topic" not in params:
    try:
        with st.spinner("Connecting…"):
            tokens = exchange_code_for_tokens(params["code"])
            info = get_user_info(tokens["access_token"])
            email = info.get("email", "")
            name = info.get("full_name") or email or "User"
            uid = save_user(email, tokens["access_token"], tokens["refresh_token"], name)
            st.session_state.update({
                "user_name": name, "user_id": uid,
                "access_token": tokens["access_token"],
                "email": email, "connected": True, "just_connected": True,
            })
            st.query_params.clear()
            st.rerun()   # MUST rerun after setting session state
    except Exception as e:
        st.session_state["_oauth_error"] = str(e)
        st.query_params.clear()
        st.rerun()

# Show any OAuth error (after rerun)
if "_oauth_error" in st.session_state:
    st.error(st.session_state.pop("_oauth_error"))
```

---

## Oura Developer Console Setup

1. Go to cloud.ouraring.com/oauth/applications
2. Create new app:
   - **Redirect URI:** `https://your-app.streamlit.app` only (do NOT add localhost — Oura rejects http://)
   - **Privacy Policy URL:** `https://your-app.streamlit.app/?page=privacy`
   - **Terms of Service URL:** `https://your-app.streamlit.app/?page=terms`
   - **Scopes:** Email, Personal, Daily, Heartrate, Session, Tag, SpO2, Ring Configuration, Workout, Stress, Heart Health
3. Copy Client ID and Client Secret → add to env

**Do not submit for review until you have tested the full flow end-to-end.** Keep it in Development mode for testing.

---

## Privacy Policy (required by Oura for approval)

Must be accessible at `?page=privacy`. Must include:
- What data is collected (list specific Oura metrics)
- How it's used (AI trend detection, research linking)
- Who processes it (Groq/Llama for AI, Supabase for storage)
- Data retention (30 days after account deletion on request)
- How to revoke access (Oura app → Connected Apps → Pulse → Disconnect)
- No medical advice disclaimer
- Contact email for data requests
- No data sold to third parties

---

## Conversion Copy Rules (apply everywhere)

**CTAs — action + benefit, never generic:**
- ✓ "Connect your Oura Ring — free"
- ✓ "Unlock my personal insights"
- ✓ "See what your body is actually telling you"
- ✗ "Sign up" / "Subscribe" / "Get started"

**Numbers — always specific:**
- ✓ "50,000+ PubMed papers"
- ✓ "14 Oura metrics analysed"
- ✓ "[X] days of data since [date]"
- ✗ "thousands of papers" / "lots of data"

**Anchoring — always before price:**
- "Longevity clinics charge $5,000/year for this level of insight."
- Then: "$25/month"

**Loss aversion on paywall:**
- "You're leaving [X days] of data unanalysed."
- NOT "Upgrade to unlock premium features"

**Trust signals near every CTA:**
- "No credit card required to start"
- "Read-only Oura access — we never write to your ring"
- "Cancel anytime · No contracts · Your data stays yours"

---

## Requirements.txt

```
streamlit>=1.40.0
supabase>=2.0.0
requests>=2.31.0
python-dotenv>=1.0.0
pandas>=2.0.0
groq>=0.9.0
stripe>=8.0.0
tenacity>=8.2.0
```

---

## Deployment: Streamlit Cloud

1. Push code to a GitHub repo (private is fine)
2. Go to share.streamlit.io → New app → connect your repo
3. Set main file: `app.py`
4. Go to Settings → Secrets → paste all env vars in TOML format:
   ```toml
   OURA_CLIENT_ID = "your-value"
   OURA_CLIENT_SECRET = "your-value"
   SUPABASE_URL = "your-value"
   SUPABASE_KEY = "your-value"
   GROQ_API_KEY = "your-value"
   STRIPE_SECRET_KEY = "your-value"
   STRIPE_PRICE_ID = "your-value"
   STREAMLIT_URL = "https://your-app.streamlit.app"
   ```
5. Deploy. After any secrets change, click "Reboot app" for them to take effect.

**Custom domain** (optional): Streamlit Cloud supports custom domains on paid plans. Point your domain's CNAME to the Streamlit URL, then update `STREAMLIT_URL` and Oura redirect URI accordingly.

---

## Critical Bugs to Avoid

1. **All `<a>` links in `st.markdown` HTML must have `target="_self"`** — Streamlit's render context causes links without this to open in new tabs

2. **`st.rerun()` after OAuth callback** — without it, session state changes don't take effect and user stays on the code-exchange page

3. **Set session state BEFORE clearing query params** — `st.query_params.clear()` can trigger a rerun, losing state set after it

4. **REDIRECT_URI is module-level** — it's set at import time. If `STREAMLIT_URL` env var isn't loaded before `import auth`, it falls back to localhost and OAuth fails. Use `load_dotenv()` at top of app before imports.

5. **Stripe checkout pre-generates URL at page render** — embed as `<a href>` not `st.button`. Streamlit buttons can't wrap arbitrary href links.

6. **Oura codes are single-use** — if the callback fails (e.g., network error), the code is consumed. The user must restart the OAuth flow. Always catch exceptions and show a clear "try again" message.

7. **Don't use `st.columns` for the first element on a page** — Streamlit CSS that makes the navbar sticky (`[data-testid="stHorizontalBlock"]:first-of-type`) will style that columns row as a 64px navbar instead.

---

## The One Metric

Every decision should answer: **does this make it more or less likely that a user who connects their Oura Ring will pay $25/month?**

The fastest path to revenue:
**Landing page → clicks "Connect Oura Ring" → OAuth → loading screen with their data being pulled → dashboard with metrics → Research mode (free value) → tries "Your Data" tab → paywall with their actual day count → pays $25 → sees personal trends → tells someone**

Remove every friction point in that journey.

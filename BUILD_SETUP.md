# Pulse — Complete Build Setup

Everything you need to rebuild, extend, or hand this to a developer.

---

## AI Coding Skills to Install First

Before writing any code, install these skills in Claude Code. They are already installed in the original build environment and must be active for design quality to match.

### 1. ui-ux-pro-max
The primary design skill. Activates with `/ui-ux-pro-max` or by typing the skill name.
Covers: design systems, component specs, brand guidelines, token architecture, UI styling, responsive design, slide creation.
**Use this skill for every UI decision — every page, every component, every color choice.**

### 2. frontend-design (claude-plugins-official)
Installed via Claude Code plugin marketplace.
Activates with `/frontend-design`.
Covers: frontend component patterns, layout systems, interaction design.
**Use this skill when building any page layout or interactive component.**

### How to invoke skills in Claude Code
At the start of every coding session, type:
```
/ui-ux-pro-max
/frontend-design
```
Or simply tell Claude Code: "Use the ui-ux-pro-max and frontend-design skills for all design decisions."

---

## Secret Keys (All Services Connected)

### Oura Ring API
```
OURA_CLIENT_ID=<see .env>
OURA_CLIENT_SECRET=<see .env>
```
Console: cloud.ouraring.com/oauth/applications
Redirect URI registered: https://pulseweb.streamlit.app
Privacy Policy: https://pulseweb.streamlit.app/?page=privacy
Terms: https://pulseweb.streamlit.app/?page=terms

### Supabase (Database)
```
SUPABASE_URL=<see .env>
SUPABASE_KEY=<see .env>
```
Console: supabase.com → project wbcqqfrcaivipywughst
Tables: users, oura_data (see RECREATE_PROMPT.md for full SQL schema)

### Groq (AI — Llama 3.3 70B)
```
GROQ_API_KEY=<see .env>
```
Console: console.groq.com
Model used: llama-3.3-70b-versatile
Used for: trend detection from biometric data, research summaries

### Stripe (Payments — $25/month)
```
STRIPE_SECRET_KEY=<see .env>
STRIPE_PRICE_ID=<see .env>
```
Console: dashboard.stripe.com
Product: Pulse Subscription — $25/month recurring
Success URL: https://pulseweb.streamlit.app?session_id={CHECKOUT_SESSION_ID}
Cancel URL: https://pulseweb.streamlit.app?page=pricing

### Deployment (Streamlit Cloud)
```
STREAMLIT_URL=https://pulseweb.streamlit.app
```
Console: share.streamlit.io
GitHub repo: https://github.com/boazbook2-debug/PulseApp (private)
Main file: app.py

---

## Streamlit Cloud Secrets (paste this entire block)

Go to share.streamlit.io → your app → Settings → Secrets → paste everything below:

```toml
OURA_CLIENT_ID = "..."
OURA_CLIENT_SECRET = "..."
SUPABASE_URL = "..."
SUPABASE_KEY = "..."
GROQ_API_KEY = "..."
STRIPE_SECRET_KEY = "..."
STRIPE_PRICE_ID = "..."
STREAMLIT_URL = "https://pulseweb.streamlit.app"
```
> Copy actual values from your local `.env` file.

After saving: click **Reboot app** for secrets to take effect.

---

## Local .env File

For local development. Create `.env` in the project root:

```
OURA_CLIENT_ID=...
OURA_CLIENT_SECRET=...
SUPABASE_URL=...
SUPABASE_KEY=...
GROQ_API_KEY=...
STRIPE_SECRET_KEY=...
STRIPE_PRICE_ID=...
STREAMLIT_URL=https://pulseweb.streamlit.app
```
> See the `.env` file in the project root for actual values (never commit that file).

Note: For local testing, Oura OAuth will redirect to the production Streamlit URL (only URI registered). Test the full OAuth flow on pulseweb.streamlit.app, not localhost.

---

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Build Instructions for Claude Code / Cursor / Windsurf

1. Open the project folder in your AI coding tool
2. Install and activate skills:
   - `/ui-ux-pro-max` — for all design decisions
   - `/frontend-design` — for component and layout work
3. Read these files first (tell the AI to read them before touching code):
   - `RECREATE_PROMPT.md` — full product and technical spec
   - `CLAUDE.md` — project rules and build guidelines
   - `.env` — all connected services
4. Start with `app.py` — it is the entire app (pages, routing, UI, logic)
5. Supporting files: `auth.py`, `database.py`, `oura_fetcher.py`, `trend_detector.py`, `pubmed.py`, `stripe_handler.py`, `design.py`

---

## Service Account Emails

- Oura developer account: boazbook2@gmail.com
- Supabase account: boazbook2@gmail.com
- Stripe account: boazbook2@gmail.com
- Streamlit Cloud: boazbook2@gmail.com
- GitHub repo: boazbook2-debug/claude-site-1

---

## Key Design Rules (enforce with ui-ux-pro-max skill)

- Background: #080808 — never white, never light grey
- Font: Plus Jakarta Sans (UI) + JetBrains Mono (data/numbers)
- Accent green #00C896 — evidence, health, positive actions
- Accent purple #7C6AF7 — AI, intelligence, insights
- Never generic wellness feel — premium, medical-grade aesthetic
- All links: target="_self" — never open new tabs
- No Streamlit default buttons for CTAs — use HTML <a> tags with custom CSS
- Slider: gradient track green→yellow→red, no numbers displayed
- Cards: dark surface, subtle border, lift on hover

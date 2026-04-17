"""
Pulse Design System
All CSS loaded once via apply_design_system().
Font: Plus Jakarta Sans (UI) + JetBrains Mono (data)
"""
import streamlit as st


def get_glow_color(value: int, min_val: int = 0, max_val: int = 10) -> str:
    """Interpolate thumb glow color matching the React component's getColorAtPosition."""
    pct = (value - min_val) / (max_val - min_val) * 100
    if pct <= 50:
        ratio = pct / 50
        r = round(0   + (255 - 0)   * ratio)
        g = round(200 + (215 - 200) * ratio)
        b = round(150 + (80  - 150) * ratio)
    else:
        ratio = (pct - 50) / 50
        r = round(255 + (224 - 255) * ratio)
        g = round(215 + (80  - 215) * ratio)
        b = round(80  + (80  - 80)  * ratio)
    return f"rgb({r},{g},{b})"


def get_evidence_shadow(relevancy: int) -> str:
    if relevancy > 75:
        return "0 0 0 1px rgba(0,200,150,0.25), 0 0 24px rgba(0,200,150,0.06)"
    elif relevancy >= 40:
        return "0 0 0 1px rgba(240,192,64,0.25), 0 0 24px rgba(240,192,64,0.06)"
    return "0 0 0 1px rgba(224,80,80,0.25), 0 0 24px rgba(224,80,80,0.06)"


def get_slider_shadow(spec_val: int) -> tuple[str, str, str]:
    """Returns (shadow, border_color, accent_color) based on slider position."""
    if spec_val <= 3:
        return (
            "0 0 0 1px rgba(0,200,150,0.30), 0 0 28px rgba(0,200,150,0.10)",
            "rgba(0,200,150,0.30)",
            "#00C896",
        )
    elif spec_val <= 6:
        return (
            "0 0 0 1px rgba(240,192,64,0.30), 0 0 28px rgba(240,192,64,0.10)",
            "rgba(240,192,64,0.30)",
            "#F0C040",
        )
    else:
        return (
            "0 0 0 1px rgba(224,80,80,0.30), 0 0 28px rgba(224,80,80,0.10)",
            "rgba(224,80,80,0.30)",
            "#E05050",
        )


def get_conf_color(conf: str) -> str:
    return {"high": "#00C896", "medium": "#F0C040", "low": "#E05050"}.get(conf, "#555555")


def get_conf_shadow(conf: str) -> str:
    return {
        "high":   "0 0 0 1px rgba(0,200,150,0.25), 0 0 24px rgba(0,200,150,0.06)",
        "medium": "0 0 0 1px rgba(240,192,64,0.25), 0 0 24px rgba(240,192,64,0.06)",
        "low":    "0 0 0 1px rgba(224,80,80,0.25), 0 0 24px rgba(224,80,80,0.06)",
    }.get(conf, "0 0 0 1px rgba(255,255,255,0.06)")


def apply_design_system(thumb_glow: str = "rgb(120,200,160)"):
    st.markdown(f"""
<style>
/* ── Fonts ──────────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Global reset ───────────────────────────────────────────────────────── */
*, *::before, *::after {{
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    box-sizing: border-box;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}}
body {{
    font-size: 16px !important;
    line-height: 1.5 !important;
}}

.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {{
    background: #080808 !important;
}}

#MainMenu, footer, header {{ display: none !important; }}
section[data-testid="stSidebar"] {{ display: none !important; }}
hr {{ display: none !important; }}
[data-testid="stDivider"] {{ display: none !important; }}

/* Remove default column borders and padding Streamlit adds */
[data-testid="column"] {{ border: none !important; }}

.block-container {{
    padding: 0 !important;
    max-width: 100% !important;
}}

[data-testid="stVerticalBlock"] > div {{ gap: 0 !important; }}
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="column"] {{
    background: transparent !important;
}}

/* ── Navbar — sticky dark bar ───────────────────────────────────────────── */
[data-testid="stHorizontalBlock"]:first-of-type {{
    position: sticky !important;
    top: 0 !important;
    z-index: 500 !important;
    background: #080808 !important;
}}
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {{
    background: #080808 !important;
    height: 64px !important;
    display: flex !important;
    align-items: center !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    border-bottom: 1px solid rgba(255,255,255,0.06) !important;
}}
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:first-child {{
    padding-left: 40px !important;
    padding-right: 16px !important;
}}
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:last-child {{
    padding-right: 40px !important;
    justify-content: flex-end !important;
}}

/* ── Search input ───────────────────────────────────────────────────────── */
[data-testid="stTextInput"] {{ width: 100% !important; }}
[data-testid="stTextInput"] label {{ display: none !important; }}
[data-testid="stTextInput"] > div {{ background: transparent !important; padding: 0 !important; }}
[data-testid="stTextInput"] > div > div {{
    background: #111111 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    height: 44px !important;
    min-height: 44px !important;
    transition: border-color 0.2s ease !important;
}}
[data-testid="stTextInput"] > div > div:focus-within {{
    border-color: rgba(255,255,255,0.20) !important;
    box-shadow: none !important;
}}
[data-testid="stTextInput"] input {{
    background: transparent !important;
    color: #F0F0F0 !important;
    font-size: 14px !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 14px !important;
    height: 44px !important;
    caret-color: #F0F0F0 !important;
}}
[data-testid="stTextInput"] input::placeholder {{ color: #444 !important; }}

/* ── Buttons — min 44px touch target per Apple HIG / Material ───────────── */
.stButton > button {{
    background: transparent !important;
    color: #888888 !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 8px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 10px 20px !important;
    min-height: 44px !important;
    transition: all 0.2s ease !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    cursor: pointer !important;
    letter-spacing: -0.1px !important;
}}
.stButton > button:hover {{
    color: #F0F0F0 !important;
    border-color: rgba(255,255,255,0.22) !important;
    background: rgba(255,255,255,0.03) !important;
    opacity: 1 !important;
}}
.stButton > button:focus-visible {{
    outline: 2px solid rgba(255,255,255,0.3) !important;
    outline-offset: 2px !important;
}}

/* ── Speculation Slider ─────────────────────────────────────────────────── */
[data-testid="stSlider"] {{
    padding: 0 40px !important;
    overflow: visible !important;
}}
[data-testid="stSlider"] > div {{
    overflow: visible !important;
    padding: 12px 0 !important;
}}
[data-testid="stSlider"] label {{ display: none !important; }}
[data-testid="stThumbValue"] {{ display: none !important; }}
[data-testid="stTickBar"] {{ display: none !important; }}

[data-baseweb="slider"] {{
    padding: 0 !important;
    overflow: visible !important;
    position: relative !important;
}}

/* Track — extend slightly past its bounds so thumb reaches true ends */
[data-baseweb="slider"] > div:first-child {{
    height: 20px !important;
    border-radius: 999px !important;
    background: linear-gradient(
        to right,
        #00C896 0%,
        #FFD750 50%,
        #E05050 100%
    ) !important;
    overflow: visible !important;
    cursor: pointer !important;
    position: relative !important;
    margin-left: -12px !important;
    margin-right: -12px !important;
}}

/* Hide BaseWeb fill div — we show the full gradient always */
[data-baseweb="slider"] > div:first-child > div:first-child {{
    background: transparent !important;
    opacity: 0 !important;
}}

/* ── Thumb: target both the role=slider element AND its child div ── */
/* In Streamlit 1.56, BaseWeb renders the visual circle as a child <div> */
[data-baseweb="slider"] [role="slider"] {{
    overflow: visible !important;
    background: transparent !important;
    border: none !important;
    outline: none !important;
    cursor: grab !important;
    z-index: 100 !important;
    position: absolute !important;
}}

/* The actual white glowing circle — child div inside [role="slider"] */
[data-baseweb="slider"] [role="slider"] > div {{
    width: 24px !important;
    height: 24px !important;
    border-radius: 50% !important;
    background: #FFFFFF !important;
    border: none !important;
    box-shadow:
        0 0 0 4px rgba(255,255,255,0.18),
        0 0 14px rgba(255,255,255,1),
        0 0 28px rgba(255,255,255,0.85),
        0 0 50px rgba(255,255,255,0.50),
        0 0 80px rgba(255,255,255,0.25),
        0 2px 8px rgba(0,0,0,0.6) !important;
    transition: box-shadow 0.15s ease, transform 0.15s ease !important;
    cursor: grab !important;
}}

/* Fallback: if the role=slider element itself IS the visual */
[data-baseweb="slider"] [role="slider"]:not(:has(> div)) {{
    width: 24px !important;
    height: 24px !important;
    border-radius: 50% !important;
    background: #FFFFFF !important;
    box-shadow:
        0 0 0 4px rgba(255,255,255,0.18),
        0 0 14px rgba(255,255,255,1),
        0 0 28px rgba(255,255,255,0.85),
        0 0 50px rgba(255,255,255,0.50),
        0 2px 8px rgba(0,0,0,0.6) !important;
}}

[data-baseweb="slider"] [role="slider"]:hover > div,
[data-baseweb="slider"] [role="slider"]:focus > div {{
    transform: scale(1.18) !important;
    box-shadow:
        0 0 0 5px rgba(255,255,255,0.22),
        0 0 18px rgba(255,255,255,1),
        0 0 36px rgba(255,255,255,0.90),
        0 0 64px rgba(255,255,255,0.60),
        0 0 100px rgba(255,255,255,0.30),
        0 2px 8px rgba(0,0,0,0.6) !important;
}}

[data-baseweb="slider"] [role="slider"]:active > div {{
    cursor: grabbing !important;
    transform: scale(1.1) !important;
}}

[data-baseweb="slider"] [role="slider"]:focus {{
    outline: none !important;
}}

/* ── User dropdown menu ─────────────────────────────────────────────────── */
.user-menu {{
    position: relative;
    display: inline-block;
}}
.user-menu summary {{
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    list-style: none;
    padding: 6px 10px;
    border-radius: 8px;
    transition: background 0.15s ease;
    user-select: none;
}}
.user-menu summary::-webkit-details-marker {{ display: none; }}
.user-menu summary:hover {{ background: rgba(255,255,255,0.05); }}
.user-menu[open] summary {{ background: rgba(255,255,255,0.07); }}
.user-avatar {{
    width: 28px; height: 28px; border-radius: 50%;
    background: linear-gradient(135deg,#7C6AF7,#00C896);
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 600; color: #fff;
    flex-shrink: 0;
}}
.user-name {{
    font-size: 14px; color: #888888;
    font-family: 'Plus Jakarta Sans', sans-serif;
}}
.user-caret {{
    font-size: 10px; color: #444; margin-left: 2px;
    transition: transform 0.15s ease;
}}
.user-menu[open] .user-caret {{ transform: rotate(180deg); }}
.user-dropdown {{
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    min-width: 160px;
    background: #161616;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 10px;
    padding: 4px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04);
    z-index: 1000;
    animation: dropdownIn 0.15s cubic-bezier(0.23,1,0.32,1);
}}
@keyframes dropdownIn {{
    from {{ opacity:0; transform:translateY(-4px); }}
    to   {{ opacity:1; transform:translateY(0); }}
}}
.user-dropdown a {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 14px;
    border-radius: 7px;
    font-size: 13px;
    font-weight: 500;
    color: #888888;
    text-decoration: none;
    transition: all 0.15s ease;
    font-family: 'Plus Jakarta Sans', sans-serif;
}}
.user-dropdown a:hover {{
    background: rgba(255,255,255,0.06);
    color: #F0F0F0;
}}
.user-dropdown .dropdown-divider {{
    height: 1px;
    background: rgba(255,255,255,0.06);
    margin: 4px 0;
}}
.user-dropdown a.danger:hover {{ color: #E05050; }}

/* ── Mode tab bar ────────────────────────────────────────────────────────── */
.pulse-tab-bar {{
    display: flex;
    justify-content: center;
    padding: 24px 0 0;
}}
.pulse-tab-inner {{
    display: inline-flex;
    background: #0d0d0d;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 3px;
    gap: 2px;
}}
.pulse-tab {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 9px 22px;
    border-radius: 7px;
    font-size: 13px;
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.18s ease;
    white-space: nowrap;
    border: 1px solid transparent;
    font-family: 'Plus Jakarta Sans', sans-serif;
    letter-spacing: -0.1px;
}}
.pulse-tab-active {{
    background: #1e1e1e;
    color: #F0F0F0;
    border-color: rgba(255,255,255,0.16);
    box-shadow: 0 1px 4px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
}}
.pulse-tab-inactive {{
    background: transparent;
    color: #555555;
}}
.pulse-tab-inactive:hover {{
    color: #888888;
    background: rgba(255,255,255,0.03);
}}

/* ── Metrics ────────────────────────────────────────────────────────────── */
[data-testid="metric-container"] {{
    background: #111111 !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
    padding: 20px 24px !important;
    transition: border-color 0.2s ease !important;
}}
[data-testid="metric-container"]:hover {{
    border-color: rgba(255,255,255,0.12) !important;
}}
[data-testid="stMetricLabel"] p {{
    font-size: 11px !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: #555555 !important;
}}
[data-testid="stMetricValue"] {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 24px !important;
    font-weight: 600 !important;
    color: #F0F0F0 !important;
    letter-spacing: -0.5px !important;
}}

/* ── Expander ───────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {{
    background: #111111 !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
}}
[data-testid="stExpander"] summary {{ color: #555555 !important; font-size: 13px !important; }}
[data-testid="stExpander"] p,
[data-testid="stExpander"] strong {{ color: #888888 !important; }}

/* ── Spinner ────────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] p {{ color: #555555 !important; font-size: 13px !important; }}

/* ── Scrollbar ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.08); border-radius: 2px; }}
::-webkit-scrollbar-thumb:hover {{ background: rgba(255,255,255,0.14); }}

/* ── Pulse logo heartbeat ────────────────────────────────────────────────── */
@keyframes pulse-heartbeat {{
    0%   {{ transform: scale(1);    text-shadow: 0 0 12px rgba(255,255,255,0.95), 0 0 28px rgba(255,255,255,0.75), 0 0 52px rgba(255,255,255,0.45); }}
    14%  {{ transform: scale(1.12); text-shadow: 0 0 16px rgba(255,255,255,1),    0 0 40px rgba(255,255,255,0.90), 0 0 80px rgba(255,255,255,0.70); }}
    28%  {{ transform: scale(1);    text-shadow: 0 0 12px rgba(255,255,255,0.95), 0 0 28px rgba(255,255,255,0.75), 0 0 52px rgba(255,255,255,0.45); }}
    42%  {{ transform: scale(1.07); text-shadow: 0 0 14px rgba(255,255,255,1),    0 0 32px rgba(255,255,255,0.85), 0 0 64px rgba(255,255,255,0.55); }}
    70%  {{ transform: scale(1);    text-shadow: 0 0 12px rgba(255,255,255,0.95), 0 0 28px rgba(255,255,255,0.75), 0 0 52px rgba(255,255,255,0.45); }}
    100% {{ transform: scale(1);    text-shadow: 0 0 12px rgba(255,255,255,0.95), 0 0 28px rgba(255,255,255,0.75), 0 0 52px rgba(255,255,255,0.45); }}
}}
.pulse-logo {{
    display: inline-block;
    animation: pulse-heartbeat 3.5s ease-in-out infinite;
    transform-origin: center;
}}

/* ── Mode tab buttons — active (tertiary) vs inactive (secondary) ─────────── */
/* Active tab: type="tertiary" → stBaseButton-tertiary */
button[data-testid="stBaseButton-tertiary"] {{
    background: #1e1e1e !important;
    color: #F0F0F0 !important;
    border: 1.5px solid rgba(255,255,255,0.22) !important;
    border-radius: 8px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05) !important;
}}
button[data-testid="stBaseButton-tertiary"]:hover {{
    background: #242424 !important;
    color: #F0F0F0 !important;
    border-color: rgba(255,255,255,0.30) !important;
    opacity: 1 !important;
}}
/* Inactive tab: keep secondary styling (already styled above) */

/* ── Invisible card-click overlay button ─────────────────────────────────── */
.stButton:has(button[data-testid="stBaseButton-primary"]) {{
    margin-top: -200px !important;
    position: relative !important;
    z-index: 50 !important;
    pointer-events: none !important;
    background: transparent !important;
    padding: 0 !important;
    border: none !important;
    box-shadow: none !important;
}}
button[data-testid="stBaseButton-primary"] {{
    width: 100% !important;
    height: 200px !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: transparent !important;
    cursor: pointer !important;
    pointer-events: auto !important;
    padding: 0 !important;
    outline: none !important;
    font-size: 1px !important;
    opacity: 0 !important;
}}
button[data-testid="stBaseButton-primary"]:hover,
button[data-testid="stBaseButton-primary"]:focus,
button[data-testid="stBaseButton-primary"]:active {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}}

/* ── Modal / page back arrow ─────────────────────────────────────────────── */
.modal-back .stButton > button {{
    background: transparent !important;
    color: rgba(255,255,255,0.6) !important;
    border: none !important;
    box-shadow: none !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    letter-spacing: 0 !important;
    height: auto !important;
    min-height: unset !important;
    padding: 6px 0 !important;
    width: auto !important;
    min-width: unset !important;
}}
.modal-back .stButton > button:hover {{
    color: #FFFFFF !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}}

/* ── Progress bar ────────────────────────────────────────────────────────── */
[data-testid="stProgress"] {{
    max-width: 360px !important;
    margin: 0 auto !important;
    padding: 0 !important;
}}
[data-testid="stProgress"] > div {{
    background: rgba(255,255,255,0.06) !important;
    border-radius: 999px !important;
    height: 2px !important;
    overflow: hidden !important;
}}
[data-testid="stProgress"] > div > div {{
    background: linear-gradient(to right, #00C896, #7C6AF7) !important;
    border-radius: 999px !important;
    transition: width 0.4s ease !important;
    height: 2px !important;
}}

/* ── Analyse button (personal mode) ─────────────────────────────────────── */
.pulse-analyse {{ padding: 8px 40px 4px; }}
.pulse-analyse .stButton > button {{
    background: rgba(124,106,247,0.10) !important;
    color: #7C6AF7 !important;
    border: 1px solid rgba(124,106,247,0.25) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 8px 24px !important;
    min-height: 40px !important;
    letter-spacing: -0.1px !important;
}}
.pulse-analyse .stButton > button:hover {{
    background: rgba(124,106,247,0.18) !important;
    border-color: rgba(124,106,247,0.45) !important;
    color: #9D8FF8 !important;
}}

/* ── CTA button (Get Started, Unlock) ───────────────────────────────────── */
.pulse-cta-btn .stButton > button {{
    background: #F0F0F0 !important;
    color: #080808 !important;
    border: none !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    border-radius: 10px !important;
    min-height: 48px !important;
    letter-spacing: -0.2px !important;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.10), 0 4px 24px rgba(255,255,255,0.08) !important;
    transition: opacity 0.2s ease, transform 0.2s ease !important;
}}
.pulse-cta-btn .stButton > button:hover {{
    background: #FFFFFF !important;
    color: #080808 !important;
    opacity: 0.92 !important;
    transform: translateY(-1px) !important;
    border: none !important;
}}

/* ── Global link reset — no browser-default blue or underlines ─────────── */
a, a:link, a:visited, a:hover, a:active, a:focus {
    text-decoration: none !important;
    -webkit-text-decoration: none !important;
}
/* Streamlit markdown renders <a> with its own blue — override */
[data-testid="stMarkdownContainer"] a {
    color: #00C896 !important;
    text-decoration: none !important;
}

/* ── Raise body text contrast globally ─────────────────────────────────── */
[data-testid="stMarkdownContainer"] p {
    color: #C0C0C0;
}

/* ── Scroll-triggered entrance animations ───────────────────────────────── */
@keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(28px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
.anim-section {{
    animation: fadeInUp 0.75s cubic-bezier(0.16, 1, 0.3, 1) both;
}}
.anim-s1 {{ animation-delay: 0.05s; }}
.anim-s2 {{ animation-delay: 0.18s; }}
.anim-s3 {{ animation-delay: 0.31s; }}
.anim-s4 {{ animation-delay: 0.44s; }}
.anim-s5 {{ animation-delay: 0.57s; }}
.anim-s6 {{ animation-delay: 0.70s; }}
/* Modern Chrome: real scroll-triggered firing */
@supports (animation-timeline: view()) {{
    .anim-section {{
        animation-timeline: view();
        animation-range: entry 0% entry 30%;
    }}
}}

/* ── Shared gradient CTA link (paywall, pricing, connect) ───────────────── */
@keyframes glow-pulse {{
    0%,100% {{ box-shadow: 0 0 0 1px rgba(0,200,150,0.4), 0 0 32px rgba(0,200,150,0.28), 0 0 64px rgba(124,106,247,0.14); }}
    50%      {{ box-shadow: 0 0 0 1px rgba(124,106,247,0.5), 0 0 48px rgba(124,106,247,0.32), 0 0 96px rgba(0,200,150,0.16); }}
}}
@keyframes shimmer-slide {{
    0%   {{ left: -60%; }}
    100% {{ left: 120%; }}
}}
.pulse-cta-link {{
    display: block;
    text-align: center;
    text-decoration: none !important;
    background: linear-gradient(135deg, #00C896 0%, #7C6AF7 100%);
    color: #FFFFFF !important;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: -0.2px;
    border-radius: 12px;
    padding: 17px 32px;
    position: relative;
    overflow: hidden;
    animation: glow-pulse 3s ease-in-out infinite;
    transition: opacity 0.2s ease, transform 0.2s ease;
}}
.pulse-cta-link:hover {{ opacity: 0.92; transform: translateY(-2px); }}
.pulse-cta-link .shimmer {{
    position: absolute;
    top: 0;
    left: -60%;
    width: 40%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.22), transparent);
    animation: shimmer-slide 2.4s ease-in-out infinite;
    pointer-events: none;
}}
</style>
""", unsafe_allow_html=True)

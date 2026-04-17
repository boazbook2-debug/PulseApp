# Pulse — Design System

## Philosophy
Dark, precise, premium. Every element should feel like it belongs in a serious health intelligence tool. Reference: ouraring.com meets linear.app. No gradients on backgrounds, no rounded blobs, no consumer wellness app feel. Clean, data-forward, trustworthy.

## Color Palette

### Backgrounds
```
App background:     #080808
Surface 1 (cards):  #111111
Surface 2 (hover):  #161616
Surface 3 (active): #1a1a1a
```

### Borders
```
Default border:     rgba(255, 255, 255, 0.06)
Hover border:       rgba(255, 255, 255, 0.10)
Active border:      rgba(255, 255, 255, 0.16)
```

### Text
```
Primary:    #F0F0F0
Secondary:  #888888
Tertiary:   #555555
Disabled:   #333333
```

### Accent Colors
```
Green (strong evidence / high confidence):  #00C896
Green dim:                                  rgba(0, 200, 150, 0.12)
Green border:                               rgba(0, 200, 150, 0.25)

Yellow (medium evidence):                   #F0C040
Yellow dim:                                 rgba(240, 192, 64, 0.12)
Yellow border:                              rgba(240, 192, 64, 0.25)

Red (speculative / low confidence):         #E05050
Red dim:                                    rgba(224, 80, 80, 0.12)
Red border:                                 rgba(224, 80, 80, 0.25)

Purple (accent / interactive):              #7C6AF7
Purple dim:                                 rgba(124, 106, 247, 0.12)
Purple border:                              rgba(124, 106, 247, 0.25)
```

### Card Shadow System (evidence strength)
```
High confidence (green):    0 0 0 1px rgba(0, 200, 150, 0.3), 0 0 24px rgba(0, 200, 150, 0.08)
Medium confidence (yellow): 0 0 0 1px rgba(240, 192, 64, 0.3), 0 0 24px rgba(240, 192, 64, 0.08)
Low confidence (red):       0 0 0 1px rgba(224, 80, 80, 0.3), 0 0 24px rgba(224, 80, 80, 0.08)
Default (no data):          0 0 0 1px rgba(255, 255, 255, 0.06)
```

### Speculation Slider Colors
```
Left end (evidence based): #00C896
Middle:                    #F0C040
Right end (speculative):   #E05050
```

## Typography

### Font
```
Primary font: Inter (load from Google Fonts)
Monospace:    JetBrains Mono (for data values and numbers)

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
```

### Type Scale
```
Display (hero numbers):   32px / weight 600 / tracking -0.5px
H1 (page title):          22px / weight 600 / tracking -0.3px
H2 (section title):       17px / weight 500 / tracking -0.2px
H3 (card title):          15px / weight 500 / tracking -0.1px
Body:                     14px / weight 400 / line-height 1.6
Small:                    13px / weight 400 / color #888888
Micro:                    11px / weight 500 / tracking 0.05em / uppercase
Data value:               JetBrains Mono 14px / weight 500
```

## Spacing System
```
4px   — micro gap between inline elements
8px   — gap between related elements
12px  — gap between items in a list
16px  — internal card padding (small)
24px  — internal card padding (standard)
32px  — section spacing
48px  — large section spacing
64px  — page section spacing
```

## Border Radius
```
Small elements (tags, badges): 6px
Cards:                         12px
Large cards:                   16px
Buttons:                       8px
Pills:                         999px
```

## Components

### Trend Card
```css
.trend-card {
    background: #111111;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 20px 24px;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
}
.trend-card:hover {
    border-color: rgba(255, 255, 255, 0.12);
    background: #141414;
}
.trend-card.confidence-high   { box-shadow: 0 0 0 1px rgba(0, 200, 150, 0.25), 0 0 24px rgba(0, 200, 150, 0.06); }
.trend-card.confidence-medium { box-shadow: 0 0 0 1px rgba(240, 192, 64, 0.25), 0 0 24px rgba(240, 192, 64, 0.06); }
.trend-card.confidence-low    { box-shadow: 0 0 0 1px rgba(224, 80, 80, 0.25), 0 0 24px rgba(224, 80, 80, 0.06); }
```

### Speculation Slider
```css
.speculation-slider {
    -webkit-appearance: none;
    width: 100%;
    height: 3px;
    border-radius: 2px;
    outline: none;
    cursor: pointer;
}
.speculation-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #F0F0F0;
    cursor: pointer;
    border: 2px solid #080808;
    box-shadow: 0 0 12px rgba(255, 255, 255, 0.2);
}
```

### Navigation Bar
```css
.navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 40px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    background: #080808;
    position: sticky;
    top: 0;
    z-index: 100;
}
.navbar-logo { font-size: 18px; font-weight: 600; color: #F0F0F0; letter-spacing: -0.3px; }
.navbar-search {
    background: #111111;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 8px 14px;
    color: #F0F0F0;
    font-size: 14px;
    width: 280px;
    outline: none;
    transition: border-color 0.2s ease;
}
.navbar-search:focus { border-color: rgba(255, 255, 255, 0.16); }
.navbar-search::placeholder { color: #444444; }
```

### Paper Card
```css
.paper-card {
    background: #111111;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
    transition: border-color 0.2s ease;
}
.paper-card:hover { border-color: rgba(255, 255, 255, 0.10); }
.paper-card-title { font-size: 14px; font-weight: 500; color: #F0F0F0; margin-bottom: 8px; line-height: 1.4; }
.paper-card-summary { font-size: 13px; color: #888888; line-height: 1.6; margin-bottom: 10px; }
```

### Buttons
```css
.btn-primary {
    background: #7C6AF7; color: #FFFFFF; border: none;
    border-radius: 8px; padding: 10px 20px;
    font-size: 14px; font-weight: 500; cursor: pointer;
    transition: opacity 0.2s ease;
}
.btn-primary:hover { opacity: 0.88; }
.btn-secondary {
    background: transparent; color: #888888;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px; padding: 10px 20px;
    font-size: 14px; font-weight: 500; cursor: pointer;
    transition: all 0.2s ease;
}
.btn-secondary:hover { color: #F0F0F0; border-color: rgba(255, 255, 255, 0.16); }
```

## Grid Layout
```css
.cards-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    padding: 0 40px;
}
@media (max-width: 1100px) { .cards-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 700px)  { .cards-grid { grid-template-columns: 1fr; } }
```

## Streamlit CSS Override Block
```python
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
* { font-family: 'Inter', sans-serif; box-sizing: border-box; }
.stApp { background-color: #080808; }
.block-container { padding: 0; max-width: 100%; }
header { display: none; }
.stMarkdown p { color: #888888; font-size: 14px; line-height: 1.6; }
.stTextInput input {
    background: #111111;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    color: #F0F0F0;
}
.stTextInput input:focus { border-color: rgba(255,255,255,0.16); box-shadow: none; }
.stButton button {
    background: #7C6AF7; color: white;
    border: none; border-radius: 8px;
    font-family: Inter; font-weight: 500;
}
div[data-testid="stSidebar"] { background: #0d0d0d; border-right: 1px solid rgba(255,255,255,0.06); }
</style>
""", unsafe_allow_html=True)
```

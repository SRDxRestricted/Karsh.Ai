"""
theme.py — Shared dark-theme config, CSS injection, and sidebar renderer for Karsh.Ai
"""
import streamlit as st


def init_theme():
    """Initialize session-state defaults (called once per page)."""
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = True


def inject_global_css():
    """Inject the global dark-theme CSS into the current page."""
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ── Base ─────────────────────────────────────────────── */
.stApp {
    background-color: #16162a !important;
    font-family: 'Inter', sans-serif;
    color: #e0e0e0;
}
header { visibility: hidden; }
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1100px;
}

/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #1e1e36 !important;
    border-right: 1px solid #2a2a4a !important;
}
/* Kill ALL top space */
[data-testid="stSidebar"] > div {
    padding-top: 0 !important;
}
[data-testid="stSidebar"] > div > div {
    padding-top: 0 !important;
}
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {
    display: none !important;
}
[data-testid="stSidebarNav"] {
    display: none !important;
}
[data-testid="stSidebarUserContent"] {
    padding-top: 0 !important;
}

/* Sidebar page_link buttons */
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
    background: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 9px 14px !important;
    margin: 1px 8px !important;
    transition: all 0.15s ease !important;
    text-decoration: none !important;
}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover {
    background: rgba(0, 200, 83, 0.07) !important;
}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] {
    background: rgba(0, 200, 83, 0.12) !important;
    border-left: 3px solid #00c853 !important;
    border-radius: 0 8px 8px 0 !important;
}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] p {
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    color: #b0b0cc !important;
}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] p {
    color: #00c853 !important;
    font-weight: 700 !important;
}

/* ── Hero ─────────────────────────────────────────────── */
.hero-title {
    text-align: center;
    color: #00c853;
    font-size: 2.6rem;
    font-weight: 900;
    margin-bottom: 0;
}
.hero-sub {
    text-align: center !important;
    color: #9e9eb8;
    font-size: 1rem;
    max-width: 620px;
    margin: 8px auto 28px auto !important;
    line-height: 1.55;
    display: block;
}

/* ── Stat numbers ─────────────────────────────────────── */
.stat-num {
    color: #00c853;
    font-size: 1.8rem;
    font-weight: 900;
    text-align: center;
}
.stat-label {
    color: #9e9eb8;
    font-size: 0.82rem;
    font-weight: 600;
    text-align: center;
}

/* ── Cards (bordered containers) ──────────────────────── */
[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #1e1e36 !important;
    border: 1px solid #2a2a4a !important;
    border-radius: 14px !important;
}

/* ── Confidence bar ───────────────────────────────────── */
.conf-bg {
    background: #2a2a4a; border-radius: 6px;
    height: 8px; width: 100%; margin: 6px 0 4px 0;
}
.conf-fill {
    background: linear-gradient(90deg, #00c853, #69f0ae);
    height: 8px; border-radius: 6px;
}

/* ── Info strip (green) ───────────────────────────────── */
.info-strip {
    background: #152e15; border: 1px solid #2e5c2e;
    border-radius: 8px; padding: 10px 16px;
    color: #69f0ae; font-size: 0.82rem;
    margin-top: 12px;
}

/* ── Scheme card ──────────────────────────────────────── */
.scheme-card {
    background: #1e1e36; border: 1px solid #2a2a4a;
    border-radius: 12px; padding: 20px;
    margin-bottom: 14px;
}
.scheme-card h4 { color: #e0e0e0; margin: 0 0 4px 0; font-size: 1.05rem; }
.scheme-meta { color: #9e9eb8; font-size: 0.82rem; margin-top: 8px; }
.scheme-meta span { margin-right: 22px; }

/* ── Footer ───────────────────────────────────────────── */
.footer-text {
    text-align: center;
    color: #7a7a9e;
    font-size: 0.78rem;
    margin-top: 40px;
    padding: 14px 0;
    border-top: 1px solid #2a2a4a;
}

/* ── Form & Input polish ──────────────────────────────── */
input, textarea, [data-baseweb="select"] {
    border-color: #2a2a4a !important;
}
input:focus, textarea:focus {
    border-color: #00c853 !important;
    box-shadow: 0 0 0 1px #00c853 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-highlight"] {
    background-color: #00c853 !important;
}

/* Buttons */
button[kind="primary"], button[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #00c853, #009624) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
}

/* Dividers */
hr {
    border-color: #2a2a4a !important;
}

/* Success / error / info / warning banners */
[data-testid="stAlert"] {
    border-radius: 10px !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def render_sidebar():
    """Render the branded sidebar navigation."""

    # ── Brand ──
    st.sidebar.markdown(
        """
<div style='padding:14px 16px 8px 16px;'>
    <div style='display:flex;align-items:center;gap:9px;'>
        <span style='font-size:1.6rem;'>🌾</span>
        <span style='color:#00c853;font-size:1.4rem;font-weight:900;letter-spacing:-0.3px;'>Karsh.Ai</span>
    </div>
    <p style='color:#7a7a9e;font-size:0.72rem;margin:4px 0 0 0;font-weight:500;'>AI-Powered Farming Assistant</p>
</div>
""",
        unsafe_allow_html=True,
    )

    # ── Divider + section label ──
    st.sidebar.markdown(
        "<hr style='border:none;border-top:1px solid #2a2a4a;margin:8px 12px;'>"
        "<p style='color:#7a7a9e;font-size:0.65rem;font-weight:700;"
        "text-transform:uppercase;letter-spacing:1.5px;padding:0 16px;"
        "margin:4px 0 6px 0;'>Navigation</p>",
        unsafe_allow_html=True,
    )

    # ── Nav links (no icons) ──
    st.sidebar.page_link("app.py", label="Homepage")
    st.sidebar.page_link("pages/1_\U0001F399\uFE0F_Malayalam_Voice_Assistant.py", label="Voice Assistant")
    st.sidebar.page_link("pages/2_\U0001F331_Crop_Predictor.py", label="Crop Predictor")
    st.sidebar.page_link("pages/3_\U0001F3DB\uFE0F_Govt_Scheme_Finder.py", label="Govt. Schemes")
    st.sidebar.page_link("pages/4_\U0001F4F8_Plant_Identifier.py", label="Plant Identifier")

    # ── Footer ──
    st.sidebar.markdown(
        "<div style='position:fixed;bottom:16px;padding:0 16px;'>"
        "<p style='color:#5a5a7e;font-size:0.7rem;font-weight:500;margin:0;'>Built for Kerala Farmers</p>"
        "</div>",
        unsafe_allow_html=True,
    )

import streamlit as st
from theme import init_theme, inject_global_css, render_sidebar
from auth import require_auth, get_username, get_user_district
from early_warning_system.early_warning_system import fetch_weather_forecast, analyze_for_calamities

# Kerala district coordinates
DISTRICT_COORDS = {
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Kollam":            (8.8932, 76.6141),
    "Pathanamthitta":    (9.2648, 76.7870),
    "Alappuzha":         (9.4981, 76.3388),
    "Kottayam":          (9.5916, 76.5222),
    "Idukki":            (9.8500, 76.9492),
    "Ernakulam":         (9.9816, 76.2999),
    "Thrissur":          (10.5276, 76.2144),
    "Palakkad":          (10.7867, 76.6548),
    "Malappuram":        (11.0510, 76.0711),
    "Kozhikode":         (11.2588, 75.7804),
    "Wayanad":           (11.6854, 76.1320),
    "Kannur":            (11.8745, 75.3704),
    "Kasaragod":         (12.4996, 74.9869),
}

st.set_page_config(
    page_title="Karsh.Ai — AI Farming Assistant",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_theme()
inject_global_css()

# Gate: must log in before seeing anything
require_auth()

render_sidebar()

# ── Hero ────────────────────────────────────────────────────────────────────
st.markdown('<h1 class="hero-title">Karsh.Ai</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="hero-sub">Welcome back, <strong>{get_username()}</strong>. An AI-powered agricultural companion built for Kerala\'s farming communities.</p>', unsafe_allow_html=True)

# ── Stats Row ───────────────────────────────────────────────────────────────
s1, s2, s3, s4 = st.columns(4)
with s1:
    st.markdown('<div class="stat-num">14</div><div class="stat-label">Kerala Districts</div>', unsafe_allow_html=True)
with s2:
    st.markdown('<div class="stat-num">50+</div><div class="stat-label">Crops Tracked</div>', unsafe_allow_html=True)
with s3:
    st.markdown('<div class="stat-num">100%</div><div class="stat-label">Offline Capable</div>', unsafe_allow_html=True)
with s4:
    st.markdown('<div class="stat-num">മലയാളം</div><div class="stat-label">Voice Support</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Early Warning System (user's district) ──────────────────────────────────
user_district = get_user_district()
lat, lon = DISTRICT_COORDS.get(user_district, (9.9816, 76.2999))

st.markdown(f"### Early Warning — {user_district}")

with st.spinner(f"Fetching 48-hr forecast for {user_district}..."):
    weather_data = fetch_weather_forecast(lat, lon)

if weather_data:
    warnings = analyze_for_calamities(weather_data)
    if warnings:
        total = sum(len(w['alerts']) for w in warnings)
        st.error(f"**{total} alert(s)** detected in {user_district} over the next 48 hours", icon="⚠️")
        shown = 0
        for w in warnings:
            if shown >= 5:
                break
            for alert in w['alerts']:
                if shown >= 5:
                    break
                icon = "🌧️" if "RAIN" in alert else "🌪️" if "WIND" in alert else "🌡️" if "HEAT" in alert else "⚠️"
                st.markdown(
                    f"<div style='background:#2a1515;border:1px solid #5c2020;border-radius:10px;"
                    f"padding:14px 18px;margin-bottom:8px;display:flex;align-items:center;gap:12px;'>"
                    f"<span style='font-size:1.4rem;'>{icon}</span>"
                    f"<div>"
                    f"<div style='font-weight:700;color:#ff6b6b;font-size:0.9rem;'>{w['time']}</div>"
                    f"<div style='color:#d0d0d0;font-size:0.85rem;'>{alert}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
                shown += 1
        if total > 5:
            st.caption(f"+ {total - 5} more alert(s) not shown")
    else:
        st.success(f"All clear in {user_district} — no extreme weather predicted for the next 48 hours.", icon="✅")
else:
    st.warning("Could not fetch meteorological data. Check your internet connection.", icon="📡")

st.markdown("---")
st.markdown("### Platform Features")

# ── Feature Cards ───────────────────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    with st.container(border=True):
        st.markdown("#### 🌱 Crop Predictor System")
        st.markdown(
            "AI-driven crop recommendations based on historical market data, "
            "seasonal patterns, and district-specific conditions across Kerala. "
            "Powered by a Random Forest model trained on real agricultural records."
        )
        st.success("✓ Live", icon="✅")
        st.page_link("pages/2_🌱_Crop_Predictor.py", label="Open Crop Predictor →", use_container_width=True)

with c2:
    with st.container(border=True):
        st.markdown("#### 🎙️ Malayalam Voice Assistant")
        st.markdown(
            "Ask questions in Malayalam using your voice and receive spoken answers. "
            "Supports both online (Gemini + gTTS) and fully offline (Phi-3 LLM + espeak-ng) "
            "modes for zero-connectivity environments."
        )
        st.success("✓ Live", icon="✅")
        st.page_link("pages/1_🎙️_Malayalam_Voice_Assistant.py", label="Open Voice Assistant →", use_container_width=True)

c3, c4 = st.columns(2)

with c3:
    with st.container(border=True):
        st.markdown("#### 🏛️ Govt. Scheme Finder")
        st.markdown(
            "Discover central and state government agricultural schemes, subsidies, "
            "and loan programs tailored to your crop type, land size, and district. "
            "Never miss a beneficial program again."
        )
        st.info("Beta", icon="🔬")
        st.page_link("pages/3_🏛️_Govt_Scheme_Finder.py", label="Open Scheme Finder →", use_container_width=True)

with c4:
    with st.container(border=True):
        st.markdown("#### 📸 Plant / Crop Identifier")
        st.markdown(
            "Take a photo of any crop or plant and instantly receive identification, "
            "health analysis, disease detection, and care recommendations "
            "powered by Gemini's multimodal vision AI."
        )
        st.info("Beta", icon="🔬")
        st.page_link("pages/4_📸_Plant_Identifier.py", label="Open Plant Identifier →", use_container_width=True)

# ── Footer ──────────────────────────────────────────────────────────────────
st.markdown('<div class="footer-text">Karsh.Ai · Built by Team Xenonites404 · Hackathon 2026</div>', unsafe_allow_html=True)
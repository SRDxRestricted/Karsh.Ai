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
st.markdown(f'<p class="hero-sub">Hello, <strong>{get_username()}</strong>! Your farming assistant is ready. Check the weather, find the right crop to plant, or discover government schemes you qualify for.</p>', unsafe_allow_html=True)

# ── Stats Row ───────────────────────────────────────────────────────────────
s1, s2, s3, s4 = st.columns(4)
with s1:
    st.markdown('<div class="stat-num">14</div><div class="stat-label">Districts Covered</div>', unsafe_allow_html=True)
with s2:
    st.markdown('<div class="stat-num">50+</div><div class="stat-label">Crops Supported</div>', unsafe_allow_html=True)
with s3:
    st.markdown('<div class="stat-num">100%</div><div class="stat-label">Works Offline</div>', unsafe_allow_html=True)
with s4:
    st.markdown('<div class="stat-num">മലയാളം</div><div class="stat-label">Voice Ready</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Early Warning System (user's district) ──────────────────────────────────
user_district = get_user_district()
lat, lon = DISTRICT_COORDS.get(user_district, (9.9816, 76.2999))

st.markdown(f"### Weather in {user_district}")

with st.spinner(f"Fetching 48-hr forecast for {user_district}..."):
    weather_data = fetch_weather_forecast(lat, lon)

if weather_data:
    warnings = analyze_for_calamities(weather_data)
    if warnings:
        total = sum(len(w['alerts']) for w in warnings)
        st.error(f"**{total} alert(s)** detected in {user_district} over the next 48 hours")
        shown = 0
        for w in warnings:
            if shown >= 5:
                break
            for alert in w['alerts']:
                if shown >= 5:
                    break
                icon = "Alert" if "RAIN" in alert else "Alert" if "WIND" in alert else "Alert" if "HEAT" in alert else "Alert"
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
        st.success(f"All clear in {user_district} — no extreme weather predicted for the next 48 hours.")
else:
    st.warning("Could not fetch meteorological data. Check your internet connection.")

st.markdown("---")
st.markdown("### What can Karsh.Ai do for you?")

# ── Feature Cards ───────────────────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    with st.container(border=True):
        st.markdown("#### Which crop should I plant?")
        st.markdown(
            "Tell us your district, the month you want to plant, and how much land you have. "
            "We'll suggest the best crops and show you how much you could earn."
        )
        st.success("Ready to use")
        st.page_link("pages/2_Crop_Predictor.py", label="Find best crops", use_container_width=True)

with c2:
    with st.container(border=True):
        st.markdown("#### Ask a farming question")
        st.markdown(
            "Type or speak your question in English or Malayalam. "
            "Get answers about diseases, fertilizers, planting schedules, and more."
        )
        st.success("Ready to use")
        st.page_link("pages/1_Malayalam_Voice_Assistant.py", label="Ask a question", use_container_width=True)

c3, c4 = st.columns(2)

with c3:
    with st.container(border=True):
        st.markdown("#### Am I eligible for any schemes?")
        st.markdown(
            "Enter your income and land size, and we'll match you "
            "with central and state government schemes, subsidies, and loans you can apply for."
        )
        st.page_link("pages/3_Govt_Scheme_Finder.py", label="Check schemes", use_container_width=True)

with c4:
    with st.container(border=True):
        st.markdown("#### What's wrong with my plant?")
        st.markdown(
            "Upload a photo of a leaf or plant. "
            "We'll identify the crop, spot any diseases, and suggest what to do next."
        )
        st.page_link("pages/4_Plant_Identifier.py", label="Upload a photo", use_container_width=True)

# ── Footer ──────────────────────────────────────────────────────────────────
st.markdown('<div class="footer-text">Karsh.Ai · Built by Team Xenonites404</div>', unsafe_allow_html=True)
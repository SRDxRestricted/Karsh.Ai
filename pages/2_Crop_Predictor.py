import streamlit as st
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import init_theme, inject_global_css, render_sidebar
from auth import require_auth
from crop_predictor.crop_predictor import initialize_model, predict_top_crops

st.set_page_config(page_title="Karsh.Ai | Crop Predictor", page_icon="🌱", layout="wide")
init_theme(); inject_global_css(); require_auth(); render_sidebar()

initialize_model()

st.markdown("### Crop Predictor")
st.markdown("Get AI-driven crop recommendations based on your district, planting season, and land area.")
st.markdown("")

c1, c2, c3, c4 = st.columns([2, 2, 1.5, 1])
with c1:
    st.markdown("District")
    district = st.selectbox("District", [
        "Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha", "Kottayam", "Idukki",
        "Ernakulam", "Thrissur", "Palakkad", "Malappuram", "Kozhikode", "Wayanad", "Kannur", "Kasaragod"
    ], label_visibility="collapsed")
with c2:
    st.markdown("Planting Month")
    month = st.selectbox("Month", list(range(1, 13)), format_func=lambda x: [
        "January","February","March","April","May","June",
        "July","August","September","October","November","December"][x-1], label_visibility="collapsed")
with c3:
    st.markdown("Land Area (Hectares)")
    land_area = st.number_input("Land", min_value=0.1, value=1.3, step=0.1, label_visibility="collapsed")
with c4:
    st.markdown("&nbsp;")
    predict_btn = st.button("Predict", use_container_width=True, type="primary")

if predict_btn:
    with st.spinner("Analyzing market data..."):
        results = predict_top_crops(month, district, land_area)
        if results:
            st.markdown("### Recommended Crops & Financial Forecast")
            for idx, res in enumerate(results):
                conf_pct = float(res['match_score'].replace('%', ''))
                st.markdown(f"""
                <div style='background:#1e1e36;border:1px solid #2a2a4a;border-radius:14px;padding:22px;margin-bottom:18px;'>
                    <div style='display:flex;align-items:flex-start;gap:20px;'>
                        <div style='font-size:2rem;font-weight:900;color:#9e9eb8;min-width:50px;'>#{idx+1}</div>
                        <div style='flex:1;'>
                            <div style='font-size:1.15rem;font-weight:700;color:#e0e0e0;'>{res['crop']}</div>
                            <div class='conf-bg'><div class='conf-fill' style='width:{conf_pct}%;'></div></div>
                            <div style='color:#9e9eb8;font-size:0.8rem;'>AI Confidence: {res['match_score']}</div>
                        </div>
                        <div style='text-align:center;min-width:140px;'>
                            <div style='color:#9e9eb8;font-size:0.75rem;font-weight:600;'>Est. Yield (Units)</div>
                            <div style='color:#00c853;font-size:1.6rem;font-weight:800;'>{res['est_yield']:,.0f}</div>
                        </div>
                        <div style='text-align:right;min-width:160px;'>
                            <div style='color:#9e9eb8;font-size:0.75rem;font-weight:600;'>Est. Revenue</div>
                            <div style='color:#00c853;font-size:1.6rem;font-weight:800;'>₹{res["est_revenue"]:,.2f}</div>
                        </div>
                    </div>
                    <div class='info-strip'>
                        Best Recommended Market: {res['best_market']} &nbsp;&nbsp;|&nbsp;&nbsp; Historical Price Range: {res['price_range']} per Quintal
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No suitable crops found for this selection.")

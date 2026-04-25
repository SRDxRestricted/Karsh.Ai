import streamlit as st
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import init_theme, inject_global_css, render_sidebar
from auth import require_auth
from scheme_recommender.recommender import recommend_schemes

st.set_page_config(page_title="Karsh.Ai | Govt. Schemes", page_icon="🏛️", layout="wide")
init_theme(); inject_global_css(); require_auth(); render_sidebar()

st.markdown("### 🏛 Govt. Scheme Finder")
st.markdown("Discover Central & Kerala State government agricultural schemes, subsidies, and loan programs tailored for you.")

st.markdown("#### 👤 Farmer Profile")
p1, p2 = st.columns(2)
with p1:
    income = st.number_input("Monthly Income (₹)", min_value=0, value=15000, step=1000)
with p2:
    land_size = st.number_input("Land Size Owned (Hectares)", min_value=0.0, value=1.5, step=0.1)

st.markdown("#### 🔍 Scheme Filters")
f1, f2, f3 = st.columns(3)
with f1:
    crop_options = ["All", "Paddy", "Coconut", "Banana", "Rubber", "Black Pepper", "Cardamom",
        "Tapioca", "Coffee", "Tea", "Ginger", "Turmeric", "Vegetables",
        "Fruits", "Sugarcane", "Cotton", "Millets", "Pulses", "Oilseeds", "Spices"]
    crop_filter = st.selectbox("🌿 Crop Type", crop_options)
with f2:
    cat_filter = st.selectbox("📁 Category", ["All", "Central Sector Scheme", "State Sector Scheme", "Centrally Sponsored Scheme"])
with f3:
    gov_filter = st.selectbox("🏛 Government Level", ["All", "Central", "Kerala"])

# Build crop list
if crop_filter == "All":
    crop_types = [c for c in crop_options if c != "All"]
else:
    crop_types = [crop_filter]

schemes = recommend_schemes(income, land_size, crop_types)

# Apply filters
if cat_filter != "All":
    schemes = [s for s in schemes if s.get('type', '').lower() == cat_filter.lower()]
if gov_filter != "All":
    label = "Central Government" if gov_filter == "Central" else "Kerala Government"
    schemes = [s for s in schemes if s.get('source', '') == label]

st.markdown(f"### Showing {len(schemes)} scheme(s)")

for scheme in schemes:
    source_flag = "🇮🇳 Central" if scheme.get('source') == "Central Government" else "🏠 Kerala"
    st.markdown(f"""
    <div class='scheme-card'>
        <h4>🏛 {scheme['scheme_name']}</h4>
        <p style='color:#9e9eb8;font-size:0.88rem;margin:0;'>Benefit: {scheme.get('benifit', 'N/A')}</p>
        <div class='scheme-meta'>
            <span>{source_flag}</span>
            <span>{scheme.get('type', 'N/A')}</span>
            <span>Max Land: {scheme.get('Land limit', 'Any')}</span>
            <span>Max Income: {scheme.get('income_limit', 'Any')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

if not schemes:
    st.info("No schemes match your current filters. Try adjusting your profile or filters.")

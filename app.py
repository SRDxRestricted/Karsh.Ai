import streamlit as st
import json
import os
import sys
import ollama

# Import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from crop_predictor.crop_predictor import initialize_model, predict_top_crops
from imageProcessing.photoAnalyzer import analyze_crop
from imageProcessing.extractingInfo import extract_farmer_profile
from scheme_recommender.recommender import recommend_schemes
from early_warning_system.early_warning_system import fetch_weather_forecast, analyze_for_calamities, LATITUDE, LONGITUDE
import importlib.util

spec = importlib.util.spec_from_file_location("translate_and_speak", os.path.join(os.path.dirname(__file__), "Malayalam TTS", "translate_and_speak.py"))
tts_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tts_module)

st.set_page_config(page_title="Karsh.Ai", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

# CSS for Dashboard aesthetic
st.markdown("""
<style>
    /* Global Background and Fonts */
    .stApp {
        background-color: #f3f6f4;
        font-family: 'Inter', sans-serif;
    }

    /* Remove top padding for a clean top bar area */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 1200px;
    }
    
    /* Hide Streamlit Header */
    header {visibility: hidden;}

    /* Sidebar Styling - FORCED FIXED */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0 !important;
        min-width: 260px !important;
        max-width: 260px !important;
        transform: translateX(0) !important;
        visibility: visible !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        z-index: 999999 !important;
        height: 100vh !important;
    }
    
    /* Shift main content right to avoid overlapping fixed sidebar */
    [data-testid="stAppViewContainer"] {
        padding-left: 260px !important;
    }
    .main .block-container {
        max-width: 1000px !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    
    /* Completely hide all toggle buttons */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    button[kind="header"] {
        display: none !important;
        visibility: hidden !important;
    }
    .css-1544g2n.e1fqcg0o4 {
        padding-top: 2rem;
    }
    
    /* Common Card Styling */
    .dash-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        margin-bottom: 20px;
    }

    /* Alerts */
    .alert-card {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 8px;
        padding: 15px;
        height: 100%;
    }
    .alert-title {
        color: #b91c1c;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 5px;
    }
    
    /* Feature Cards */
    .feature-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        cursor: pointer;
        transition: transform 0.2s;
    }
    .feature-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }
    .feature-card.primary {
        background: #065f46;
        color: white;
        border: none;
    }

    /* Buttons and Overrides */
    .stButton>button {
        font-size: 1rem !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        border-radius: 8px !important;
        border: 1px solid #e2e8f0 !important;
    }
    .stButton>button[kind="primary"] {
        background: #065f46 !important;
        color: white !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Crop Model safely without caching bugs
initialize_model()

def stream_general_chat(text):
    try:
        response = ollama.chat(
            model='gemma4:e2b',
            messages=[
                {'role': 'system', 'content': 'You are a helpful Kerala farming assistant. Always respond in English unless specifically asked to speak Malayalam.'},
                {'role': 'user', 'content': text}
            ],
            stream=True
        )
        for chunk in response:
            yield chunk['message']['content']
    except Exception as e:
        yield f"Error: {e}"

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown("""
    <div style='margin-bottom: 30px;'>
        <h2 style='color: #065f46; margin-bottom: 0; font-size: 1.8rem; font-weight: 900;'>Karsh.Ai</h2>
        <p style='color: #64748b; font-size: 0.85rem; margin-top: -5px; font-weight: 600;'>Precision Agriculture</p>
    </div>
""", unsafe_allow_html=True)

page = st.sidebar.radio(
    "Navigation", 
    ["Dashboard", "AI Chat Assistant", "Scheme Discovery", "Profile Extraction", "Crop Predictor"], 
    label_visibility="collapsed"
)

st.sidebar.markdown("<br>" * 10, unsafe_allow_html=True)
st.sidebar.markdown("<p style='color:#64748b; font-weight:600; font-size:0.9rem; cursor:pointer;'>❔ Support</p>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='color:#64748b; font-weight:600; font-size:0.9rem; cursor:pointer;'>🚪 Sign Out</p>", unsafe_allow_html=True)

# --- PAGE CONTENT ---

if page == "Dashboard":
    # Greeting
    st.markdown("""
        <h1 style='color: #065f46; margin-bottom: 0; font-size: 2.2rem;'>Good morning, Ravi</h1>
        <p style='color: #64748b; font-size: 1.05rem; margin-top: 5px; margin-bottom: 25px;'>Here is your farm overview and alerts for today.</p>
    """, unsafe_allow_html=True)
    
    # Real Early Warning Alerts
    with st.spinner("Fetching meteorological data..."):
        weather_data = fetch_weather_forecast(LATITUDE, LONGITUDE)
        
    if weather_data:
        warnings = analyze_for_calamities(weather_data)
        
        if warnings:
            st.markdown("""
                <div class="dash-card" style="background:#fff1f2; border: 1px solid #ffe4e6;">
                    <h3 style="margin:0 0 15px 0; font-size:1.1rem; color:#be123c; display:flex; align-items:center; gap:8px;">⚠️ Early Warning Alerts (Next 48 Hours)</h3>
                    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap:15px;">
            """, unsafe_allow_html=True)
            
            for w in warnings:
                time_str = w['time']
                for alert in w['alerts']:
                    icon = "⚠️"
                    if "RAIN" in alert: icon = "🌧️"
                    elif "WINDS" in alert: icon = "🌪️"
                    elif "HEAT" in alert: icon = "🌡️"
                    
                    st.markdown(f"""
                        <div style="background:white; padding:15px; border-radius:8px; display:flex; gap:10px; border:1px solid #fecaca;">
                            <div style="background:#fee2e2; width:35px; height:35px; border-radius:8px; display:flex; align-items:center; justify-content:center; color:#b91c1c;">{icon}</div>
                            <div>
                                <div style="font-weight:700; color:#0f172a; font-size:0.95rem; margin-bottom:4px;">{time_str}</div>
                                <div style="font-size:0.8rem; color:#64748b; line-height:1.4;">{alert}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="dash-card" style="background:#f0fdf4; border: 1px solid #dcfce7;">
                    <h3 style="margin:0 0 5px 0; font-size:1.1rem; color:#166534; display:flex; align-items:center; gap:8px;">✅ All Clear</h3>
                    <p style="margin:0; font-size:0.9rem; color:#166534;">No extreme weather events predicted for the next 48 hours. Normal farming activities can proceed.</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Could not fetch meteorological data.")
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            <div class="feature-card primary">
                <div style="display:flex; justify-content:space-between; margin-bottom:40px;">
                    <span style="font-size:1.5rem;">🧠</span>
                    <span style="font-size:1.5rem;">→</span>
                </div>
                <h3 style="margin:0 0 5px 0; font-size:1.2rem;">Crop Predictor</h3>
                <p style="margin:0; font-size:0.85rem; opacity:0.9; line-height:1.4;">AI-driven yield forecasts and optimal harvest timing based on current growth data.</p>
            </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
            <div class="feature-card">
                <div style="display:flex; justify-content:space-between; margin-bottom:40px;">
                    <span style="font-size:1.5rem;">🏛️</span>
                    <span style="font-size:1.5rem; color:#94a3b8;">→</span>
                </div>
                <h3 style="margin:0 0 5px 0; font-size:1.2rem; color:#1e293b;">Scheme Discovery</h3>
                <p style="margin:0; font-size:0.85rem; color:#64748b; line-height:1.4;">Personalized government subsidies and insurance programs matched to your farm profile.</p>
            </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
            <div class="feature-card">
                <div style="display:flex; justify-content:space-between; margin-bottom:40px;">
                    <span style="font-size:1.5rem;">💬</span>
                    <span style="font-size:1.5rem; color:#94a3b8;">→</span>
                </div>
                <h3 style="margin:0 0 5px 0; font-size:1.2rem; color:#1e293b;">AI Chat Assistant</h3>
                <p style="margin:0; font-size:0.85rem; color:#64748b; line-height:1.4;">Your virtual agronomist. Ask questions and get crop health diagnostics instantly.</p>
            </div>
        """, unsafe_allow_html=True)

elif page == "AI Chat Assistant":
    st.subheader("Your Virtual Agronomist")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if "image" in msg and msg["image"]:
                st.image(msg["image"], width=300)
            st.markdown(msg["content"])

    if prompt := st.chat_input(
        "Ask Karsh.Ai a question or describe your crop issues...",
        accept_file=True,
        file_type=["jpg", "jpeg", "png"]
    ):
        img_bytes = None
        if prompt.files:
            img_bytes = prompt.files[0].read()
            
        prompt_text = prompt.text
        
        user_msg = {"role": "user", "content": prompt_text}
        if img_bytes:
            user_msg["image"] = img_bytes
        st.session_state.messages.append(user_msg)
        
        with st.chat_message("user"):
            if img_bytes:
                st.image(img_bytes, width=300)
            if prompt_text:
                st.markdown(prompt_text)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result_container = st.empty()
                full_response = ""
                
                if img_bytes:
                    st.caption("*(Running Crop Diagnosis...)*")
                    for chunk in analyze_crop(img_bytes):
                        full_response += chunk
                        result_container.markdown(full_response + "▌")
                else:
                    for chunk in stream_general_chat(prompt_text):
                        full_response += chunk
                        result_container.markdown(full_response + "▌")
                        
                result_container.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        if st.button("🔊 Listen in Malayalam", key=f"tts_{len(st.session_state.messages)}"):
            with st.spinner("Translating and generating audio..."):
                try:
                    audio_path = tts_module.speak_malayalam_from_english(st.session_state.messages[-1]["content"][:1000])
                    st.audio(audio_path, format="audio/mp3")
                except Exception as e:
                    st.error(f"TTS Failed: {e}")

elif page == "Scheme Discovery":
    st.header("🏛️ Scheme Discovery")
    st.markdown("Find the financial support you are entitled to based on your land and income.")
    
    col1, col2 = st.columns(2)
    with col1:
        income = st.number_input("Monthly Income (₹)", min_value=0, value=10000, step=1000)
    with col2:
        land_size = st.number_input("Land Size (in hectares)", min_value=0.0, value=1.0, step=0.1)
        
    if st.button("Find Schemes", use_container_width=True, type="primary"):
        schemes = recommend_schemes(income, land_size)
        if schemes:
            st.success(f"Found {len(schemes)} eligible scheme(s)!")
            for idx, scheme in enumerate(schemes):
                with st.expander(f"{idx+1}. {scheme['scheme_name']} ({scheme['source']})"):
                    st.markdown(f"**Type:** {scheme['type']}")
                    st.markdown(f"**Benefit:** {scheme.get('benifit', 'N/A')}")
                    st.markdown(f"**Eligibility:** Land up to {scheme.get('Land limit', 'Any')}, Income up to {scheme.get('income_limit', 'Any')}")
                    
                    scheme_summary = f"{scheme['scheme_name']}. Provides {scheme.get('benifit', 'financial support')}"
                    
                    if st.button(f"🔊 Listen in Malayalam", key=f"tts_scheme_{idx}"):
                        with st.spinner("Generating audio..."):
                            try:
                                audio_path = tts_module.speak_malayalam_from_english(scheme_summary)
                                st.audio(audio_path, format="audio/mp3")
                            except Exception as e:
                                st.error(f"TTS Failed: {e}")
        else:
            st.warning("No matching schemes found for your profile.")

elif page == "Profile Extraction":
    st.header("📄 Smart Profile Extraction (KYC)")
    st.markdown("Upload your Aadhar or Land Record. We will automatically extract the details.")
    
    uploaded_doc = st.file_uploader("Upload Document", type=["jpg", "jpeg", "png"], key="doc_upload")
    
    if uploaded_doc:
        st.image(uploaded_doc, caption="Uploaded Document", width=400)
        if st.button("Extract Information", use_container_width=True, type="primary"):
            img_bytes = uploaded_doc.read()
            with st.spinner("Extracting info using Vision AI..."):
                extracted_data = extract_farmer_profile(img_bytes)
                st.success("Extraction Complete!")
                st.json(extracted_data)

elif page == "Crop Predictor":
    st.header("📈 Predict the Most Profitable Crop")
    st.markdown("Select your details to see data-driven planting recommendations for maximum yield and profit.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        month = st.selectbox("Planting Month", list(range(1, 13)), format_func=lambda x: [
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"][x-1])
    with col2:
        district = st.selectbox("District", [
            "Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha", "Kottayam", "Idukki", 
            "Ernakulam", "Thrissur", "Palakkad", "Malappuram", "Kozhikode", "Wayanad", "Kannur", "Kasaragod"
        ])
    with col3:
        land_area = st.number_input("Land Area (hectares)", min_value=0.1, value=1.0, step=0.1)
    
    if st.button("Predict Optimal Crops", use_container_width=True, type="primary"):
        with st.spinner("Analyzing market data and predicting..."):
            results = predict_top_crops(month, district, land_area)
            if results:
                for idx, res in enumerate(results):
                    st.markdown(f"""
                    <div class="dash-card">
                        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #e2e8f0; padding-bottom:15px; margin-bottom:15px;">
                            <h3 style="margin:0; font-size:1.3rem; color:#065f46;">#{idx+1} {res['crop']}</h3>
                            <div style="background:#dcfce7; color:#166534; padding:5px 12px; border-radius:15px; font-weight:700; font-size:0.9rem;">🎯 {res['match_score']} Match</div>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px;">
                            <div>
                                <div style="font-size:0.85rem; color:#64748b; font-weight:600; text-transform:uppercase;">💰 Est. Revenue</div>
                                <div style="font-size:1.2rem; color:#065f46; font-weight:800;">₹{res['est_revenue']:,.2f}</div>
                            </div>
                            <div>
                                <div style="font-size:0.85rem; color:#64748b; font-weight:600; text-transform:uppercase;">⚖️ Est. Yield</div>
                                <div style="font-size:1.1rem; font-weight:600;">{res['est_yield']:,.0f} Units</div>
                            </div>
                            <div>
                                <div style="font-size:0.85rem; color:#64748b; font-weight:600; text-transform:uppercase;">🏪 Best Market</div>
                                <div style="font-size:1.1rem; font-weight:600;">{res['best_market']}</div>
                            </div>
                            <div>
                                <div style="font-size:0.85rem; color:#64748b; font-weight:600; text-transform:uppercase;">📊 Price Range / Qtl</div>
                                <div style="font-size:1.1rem; font-weight:600;">{res['price_range']}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("No suitable crops found.")

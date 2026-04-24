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
import importlib.util
spec = importlib.util.spec_from_file_location("translate_and_speak", os.path.join(os.path.dirname(__file__), "Malayalam TTS", "translate_and_speak.py"))
tts_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tts_module)

st.set_page_config(page_title="Karsh.Ai", page_icon="✨", layout="wide")

# CSS for Gemini-like aesthetic
st.markdown("""
<style>
    /* Remove padding to use full width */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 1000px;
    }
    
    /* Increase base font size for elderly accessibility */
    html, body, [class*="css"] {
        font-size: 1.15rem !important;
    }
    
    p, span, label, div {
        font-size: 1.15rem !important;
    }

    /* Larger, more readable buttons */
    .stButton>button {
        font-size: 1.2rem !important;
        font-weight: bold !important;
        padding: 15px 30px !important;
        height: auto !important;
    }

    /* Clean chat styling */
    .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        padding: 1.5rem 1rem !important;
    }
    [data-testid="stChatMessageAvatarUser"] {
        background-color: #e8f0fe;
        color: #1f1f1f;
        width: 3rem;
        height: 3rem;
    }
    [data-testid="stChatMessageAvatarAssistant"] {
        background-color: #ffffff;
        width: 3rem;
        height: 3rem;
    }
    
    /* Styling for the predictor cards */
    .card {
        background: white;
        color: #1f1f1f;
        padding: 20px;
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .card h3 {
        margin-top: 0;
        font-size: 1.3rem !important;
        color: #2e7d32;
        font-weight: bold;
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

st.title("✨ Karsh.Ai Tools")

# Use a 4-tab layout
tabs = st.tabs(["💬 AI Chat Assistant", "🏛️ Scheme Recommender", "📄 Profile Extraction", "📈 Crop Predictor"])

# --- TAB 1: AI Chat Assistant ---
with tabs[0]:
    st.subheader("Your Virtual Agronomist")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if "image" in msg and msg["image"]:
                st.image(msg["image"], width=300)
            st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input(
        "Ask Karsh.Ai a question or describe your crop issues...",
        accept_file=True,
        file_type=["jpg", "jpeg", "png"]
    ):
        
        # Read image bytes if present
        img_bytes = None
        if prompt.files:
            img_bytes = prompt.files[0].read()
            
        prompt_text = prompt.text
        
        # Add user message to chat history
        user_msg = {"role": "user", "content": prompt_text}
        if img_bytes:
            user_msg["image"] = img_bytes
        st.session_state.messages.append(user_msg)
        
        # Display immediately
        with st.chat_message("user"):
            if img_bytes:
                st.image(img_bytes, width=300)
            if prompt_text:
                st.markdown(prompt_text)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result_container = st.empty()
                full_response = ""
                
                # Logic: If image, run crop diagnosis. If text only, run general chat.
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

    # Voice TTS Generation Button for latest response
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        if st.button("🔊 Listen in Malayalam", key=f"tts_{len(st.session_state.messages)}"):
            with st.spinner("Translating and generating audio..."):
                try:
                    audio_path = tts_module.speak_malayalam_from_english(st.session_state.messages[-1]["content"][:1000])
                    st.audio(audio_path, format="audio/mp3")
                except Exception as e:
                    st.error(f"TTS Failed: {e}")

# --- TAB 2: Scheme Recommender ---
with tabs[1]:
    st.header("Government Scheme Matcher")
    st.markdown("Find the financial support you are entitled to based on your land and income.")
    
    col1, col2 = st.columns(2)
    with col1:
        income = st.number_input("Monthly Income (₹)", min_value=0, value=10000, step=1000)
    with col2:
        land_size = st.number_input("Land Size (in hectares)", min_value=0.0, value=1.0, step=0.1)
        
    if st.button("Find Schemes", use_container_width=True):
        schemes = recommend_schemes(income, land_size)
        if schemes:
            st.success(f"Found {len(schemes)} eligible scheme(s)!")
            for idx, scheme in enumerate(schemes):
                with st.expander(f"{idx+1}. {scheme['scheme_name']} ({scheme['source']})"):
                    st.markdown(f"**Type:** {scheme['type']}")
                    st.markdown(f"**Benefit:** {scheme.get('benifit', 'N/A')}")
                    st.markdown(f"**Eligibility:** Land up to {scheme.get('Land limit', 'Any')}, Income up to {scheme.get('income_limit', 'Any')}")
                    
                    scheme_summary = f"{scheme['scheme_name']}. Provides {scheme.get('benifit', 'financial support')}"
                    
                    # Add TTS button inside expander
                    if st.button(f"🔊 Listen in Malayalam", key=f"tts_scheme_{idx}"):
                        with st.spinner("Generating audio..."):
                            try:
                                audio_path = tts_module.speak_malayalam_from_english(scheme_summary)
                                st.audio(audio_path, format="audio/mp3")
                            except Exception as e:
                                st.error(f"TTS Failed: {e}")
        else:
            st.warning("No matching schemes found for your profile.")

# --- TAB 3: Profile Extraction ---
with tabs[2]:
    st.header("Smart Profile Extraction (KYC)")
    st.markdown("Upload your Aadhar or Land Record. We will automatically extract the details.")
    
    uploaded_doc = st.file_uploader("Upload Document", type=["jpg", "jpeg", "png"], key="doc_upload")
    
    if uploaded_doc:
        st.image(uploaded_doc, caption="Uploaded Document", width=400)
        if st.button("Extract Information", use_container_width=True):
            img_bytes = uploaded_doc.read()
            with st.spinner("Extracting info using Vision AI..."):
                extracted_data = extract_farmer_profile(img_bytes)
                st.success("Extraction Complete!")
                st.json(extracted_data)

# --- TAB 4: Crop Predictor ---
with tabs[3]:
    st.header("Predict the Most Profitable Crop")
    st.markdown("Select a month and your district to see what you should plant next.")
    
    col1, col2 = st.columns(2)
    with col1:
        month = st.selectbox("Planting Month", list(range(1, 13)), format_func=lambda x: [
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"][x-1])
    with col2:
        district = st.selectbox("District", [
            "Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha", "Kottayam", "Idukki", 
            "Ernakulam", "Thrissur", "Palakkad", "Malappuram", "Kozhikode", "Wayanad", "Kannur", "Kasaragod"
        ])
    
    if st.button("Predict Optimal Crops", use_container_width=True):
        results = predict_top_crops(month, district)
        if results:
            for idx, res in enumerate(results):
                st.markdown(f"""
                <div class="card">
                    <h3>#{idx+1} {res['crop']}</h3>
                    <p style='margin:0; font-size:1.1rem;'>Confidence: <strong>{res['match_score']}</strong></p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No suitable crops found.")

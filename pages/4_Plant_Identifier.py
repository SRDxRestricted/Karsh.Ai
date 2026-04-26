import streamlit as st
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import init_theme, inject_global_css, render_sidebar
from auth import require_auth
from imageProcessing.photoAnalyzer import analyze_crop

st.set_page_config(page_title="Karsh.Ai | Plant Identifier", page_icon="🌱", layout="wide")
init_theme(); inject_global_css(); require_auth(); render_sidebar()

st.markdown("### Plant & Disease Identifier")
st.markdown("Upload a photo of your crop leaf or plant. Our Vision AI will identify diseases and suggest remedies.")

uploaded = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

if uploaded:
    st.image(uploaded, caption="Uploaded Image", width=400)
    if st.button("Analyze", use_container_width=True, type="primary"):
        img_bytes = uploaded.read()
        with st.spinner("Running Vision AI analysis..."):
            result_container = st.empty()
            full_response = ""
            for chunk in analyze_crop(img_bytes):
                full_response += chunk
                result_container.markdown(full_response + "▌")
            result_container.markdown(full_response)

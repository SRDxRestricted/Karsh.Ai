import streamlit as st
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import init_theme, inject_global_css, render_sidebar
from auth import require_auth

st.set_page_config(page_title="Karsh.Ai | Farming Assistant", page_icon="🌾", layout="wide")
init_theme(); inject_global_css(); require_auth(); render_sidebar()

st.markdown("### 🌾 Ask a farming question")
st.markdown("Have a question about your crops, soil, pests, or fertilizers? Type it below and we'll answer in **English and Malayalam**.")

left, right = st.columns([2, 1])
with left:
    st.markdown("**Your question (English or Malayalam)**")
    query = st.text_area("query", placeholder="e.g. My coconut leaves are turning yellow, what should I do?\nഅല്ലെങ്കിൽ മലയാളത്തിൽ ചോദിക്കൂ...", height=140, label_visibility="collapsed")
with right:
    st.markdown("**Common questions**")
    if st.button("🥥 Why are my coconut leaves yellowing?", use_container_width=True):
        st.session_state["va_query"] = "My coconut leaves are turning yellow. What could be the cause and how do I treat it?"
    if st.button("🌳 When should I fertilize rubber?", use_container_width=True):
        st.session_state["va_query"] = "When is the best time to apply fertilizer to rubber trees in Kerala?"
    if st.button("🌾 Best rice variety for Kuttanad?", use_container_width=True):
        st.session_state["va_query"] = "Which rice variety is best suited for Kuttanad's waterlogged conditions?"
    if st.button("🌶️ How to protect pepper from quick wilt?", use_container_width=True):
        st.session_state["va_query"] = "How can I protect my black pepper vines from quick wilt disease in Kerala?"

# Use suggestion if clicked
if "va_query" in st.session_state and st.session_state["va_query"]:
    query = st.session_state.pop("va_query")

if st.button("Get answer", use_container_width=True, type="primary"):
    if query:
        with st.spinner("🤔 Thinking..."):
            try:
                import google.generativeai as genai
                api_key = st.secrets.get("GEMINI_API_KEY")
                if not api_key:
                    st.error("GEMINI_API_KEY not found in Streamlit Secrets.")
                else:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash-lite')

                    # ── Step 1: Get precise English answer ──
                    system_prompt = (
                        "You are a Kerala farming expert. "
                        "Give a precise, practical answer in 100-150 words. "
                        "Use bullet points. Include the cause, solution, and one preventive tip. "
                        "No filler — every sentence must be useful to a farmer."
                    )
                    response = model.generate_content(f"{system_prompt}\n\nFarmer's Question: {query}")
                    english_answer = response.text

                    # ── Step 2: Translate to Malayalam ──
                    with st.spinner("🌐 Translating to Malayalam..."):
                        translate_prompt = (
                            "Translate the following agricultural advice into Malayalam. "
                            "Use simple, everyday Malayalam that a rural farmer can easily understand. "
                            "Keep it short and practical. Keep bullet points. "
                            "Return ONLY the Malayalam translation.\n\n"
                            f"{english_answer}"
                        )
                        ml_response = model.generate_content(translate_prompt)
                        malayalam_answer = ml_response.text

                    # ── Step 3: Display in tabs ──
                    tab_en, tab_ml = st.tabs(["🇬🇧 English", "🇮🇳 മലയാളം"])
                    with tab_en:
                        st.markdown(english_answer)
                    with tab_ml:
                        st.markdown(malayalam_answer)

            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Please type a question first.")

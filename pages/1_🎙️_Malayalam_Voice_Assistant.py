import streamlit as st
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import init_theme, inject_global_css, render_sidebar
from auth import require_auth

st.set_page_config(page_title="Karsh.Ai | Voice Assistant", page_icon="🎙️", layout="wide")
init_theme(); inject_global_css(); require_auth(); render_sidebar()

st.markdown("### 🎙 Karsh.ai Assistant")
st.markdown("Speak to the AI Agronomist in your native language — powered by Google Voice Search and Gemini AI.")

left, right = st.columns([2, 1])
with left:
    st.markdown("**📋 Enter your query**")
    query = st.text_area("query", placeholder="Type your agricultural question here...", height=120, label_visibility="collapsed")
with right:
    st.markdown("**💡 Try These**")
    if st.button("🌴 Coconut yellowing disease?", use_container_width=True):
        st.session_state["va_query"] = "Coconut yellowing disease?"
    if st.button("🌿 When to fertilize rubber?", use_container_width=True):
        st.session_state["va_query"] = "When to fertilize rubber?"
    if st.button("🌾 Best rice variety for Kuttanad?", use_container_width=True):
        st.session_state["va_query"] = "Best rice variety for Kuttanad?"

# Use suggestion if clicked
if "va_query" in st.session_state and st.session_state["va_query"]:
    query = st.session_state.pop("va_query")

st.markdown("**🔧 Or Record Voice**")
audio_input = st.audio_input("Record", label_visibility="collapsed")

if st.button("🚀 Ask Assistant", use_container_width=True, type="primary"):
    if query:
        with st.spinner("Thinking..."):
            try:
                import ollama
                response = ollama.chat(
                    model='gemma4:e2b',
                    messages=[
                        {'role': 'system', 'content': 'You are a helpful Kerala farming assistant. Respond in English.'},
                        {'role': 'user', 'content': query}
                    ]
                )
                st.markdown(response['message']['content'])
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Please enter a query first.")

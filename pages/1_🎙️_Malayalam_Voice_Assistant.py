import streamlit as st
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import init_theme, inject_global_css, render_sidebar
from auth import require_auth

st.set_page_config(page_title="Karsh.Ai | Voice Assistant", page_icon="🎙️", layout="wide")
init_theme(); inject_global_css(); require_auth(); render_sidebar()

st.markdown("### Ask a farming question")
st.markdown("Have a question about your crops, soil, pests, or fertilizers? Type it below or record your voice. We'll do our best to help.")

left, right = st.columns([2, 1])
with left:
    st.markdown("**Your question**")
    query = st.text_area("query", placeholder="e.g. My coconut leaves are turning yellow, what should I do?", height=120, label_visibility="collapsed")
with right:
    st.markdown("**Common questions**")
    if st.button("Why are my coconut leaves yellowing?", use_container_width=True):
        st.session_state["va_query"] = "My coconut leaves are turning yellow. What could be the cause and how do I treat it?"
    if st.button("When should I fertilize rubber?", use_container_width=True):
        st.session_state["va_query"] = "When is the best time to apply fertilizer to rubber trees in Kerala?"
    if st.button("Best rice variety for Kuttanad?", use_container_width=True):
        st.session_state["va_query"] = "Which rice variety is best suited for Kuttanad's waterlogged conditions?"

# Use suggestion if clicked
if "va_query" in st.session_state and st.session_state["va_query"]:
    query = st.session_state.pop("va_query")

st.markdown("**Or record your voice**")
audio_input = st.audio_input("Record", label_visibility="collapsed")

if st.button("Get answer", use_container_width=True, type="primary"):
    if query:
        with st.spinner("Thinking..."):
            try:
                import ollama
                response = ollama.chat(
                    model='gemma4:e2b',
                    messages=[
                        {
                            'role': 'system', 
                            'content': 'You are a helpful Kerala farming assistant. Give very concise, direct, and short answers (max 3-4 sentences).'
                        },
                        {'role': 'user', 'content': query}
                    ],
                    options={
                        'num_predict': 150,  # Limit tokens for faster generation
                        'temperature': 0.7,
                    }
                )
                st.markdown(response['message']['content'])
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Please type a question or record your voice first.")

import google.generativeai as genai
import streamlit as st
import PIL.Image
import io

def analyze_crop(image_bytes):
    """
    Analyzes crop image using Google Gemini 1.5 Flash.
    Requires GEMINI_API_KEY in st.secrets.
    """
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            yield "❌ Error: GEMINI_API_KEY not found in Streamlit Secrets."
            return

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        # Convert bytes to PIL Image
        img = PIL.Image.open(io.BytesIO(image_bytes))
        
        prompt = (
            "You are a Kerala agriculture expert. Identify the crop in this image, "
            "detect any diseases or pests, and provide concise remedies. "
            "Be extremely concise (max 120 words)."
        )
        
        response = model.generate_content([prompt, img], stream=True)

        for chunk in response:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        yield f"\n❌ An error occurred during Gemini analysis: {e}"
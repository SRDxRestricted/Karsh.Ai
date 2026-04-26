import google.generativeai as genai
import streamlit as st
import PIL.Image
import io
import base64
from groq import Groq

def analyze_crop(image_bytes):
    """
    Analyzes crop image using Groq (Primary) or Gemini (Fallback).
    """
    groq_key = st.secrets.get("GROQ_API_KEY")
    gemini_key = st.secrets.get("GEMINI_API_KEY")
    
    prompt = (
        "You are a Kerala agriculture expert. Identify the crop in this image, "
        "detect any diseases or pests, and provide concise remedies. "
        "Be extremely concise (max 120 words)."
    )

    try:
        if groq_key:
            # ── Use Groq Vision (Llama 3.2) ──
            client = Groq(api_key=groq_key)
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                },
                            },
                        ],
                    }
                ],
                model="llama-3.2-11b-vision-preview",
            )
            yield response.choices[0].message.content

        elif gemini_key:
            # ── Use Gemini (Fallback) ──
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            img = PIL.Image.open(io.BytesIO(image_bytes))
            response = model.generate_content([prompt, img], stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        else:
            yield "❌ Error: No API keys (GROQ or GEMINI) found in secrets."

    except Exception as e:
        yield f"\n❌ An error occurred during analysis: {e}"
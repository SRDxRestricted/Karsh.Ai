import google.generativeai as genai
import streamlit as st
import json
import PIL.Image
import io

def extract_farmer_profile(img_bytes, current_data=None):
    if current_data is None:
        current_data = {}

    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY not found in Streamlit Secrets."}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

    # Convert bytes to PIL Image
    img = PIL.Image.open(io.BytesIO(img_bytes))

    system_prompt = f"""
    You are a specialized Kerala Data Assistant.
    Your task: Update the EXISTING_JSON based on the new IMAGE provided.

    EXISTING_JSON:
    {json.dumps(current_data, indent=2)}

    RULES:
    - If the image contains personal info (like Gender, Name, DOB, etc), update the existing 'personal_info' fields. 
    - If the image is a Land Record, check 'land_records'. If the survey number is new, add a new entry.
    - If the land record already exists (matching survey number), update its details (length/breadth).
    - CRITICAL: Always try to extract or estimate 'monthly_income' (as a number) and 'land_size_hectares' (as a number). Add these as top-level keys.
    - Return ONLY the updated JSON. No conversational text.
    """

    try:
        response = model.generate_content(
            [system_prompt, img],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=500,
            )
        )

        updated_json_str = response.text
        try:
            new_data = json.loads(updated_json_str)
            return new_data
        except Exception as e:
            return {"error": str(e), "raw_response": updated_json_str}
    except Exception as e:
        return {"error": str(e)}
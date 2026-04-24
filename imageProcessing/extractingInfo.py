import ollama
import json
import os

def extract_farmer_profile(img_bytes, current_data=None):
    if current_data is None:
        current_data = {}

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

    response = ollama.chat(
        model='gemma4:e2b',
        format='json',
        messages=[{
            'role': 'user',
            'content': system_prompt,
            'images': [img_bytes]
        }]
    )

    updated_json_str = response['message']['content']
    try:
        new_data = json.loads(updated_json_str)
        return new_data
    except Exception as e:
        return {"error": str(e), "raw_response": updated_json_str}
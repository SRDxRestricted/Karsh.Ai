import ollama
import json
import os

def update_farmer_profile(image_path):
    # 1. Load the existing profile
    json_file = 'farmer_profile.json'
    with open(json_file, 'r') as f:
        current_data = json.load(f)

    # 2. Encode the image bytes
    with open(image_path, 'rb') as f:
        img_bytes = f.read()

    # 3. Prompt Gemma 4 to act as a "JSON Sync Agent"
    # We use a f-string to inject the current JSON directly into the prompt
    system_prompt = f"""
    You are a specialized Kerala Data Assistant.
    Your task: Update the EXISTING_JSON based on the new IMAGE provided.

    EXISTING_JSON:
    {json.dumps(current_data, indent=2)}

    RULES:
    - If the image contains personal info (like Gender), update the existing 'personal_info' fields. 
    - If the image is a Land Record, check 'land_records'. If the survey number is new, add a new entry.
    - If the land record already exists (matching survey number), update its details (length/breadth).
    - Return ONLY the updated JSON. No conversational text.
    """

    # 4. Call Ollama with Image + Prompt
    response = ollama.chat(
        model='gemma4:e2b',
        format='json',  # Enforces that Gemma returns valid JSON
        messages=[{
            'role': 'user',
            'content': system_prompt,
            'images': [img_bytes]
        }]
    )

    # 5. Parse and save the results
    updated_json_str = response['message']['content']
    try:
        new_data = json.loads(updated_json_str)
        with open(json_file, 'w') as f:
            json.dump(new_data, f, indent=2)
        print("Profile successfully updated!")
        return new_data
    except Exception as e:
        print(f"Error parsing AI output: {e}")
        return None

# Run the update
update_farmer_profile('aadhar.jpg')
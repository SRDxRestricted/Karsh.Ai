import google.generativeai as genai
import time

API_KEY = "AIzaSyC_wW3QdYEO4dX1zWByje8Fm_O_ZE35HL8"
genai.configure(api_key=API_KEY)

# Try newer models from the available list
test_models = [
    'gemini-2.5-flash-lite',
    'gemini-3-flash-preview',
    'gemini-3.1-flash-lite-preview',
    'gemini-pro-latest',
]

for model_name in test_models:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say hello in one word.")
        print(f"  {model_name}: OK -> {response.text.strip()}")
        break  # Stop on first success
    except Exception as e:
        err_msg = str(e)[:120]
        print(f"  {model_name}: FAILED -> {err_msg}")
    time.sleep(2)

import time
import sys
import io

# Force UTF-8 encoding for standard output to avoid Windows console errors
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from translate_and_speak import speak_malayalam_from_english
from offline_tts import speak_offline_malayalam

class MockOfflineAgriBrain:
    def __init__(self, *args, **kwargs):
        pass
        
    def process_agri_query(self, query):
        # Mocking the AI model response
        return "Apply Bordeaux mixture to the crown and ensure proper drainage."

def main():
    print("=" * 60)
    print("Test Run: Offline Agri Brain + TTS")
    print("=" * 60)
    
    # 1. Initialize the Brain (Mocked)
    print("\n[1/3] Loading OfflineAgriBrain (Mocked due to missing C++ compilers)...")
    start_time = time.time()
    brain = MockOfflineAgriBrain()
    print(f"      Model loaded in {time.time() - start_time:.2f} seconds.")

    # 2. Process a query
    print("\n[2/3] Processing query...")
    query = "തെങ്ങിന് മഞ്ഞളിപ്പ് രോഗം വന്നാൽ എന്ത് ചെയ്യണം?" # What to do if coconut tree has yellowing disease?
    print(f"      Farmer Query: {query}")
    
    start_time = time.time()
    response_english = brain.process_agri_query(query)
    print(f"      AI Response (Raw): {response_english}")
    print(f"      Inference took {time.time() - start_time:.2f} seconds.")

    # 3. Translate to Malayalam and Synthesize (gTTS)
    print("\n[3/3] Translating and synthesizing audio (gTTS)...")
    start_time = time.time()
    audio_file = speak_malayalam_from_english(response_english, output_path="test_response.mp3")
    print(f"      Translated Audio saved to: {audio_file}")
    print(f"      TTS took {time.time() - start_time:.2f} seconds.")
    
    # 4. Synthesize with offline espeak-ng
    print("\n[4/4] Testing Offline espeak-ng TTS...")
    start_time = time.time()
    malayalam_text = "ബോർഡോ മിശ്രിതം തളിക്കുക"
    print(f"      Input (Malayalam): {malayalam_text}")
    audio_file2 = speak_offline_malayalam(malayalam_text, output_file="espeak_output.wav")
    print(f"      Translated Audio saved to: {audio_file2}")
    print(f"      TTS took {time.time() - start_time:.2f} seconds.")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()

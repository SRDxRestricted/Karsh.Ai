import ollama
import sys
import os

def analyze_crop(image_path):
    if not os.path.exists(image_path):
        print(f"❌ Error: Image file '{image_path}' not found.")
        return

    print(f"🔍 Loading image and connecting to Ollama (Gemma 4)...")
    
    try:
        # We use stream=True so you can see the AI 'thinking' in real-time
        response = ollama.chat(
            model='gemma4:e2b',
            messages=[
                {
                    'role': 'system',
                    'content': 'You are a Kerala agriculture expert. Identify crop issues and provide remedies in English'
                },
                {
                    'role': 'user',
                    'content': 'Analyze this crop image for diseases.',
                    'images': [image_path]
                }
            ],
            stream=True 
        )

        print("✅ Analysis started:\n" + "-"*30)
        
        for chunk in response:
            content = chunk['message']['content']
            print(content, end='', flush=True) # This ensures output appears letter-by-letter

        print("\n" + "-"*30 + "\n✅ Analysis Complete.")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    # Replace 'leaf.jpg' with your actual image filename
    analyze_crop('leaf_sample.jpg')
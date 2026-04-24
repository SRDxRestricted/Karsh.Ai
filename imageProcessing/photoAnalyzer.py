import ollama
import sys
import os

def analyze_crop(image_bytes):
    try:
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
                    'images': [image_bytes]
                }
            ],
            stream=True 
        )

        for chunk in response:
            content = chunk['message']['content']
            yield content

    except Exception as e:
        yield f"\n❌ An error occurred: {e}"
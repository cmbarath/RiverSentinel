import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
try:
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    with open('model_list_output.txt', 'w', encoding='utf-8') as f:
        f.write("Listing all models safely:\n")
        for m in genai.list_models():
            safe_name = m.name.encode('ascii', 'ignore').decode('ascii')
            f.write(f"MODEL: {safe_name}\n")
            if 'generateContent' in m.supported_generation_methods:
                 f.write(f"  - Supports generateContent\n")
    print("Done writing to model_list_output.txt")
except Exception as e:
    with open('model_list_output.txt', 'w') as f:
        f.write(f"Error: {e}")
    print(f"Error: {e}")

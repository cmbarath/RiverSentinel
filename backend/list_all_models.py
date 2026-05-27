import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
try:
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    print("Listing all models safely:")
    for m in genai.list_models():
        # Encode to ascii to avoid console errors
        safe_name = m.name.encode('ascii', 'ignore').decode('ascii')
        print(f"MODEL: {safe_name}")
        if 'generateContent' in m.supported_generation_methods:
             print(f"  - Supports generateContent")
except Exception as e:
    print(f"Error: {e}")

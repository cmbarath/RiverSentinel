import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

models = [m.name for m in genai.list_models()]
candidates = [
    'models/gemini-1.5-flash',
    'models/gemini-1.5-flash-latest',
    'models/gemini-1.5-flash-001',
    'models/gemini-1.5-flash-002',
    'models/gemini-pro-vision'
]

found = []
for c in candidates:
    if c in models:
        found.append(c)

print("Found candidates:", found)
if found:
    print("BEST:", found[0])
else:
    print("BEST: None")

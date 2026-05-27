import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv('FIREBASE_DATABASE_URL')
SECRET = os.getenv('FIREBASE_SECRET')

if not DB_URL or not SECRET:
    print("Error: Missing FIREBASE_DATABASE_URL or FIREBASE_SECRET")
    exit(1)

test_data = {"status": "test_write_successful", "timestamp": "now"}
url = f"{DB_URL}/test_write.json?auth={SECRET}"

print(f"Writing to {url}...")
try:
    response = requests.put(url, json=test_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# --- MOCK DATA ---
STATIONS = [
    {"id": "s1", "name": "Dashashwamedh", "status": "SAFE", "ph": 7.4, "turbidity": 4},
    {"id": "s2", "name": "Assi Ghat", "status": "CAUTION", "ph": 7.8, "turbidity": 12},
    {"id": "s3", "name": "Manikarnika", "status": "SAFE", "ph": 7.2, "turbidity": 3},
]

# --- ROUTES ---

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": time.time()})

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    # Simple logic for demo
    user_type = 'authority' if 'authority' in email else 'citizen'
    return jsonify({
        "status": "success",
        "user": {"email": email, "userType": user_type},
        "token": "demo-jwt-token"
    })

@app.route('/api/citizen/safety-status', methods=['GET'])
def get_safety_status():
    return jsonify({"stations": STATIONS})

@app.route('/api/authority/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    return jsonify({
        "activeStations": "11/12",
        "criticalAlerts": 3,
        "pendingReports": 14,
        "systemHealth": "98.5%"
    })

@app.route('/api/ai/analyze-image', methods=['POST'])
def analyze_image():
    # Simulate Gemini Image Analysis
    time.sleep(2)
    return jsonify({
        "isPolluted": "YES",
        "types": ["Plastic", "Sewage"],
        "severity": "HIGH",
        "confidence": 0.94,
        "insight": "AI detected significant plastic debris and suspicious liquid discharge near the steps."
    })

@app.route('/api/ai/chat', methods=['POST'])
def chat():
    data = request.json
    query = data.get('query', '').lower()
    # Simulate ChatGPT/Gemini Chat
    time.sleep(1)
    response = "Based on current data, the river is safe for religious bathing, but I recommend boiling it before drinking."
    if "flood" in query:
        response = "The flood risk is currently LOW. Water levels are well below danger mark."
    
    return jsonify({"response": response})

if __name__ == '__main__':
    app.run(debug=True, port=int(os.getenv('PORT', 5000)))

"""
River Sentinel 2.0 Backend Application
Flask entrypoint and application factory registering modular route blueprints.
"""

import os
import sys
import time
from dotenv import load_dotenv

# Ensure backend root is in Python sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load environment variables
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

from flask import Flask, jsonify
from flask_cors import CORS

from routes.sensors import sensors_bp
from routes.predictions import predictions_bp
from routes.ai import ai_bp
from routes.authority import authority_bp

START_TIME = time.time()


def create_app():
    """Application factory for River Sentinel Flask backend."""
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Register modular route blueprints
    app.register_blueprint(sensors_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(authority_bp)

    @app.route('/')
    def index():
        return jsonify({
            "message": "RiverSentinel Backend API",
            "version": "2.0.0",
            "status": "operational",
            "database": "Supabase PostgreSQL",
            "endpoints": {
                "sensors": "/api/sensors/latest",
                "telemetry_ingest": "/api/telemetry/simulate",
                "flood_prediction": "/api/flood/predict",
                "water_quality": "/api/water-quality/predict",
                "weather": "/api/weather",
                "chatbot": "/api/ai/chat",
                "image_analysis": "/api/ai/analyze-image",
                "reports": "/api/authority/reports",
                "report_summary": "/api/authority/report-summary",
                "health": "/api/health"
            }
        })

    @app.route('/api/health')
    def health_check():
        uptime = round(time.time() - START_TIME, 2)
        return jsonify({
            'status': 'healthy',
            'uptime_seconds': uptime,
            'database': 'Supabase PostgreSQL',
            'services': {
                'groq_ai': bool(os.getenv('GROQ_API_KEY')),
                'supabase': bool(os.getenv('SUPABASE_URL'))
            }
        })

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 River Sentinel 2.0 API Server running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

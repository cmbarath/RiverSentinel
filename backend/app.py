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
from routes.stations_v1 import stations_v1_bp
from routes.alerts_v1 import alerts_v1_bp
from routes.health import health_bp
from services.logging_service import init_logging_middleware

START_TIME = time.time()


def create_app():
    """Application factory for River Sentinel Flask backend."""
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Initialize structured logging middleware & global sanitized error handlers
    init_logging_middleware(app)

    # Register modular route blueprints
    app.register_blueprint(sensors_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(authority_bp)
    app.register_blueprint(stations_v1_bp)
    app.register_blueprint(alerts_v1_bp)
    app.register_blueprint(health_bp)

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
                "telemetry_ingest_v1": "/api/v1/telemetry/ingest",
                "flood_prediction": "/api/flood/predict",
                "water_quality": "/api/water-quality/predict",
                "weather": "/api/weather",
                "chatbot": "/api/ai/chat",
                "image_analysis": "/api/ai/analyze-image",
                "reports": "/api/authority/reports",
                "report_summary": "/api/authority/report-summary",
                "alerts_v1": "/api/v1/alerts",
                "alert_rules_v1": "/api/v1/alerts/rules",
                "notifications_v1": "/api/v1/notifications",
                "notification_prefs_v1": "/api/v1/notifications/preferences",
                "health": "/api/health",
                "health_live": "/api/health/live",
                "health_ready": "/api/health/ready",
                "health_status": "/api/health/status"
            }
        })

    @app.route('/api/health')
    def health_check():
        from routes.health import readiness_check
        return readiness_check()

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 River Sentinel 2.0 API Server running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

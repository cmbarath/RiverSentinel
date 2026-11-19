"""
River Sentinel 2.0 - Structured Logging & Error Management Service (Phase 7)
Provides:
- Request correlation ID & request ID tracking across all Flask routes.
- High-resolution response duration instrumentation.
- Structured JSON logging to console and rotating log files.
- Strict data sanitization: redaction of tokens, secrets, credentials, base64 images.
- Standardized, safe error classification and response masking for user safety.
"""

import os
import sys
import time
import uuid
import json
import logging
from logging.handlers import RotatingFileHandler
from flask import request, g, jsonify, Response

# Sensitive key patterns to redact in any logged payload
SENSITIVE_PATTERNS = {
    'token', 'password', 'secret', 'key', 'auth', 'jwt',
    'device_token', 'authorization', 'bearer', 'cookie', 'evidence'
}

# Ensure logs directory exists
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(_backend_dir, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOGS_DIR, 'app.log')


class JsonStructuredFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        # Add correlation context if available
        if hasattr(record, 'correlation_id'):
            log_obj['correlation_id'] = record.correlation_id
        if hasattr(record, 'request_id'):
            log_obj['request_id'] = record.request_id
        if hasattr(record, 'extra_data') and isinstance(record.extra_data, dict):
            log_obj.update(record.extra_data)

        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def sanitize_dict(d: dict, max_depth: int = 3) -> dict:
    """Recursively sanitize a dictionary to prevent logging sensitive tokens or giant blobs."""
    if max_depth <= 0 or not isinstance(d, dict):
        return {}

    sanitized = {}
    for k, v in d.items():
        k_lower = str(k).lower()
        if any(pat in k_lower for pat in SENSITIVE_PATTERNS):
            sanitized[k] = '[REDACTED]'
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict(v, max_depth - 1)
        elif isinstance(v, (list, tuple)):
            if len(v) > 20:
                sanitized[k] = f'[Array with {len(v)} elements]'
            else:
                sanitized[k] = [sanitize_dict(item, max_depth - 1) if isinstance(item, dict) else item for item in v]
        elif isinstance(v, str) and len(v) > 500:
            sanitized[k] = v[:64] + '... [TRUNCATED]'
        else:
            sanitized[k] = v
    return sanitized


def setup_logger(name: str = 'river_sentinel') -> logging.Logger:
    """Initialize structured application logger with stream and rotating file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers on reload
    if logger.handlers:
        return logger

    # Console Stream Handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JsonStructuredFormatter())
    logger.addHandler(stream_handler)

    # Rotating File Handler (10MB per file, up to 5 backups)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(JsonStructuredFormatter())
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"[WARN] Could not initialize file logger: {e}", file=sys.stderr)

    return logger


logger = setup_logger()


def init_logging_middleware(app):
    """Register structured logging middleware and safe error handlers on the Flask app."""

    @app.before_request
    def before_request_logger():
        g.start_time = time.time()
        # Extract or generate correlation ID and request ID
        g.correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())
        g.request_id = request.headers.get('X-Request-ID') or f"req-{uuid.uuid4().hex[:12]}"

    @app.after_request
    def after_request_logger(response: Response) -> Response:
        # Attach correlation and request IDs to response headers
        corr_id = getattr(g, 'correlation_id', str(uuid.uuid4()))
        req_id = getattr(g, 'request_id', str(uuid.uuid4()))
        response.headers['X-Correlation-ID'] = corr_id
        response.headers['X-Request-ID'] = req_id

        # Skip high-frequency static/options logging to prevent clutter
        if request.method == 'OPTIONS':
            return response

        duration_ms = round((time.time() - getattr(g, 'start_time', time.time())) * 1000, 2)
        status_code = response.status_code

        # Log entry
        log_payload = {
            'route': request.path,
            'method': request.method,
            'status_code': status_code,
            'duration_ms': duration_ms,
            'client_ip': request.remote_addr,
        }

        # Safely capture authenticated user or device if available
        if hasattr(request, 'user') and request.user and 'id' in request.user:
            log_payload['user_id'] = request.user['id']
        if request.headers.get('X-Device-Code'):
            log_payload['device_code'] = request.headers.get('X-Device-Code')

        level = logging.INFO
        if status_code >= 500:
            level = logging.ERROR
            log_payload['error_category'] = 'server_error'
        elif status_code >= 400:
            level = logging.WARNING
            log_payload['error_category'] = 'client_error'

        record = logger.makeRecord(
            logger.name, level, '', 0,
            f"{request.method} {request.path} {status_code} ({duration_ms}ms)",
            (), None
        )
        record.correlation_id = corr_id
        record.request_id = req_id
        record.extra_data = log_payload
        logger.handle(record)

        return response

    # ------------------------------------------------------------------------
    # Global Sanitized Error Handlers
    # ------------------------------------------------------------------------

    @app.errorhandler(400)
    def handle_bad_request(e):
        corr_id = getattr(g, 'correlation_id', str(uuid.uuid4()))
        msg = getattr(e, 'description', 'Invalid request payload or parameters.')
        return jsonify({
            'status': 'error',
            'error': 'Bad Request',
            'error_code': 'BAD_REQUEST',
            'message': str(msg),
            'correlation_id': corr_id
        }), 400

    @app.errorhandler(401)
    def handle_unauthorized(e):
        corr_id = getattr(g, 'correlation_id', str(uuid.uuid4()))
        return jsonify({
            'status': 'error',
            'error': 'Unauthorized',
            'error_code': 'UNAUTHORIZED',
            'message': 'Authentication required or invalid credentials.',
            'correlation_id': corr_id
        }), 401

    @app.errorhandler(403)
    def handle_forbidden(e):
        corr_id = getattr(g, 'correlation_id', str(uuid.uuid4()))
        return jsonify({
            'status': 'error',
            'error': 'Forbidden',
            'error_code': 'FORBIDDEN',
            'message': 'You do not have permission to perform this action.',
            'correlation_id': corr_id
        }), 403

    @app.errorhandler(404)
    def handle_not_found(e):
        corr_id = getattr(g, 'correlation_id', str(uuid.uuid4()))
        return jsonify({
            'status': 'error',
            'error': 'Not Found',
            'error_code': 'RESOURCE_NOT_FOUND',
            'message': 'The requested resource could not be found.',
            'correlation_id': corr_id
        }), 404

    @app.errorhandler(429)
    def handle_rate_limit(e):
        corr_id = getattr(g, 'correlation_id', str(uuid.uuid4()))
        return jsonify({
            'status': 'error',
            'error': 'Too Many Requests',
            'error_code': 'RATE_LIMITED',
            'message': 'Rate limit exceeded. Please wait before repeating the request.',
            'correlation_id': corr_id
        }), 429

    @app.errorhandler(Exception)
    def handle_unhandled_exception(e):
        corr_id = getattr(g, 'correlation_id', str(uuid.uuid4()))
        req_id = getattr(g, 'request_id', str(uuid.uuid4()))

        # Internal detailed log with traceback for operators
        record = logger.makeRecord(
            logger.name, logging.ERROR, '', 0,
            f"Unhandled exception on {request.method} {request.path}: {str(e)}",
            (), sys.exc_info()
        )
        record.correlation_id = corr_id
        record.request_id = req_id
        record.extra_data = {
            'route': request.path,
            'method': request.method,
            'error_category': 'unhandled_exception'
        }
        logger.handle(record)

        # Sanitized user-facing response - NEVER leak stack trace or internal configuration
        return jsonify({
            'status': 'error',
            'error': 'Internal Server Error',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'message': 'An unexpected error occurred. Please quote the correlation ID for assistance.',
            'correlation_id': corr_id
        }), 500

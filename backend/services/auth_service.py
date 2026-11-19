"""
Authentication & Role-Based Authorization Service for River Sentinel 2.0
Validates Supabase Auth JWTs and enforces RBAC for citizen, field_officer, and authority_admin.
"""

import os
import time
import requests
from functools import wraps
from typing import Dict, Any, Optional, Tuple
from flask import request, jsonify

# Load Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', '').rstrip('/')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_KEY', '')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')

# Simple in-memory token cache to prevent redundant HTTP roundtrips during rapid polling
# Cache format: { token_str: { 'user': dict, 'profile': dict, 'expires_at': float } }
_AUTH_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 60.0


def _clean_cache():
    """Remove expired token cache entries."""
    now = time.time()
    expired_keys = [k for k, v in _AUTH_CACHE.items() if v['expires_at'] < now]
    for k in expired_keys:
        _AUTH_CACHE.pop(k, None)


def verify_supabase_jwt(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify Supabase JWT by querying Supabase Auth endpoint /auth/v1/user.
    This guarantees 100% standard cryptographic & session validity without secret mismatch issues.
    """
    if not token or not SUPABASE_URL:
        return None

    _clean_cache()
    cached = _AUTH_CACHE.get(token)
    if cached and cached['expires_at'] > time.time():
        return cached['user']

    url = f"{SUPABASE_URL}/auth/v1/user"
    headers = {
        'Authorization': f'Bearer {token}',
        'apikey': SUPABASE_ANON_KEY
    }

    try:
        res = requests.get(url, headers=headers, timeout=3.5)
        if res.status_code == 200:
            user_data = res.json()
            # Store in cache
            _AUTH_CACHE[token] = {
                'user': user_data,
                'profile': None,
                'expires_at': time.time() + CACHE_TTL_SECONDS
            }
            return user_data
    except Exception as e:
        print(f"[AUTH ERROR] Supabase token verification failed: {e}")

    return None


def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the role and profile from public.profiles using service role."""
    from services.supabase_service import supabase_get

    if not user_id:
        return None

    try:
        profiles = supabase_get('profiles', filters={'id': f'eq.{user_id}'})
        if profiles and isinstance(profiles, list) and len(profiles) > 0:
            return profiles[0]
    except Exception as e:
        print(f"[AUTH ERROR] Error fetching profile for user {user_id}: {e}")

    return None


def extract_bearer_token() -> Optional[str]:
    """Extract Bearer token from HTTP Authorization header."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:].strip()
    return None


def require_auth(f):
    """Decorator: Requires a valid Supabase authenticated session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = extract_bearer_token()
        if not token:
            return jsonify({'error': 'Unauthorized', 'message': 'Missing Authorization Bearer token'}), 401

        user = verify_supabase_jwt(token)
        if not user:
            return jsonify({'error': 'Unauthorized', 'message': 'Invalid or expired authentication session'}), 401

        # Retrieve profile & role
        cached = _AUTH_CACHE.get(token)
        profile = cached.get('profile') if cached else None
        if not profile:
            profile = get_user_profile(user['id'])
            if cached and profile:
                cached['profile'] = profile

        # Default role fallback is 'citizen' if profile not yet populated
        role = profile.get('role', 'citizen') if profile else 'citizen'

        request.user = user
        request.user_profile = profile
        request.user_role = role

        return f(*args, **kwargs)
    return decorated_function


def require_role(*allowed_roles):
    """
    Decorator: Requires user to be authenticated AND hold one of the specified roles.
    Example: @require_role('authority_admin') or @require_role('authority_admin', 'field_officer')
    """
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user_role = getattr(request, 'user_role', 'citizen')
            if user_role not in allowed_roles:
                return jsonify({
                    'error': 'Forbidden',
                    'message': f'Access denied. Required role in {allowed_roles}, your role is {user_role}.'
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def optional_auth(f):
    """Decorator: Checks auth token if provided, but allows unauthenticated access if omitted."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = extract_bearer_token()
        request.user = None
        request.user_profile = None
        request.user_role = 'anonymous'

        if token:
            user = verify_supabase_jwt(token)
            if user:
                profile = get_user_profile(user['id'])
                request.user = user
                request.user_profile = profile
                request.user_role = profile.get('role', 'citizen') if profile else 'citizen'

        return f(*args, **kwargs)
    return decorated_function

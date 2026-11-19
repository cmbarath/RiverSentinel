"""
Device Authentication & Verification Service for River Sentinel 2.0
Handles constant-time cryptographic verification of ESP32 edge device tokens,
lifecycle validation, and station binding derivation.
"""

import hashlib
import hmac
import secrets
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from services.supabase_service import supabase_get, supabase_update

# Standardized Pre-Shared Key (PSK) Token Architecture
# 24 cryptographically random bytes = 48 hexadecimal characters = 192 bits of entropy
TOKEN_PREFIX = "rs_dev_"
TOKEN_ENTROPY_BYTES = 24
TOKEN_HEX_CHARS = 48
TOKEN_TOTAL_LEN = len(TOKEN_PREFIX) + TOKEN_HEX_CHARS  # 55 chars

# Constant dummy hash used to neutralize timing attacks when device_code is not found
_DUMMY_HASH = hashlib.sha256(b"river_sentinel_dummy_hash_timing_pad").hexdigest()


def generate_device_token() -> str:
    """
    Generate high-entropy pre-shared device token (192-bit entropy).
    Format: rs_dev_<48 hex chars> (55 characters total).
    """
    return f"{TOKEN_PREFIX}{secrets.token_hex(TOKEN_ENTROPY_BYTES)}"


def is_valid_token_format(token: str) -> bool:
    """
    Validate that token strictly adheres to the 192-bit rs_dev_ specification.
    """
    if not token or not isinstance(token, str):
        return False
    clean = token.strip()
    if len(clean) != TOKEN_TOTAL_LEN or not clean.startswith(TOKEN_PREFIX):
        return False
    hex_part = clean[len(TOKEN_PREFIX):]
    return all(c in "0123456789abcdefABCDEF" for c in hex_part)


def mask_device_token(token: str) -> str:
    """
    Mask token for safe diagnostic display without exposing credential entropy.
    """
    if not token or not isinstance(token, str):
        return "[UNSET]"
    clean = token.strip()
    if clean.startswith(TOKEN_PREFIX) and len(clean) == TOKEN_TOTAL_LEN:
        return f"{TOKEN_PREFIX}{clean[7:11]}...****************...{clean[-4:]}"
    return f"{TOKEN_PREFIX}************************************************"


def hash_device_token(token: str) -> str:
    """Compute SHA-256 digest of device token."""
    return hashlib.sha256(token.strip().encode('utf-8')).hexdigest()


def verify_device_credentials(device_code: str, raw_token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Authenticate an incoming IoT device request.
    
    Returns:
        (is_valid: bool, device_record: Optional[dict], error_message: Optional[str])
    """
    if not device_code or not raw_token:
        # Constant-time dummy check to prevent timing attack enumeration
        hmac.compare_digest(hash_device_token(raw_token or ""), _DUMMY_HASH)
        return False, None, "Invalid or missing device credentials"

    # Enforce strict format check while keeping constant-time execution
    format_valid = is_valid_token_format(raw_token)

    # Fetch device record from Supabase
    devices = supabase_get('devices', filters={'device_code': f'eq.{device_code.strip()}'}, limit=1)

    if not devices or not isinstance(devices, list) or len(devices) == 0:
        # Constant-time dummy check to prevent timing attack enumeration of device codes
        hmac.compare_digest(hash_device_token(raw_token), _DUMMY_HASH)
        return False, None, "Authentication failed"

    device = devices[0]
    stored_hash = device.get('credential_hash', '')
    incoming_hash = hash_device_token(raw_token)

    # Constant-time comparison
    hash_matches = hmac.compare_digest(incoming_hash, stored_hash)

    if not format_valid or not hash_matches:
        return False, None, "Authentication failed"

    # Enforce device lifecycle status
    status = device.get('status', 'offline')
    if status == 'revoked':
        return False, None, "Device credentials have been revoked by authority"
    if status in ('inactive', 'maintenance'):
        return False, None, f"Device is currently in {status} state"
    if status in ('registered', 'awaiting_installation'):
        return False, None, "Device registration is pending physical deployment"

    # Ensure device is bound to a registered station
    station_id = device.get('station_id')
    if not station_id:
        return False, None, "Device is not assigned to any monitoring station"

    return True, device, None


def touch_device_activity(device_id: str, battery_level: Optional[float] = None, firmware_ver: Optional[str] = None):
    """Update device last_seen_at and battery status on successful authenticated telemetry."""
    if not device_id:
        return

    update_payload: Dict[str, Any] = {
        'status': 'online',
        'last_seen_at': datetime.now(timezone.utc).isoformat()
    }
    if battery_level is not None:
        try:
            update_payload['battery_level_pct'] = round(float(battery_level), 2)
        except (ValueError, TypeError):
            pass
    if firmware_ver:
        update_payload['firmware_version'] = str(firmware_ver).strip()[:20]

    supabase_update('devices', f"id=eq.{device_id}", update_payload)

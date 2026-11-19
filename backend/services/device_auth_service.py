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

# Constant dummy hash used to neutralize timing attacks when device_code is not found
_DUMMY_HASH = hashlib.sha256(b"river_sentinel_dummy_hash_timing_pad").hexdigest()


def generate_device_token() -> str:
    """Generate high-entropy pre-shared device token (192-bit entropy)."""
    return f"rs_dev_{secrets.token_hex(24)}"


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
        return False, None, "Invalid or missing device credentials"

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
    if not hmac.compare_digest(incoming_hash, stored_hash):
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

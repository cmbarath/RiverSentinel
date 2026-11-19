"""
River Sentinel 2.0 - Provider-Independent Telephony & SMS Gateway Service (Phase 5)
Provides:
- Base abstract SMS provider interface.
- Mock provider for deterministic unit & integration tests.
- Configurable REST HTTP provider adapter for external gateways (Twilio, CDAC, MSG91).
- Canonical alert message templating with GSM 160-char compliance and non-emergency disclaimers.
"""

import os
import re
import uuid
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional

SMS_ENABLED = os.getenv('SMS_ENABLED', 'false').lower() in ('true', '1', 'yes')
SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'mock').lower().strip()
SMS_API_KEY = os.getenv('SMS_API_KEY', '')
SMS_SENDER_ID = os.getenv('SMS_SENDER_ID', 'RIVSEN')
SMS_BASE_URL = os.getenv('SMS_BASE_URL', '')


class BaseSMSProvider(ABC):
    """Abstract SMS Gateway Provider Interface."""

    @abstractmethod
    def send_message(self, recipient_phone: str, message: str) -> Dict[str, Any]:
        """Dispatch an SMS message to a validated recipient phone number."""
        pass

    @abstractmethod
    def get_delivery_status(self, provider_message_id: str) -> Dict[str, Any]:
        """Check provider delivery receipt status."""
        pass

    @abstractmethod
    def validate_configuration(self) -> bool:
        """Verify whether required provider credentials and endpoints are configured."""
        pass


class MockSMSProvider(BaseSMSProvider):
    """
    Mock provider for automated testing and offline development.
    Never makes network calls and never incurs telephony billing.
    """
    def __init__(self):
        self.dispatched_messages = []

    def send_message(self, recipient_phone: str, message: str) -> Dict[str, Any]:
        msg_id = f"mock_sms_{uuid.uuid4().hex[:16]}"
        record = {
            'provider_message_id': msg_id,
            'recipient_phone': recipient_phone,
            'message': message,
            'status': 'accepted',
            'dispatched_at': datetime.now(timezone.utc).isoformat()
        }
        self.dispatched_messages.append(record)
        return {
            'success': True,
            'provider_message_id': msg_id,
            'status': 'accepted',
            'error_code': None,
            'error_message': None
        }

    def get_delivery_status(self, provider_message_id: str) -> Dict[str, Any]:
        return {
            'provider_message_id': provider_message_id,
            'status': 'delivered',
            'delivered_at': datetime.now(timezone.utc).isoformat()
        }

    def validate_configuration(self) -> bool:
        return True


class HTTPGatewaySMSProvider(BaseSMSProvider):
    """
    Generic HTTP REST Gateway Provider adapter (e.g. CDAC / Twilio / MSG91).
    Activated only when SMS_ENABLED=true and credentials are provided.
    """
    def __init__(self, api_key: str, sender_id: str, base_url: str):
        self.api_key = api_key
        self.sender_id = sender_id
        self.base_url = base_url.rstrip('/')

    def validate_configuration(self) -> bool:
        return bool(self.api_key and self.base_url)

    def send_message(self, recipient_phone: str, message: str) -> Dict[str, Any]:
        if not self.validate_configuration():
            return {
                'success': False,
                'provider_message_id': None,
                'status': 'failed',
                'error_code': 'UNCONFIGURED_GATEWAY',
                'error_message': 'HTTP SMS Gateway credentials or base URL missing.'
            }

        # Simulated REST post structure - ready for production URL hook
        import requests
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                'sender': self.sender_id,
                'recipient': recipient_phone,
                'text': message
            }
            res = requests.post(f"{self.base_url}/messages", json=payload, headers=headers, timeout=5.0)
            if res.status_code in (200, 201, 202):
                data = res.json() if res.text else {}
                return {
                    'success': True,
                    'provider_message_id': data.get('id') or data.get('message_id') or str(uuid.uuid4()),
                    'status': 'accepted',
                    'error_code': None,
                    'error_message': None
                }
            return {
                'success': False,
                'provider_message_id': None,
                'status': 'failed',
                'error_code': f"HTTP_{res.status_code}",
                'error_message': res.text[:200]
            }
        except Exception as e:
            return {
                'success': False,
                'provider_message_id': None,
                'status': 'failed',
                'error_code': 'NETWORK_ERROR',
                'error_message': str(e)
            }

    def get_delivery_status(self, provider_message_id: str) -> Dict[str, Any]:
        return {'provider_message_id': provider_message_id, 'status': 'unknown'}


# Factory instantiation
def get_sms_provider() -> BaseSMSProvider:
    if SMS_PROVIDER == 'http' and SMS_ENABLED:
        return HTTPGatewaySMSProvider(SMS_API_KEY, SMS_SENDER_ID, SMS_BASE_URL)
    return MockSMSProvider()


# ----------------------------------------------------------------------------
# Message Formatting & Templating
# ----------------------------------------------------------------------------

def format_sms_message(category: str, severity: str, station_name: str,
                       param: str, value: Any, unit: str, timestamp_str: str) -> str:
    """
    Format concise alert messages conforming to standard GSM 7-bit lengths (<= 160 chars).
    Crucially includes disclaimer directing citizens to official authorities (CWC / UPPCB).
    """
    ts = timestamp_str[:16].replace('T', ' ') if 'T' in timestamp_str else timestamp_str

    if category == 'FLOOD':
        stage_name = "DANGER" if severity == 'CRITICAL' else "WARNING"
        msg = f"[RiverSentinel] Ganga {station_name}: Water stage reached CWC {stage_name} level ({value}{unit}). Consult Varanasi Disaster Control (1077). {ts}"
    elif category == 'WATER_QUALITY':
        msg = f"[RiverSentinel] Ganga {station_name}: {param} ({value}{unit}) deviates from CPCB Class B standards. Field team notified. {ts}"
    elif category == 'DEVICE_HEALTH':
        msg = f"[RiverSentinel Ops] Hardware node {station_name} offline/stale. Technician check required. {ts}"
    elif category == 'POLLUTION_REPORT':
        msg = f"[RiverSentinel Ops] Citizen report #{value} logged at {station_name}. UPPCB review pending. {ts}"
    else:
        msg = f"[RiverSentinel Alert] {severity}: {station_name} - {param}: {value}{unit}. {ts}"

    return msg[:160]  # Hard truncate to 1 SMS segment to guarantee no multi-part overflow


def validate_indian_phone(phone: str) -> Optional[str]:
    """
    Validate and format E.164 phone numbers for Indian routing (+91XXXXXXXXXX).
    Strictly enforces Indian National Numbering Plan (DoT/TRAI): 10-digit mobile subscriber
    numbers must begin with 6, 7, 8, or 9.
    """
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    if cleaned.startswith('+91') and len(cleaned) == 13:
        if cleaned[3] in ('6', '7', '8', '9'):
            return cleaned
        return None
    elif cleaned.startswith('91') and len(cleaned) == 12:
        if cleaned[2] in ('6', '7', '8', '9'):
            return f"+{cleaned}"
        return None
    elif len(cleaned) == 11 and cleaned.startswith('0') and cleaned[1] in ('6', '7', '8', '9'):
        return f"+91{cleaned[1:]}"
    elif len(cleaned) == 10 and cleaned[0] in ('6', '7', '8', '9'):
        return f"+91{cleaned}"
    return None

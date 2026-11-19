"""
River Sentinel 2.0 - Provider-Independent Telephony & SMS Gateway Service (Phase 5.1 Hardened)
Provides:
- Base abstract SMS provider interface.
- Mock provider for deterministic unit & integration tests.
- Configurable REST HTTP provider adapter for external gateways (CDAC, Twilio, MSG91).
- Canonical alert message templating with encoding-aware segment calculations (GSM 7-bit & UCS-2).
- Strict DoT / TRAI National Numbering Plan E.164 verification (+91).
- Carrier accepted vs terminal delivered lifecycle tracking.

REGULATORY NOTICE (TRAI / DLT COMPLIANCE):
Under the Telecom Commercial Communications Customer Preference Regulations (TCCCPR, 2018):
1. Principal Entity (PE) Registration: All enterprise / government senders must hold a verified PE ID with Indian access providers.
2. Registered Header: All promotional/transactional SMS must use an approved 6-character alphabetic Header (e.g. RIVSEN).
3. Registered Content Template: Every message sent must match an approved DLT Content Template containing fixed text and {#var#} variables.
4. Recipient Consent & Preference: Explicit consent timestamping and DND preference verification are statutory prerequisites.
5. Delivery Receipts: HTTP transmission acceptance does not guarantee terminal delivery; asynchronous DLR webhooks are required.
"""

import os
import re
import math
import uuid
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

SMS_ENABLED = os.getenv('SMS_ENABLED', 'false').lower() in ('true', '1', 'yes')
SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'mock').lower().strip()
SMS_API_KEY = os.getenv('SMS_API_KEY', '')
SMS_SENDER_ID = os.getenv('SMS_SENDER_ID', 'RIVSEN')
SMS_BASE_URL = os.getenv('SMS_BASE_URL', '')
SMS_WEBHOOK_SECRET = os.getenv('SMS_WEBHOOK_SECRET', 'rs_sec_dlr_webhook_token_99')

# ----------------------------------------------------------------------------
# GSM 7-bit Character Set Definitions (3GPP TS 23.038 / ITU-T)
# ----------------------------------------------------------------------------
GSM7_BASIC = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿"
    "abcdefghijklmnopqrstuvwxyzäöñüà"
)

# Extension table characters - each requires 1 escape byte (counts as 2 GSM chars)
GSM7_EXTENDED = set("^{}\\[~]|€\f")


def calculate_sms_segments(text: str) -> Dict[str, Any]:
    """
    Calculate encoding and segment counts for an SMS message.
    Distinguishes:
      - GSM 7-bit default alphabet (160 chars single, 153 chars/segment multipart)
      - GSM extension-table characters (count as 2 characters)
      - Unicode / UCS-2 messages (70 chars single, 67 chars/segment multipart)
    """
    if not text:
        return {
            'encoding': 'gsm7',
            'raw_character_count': 0,
            'billable_character_count': 0,
            'segment_count': 0,
            'max_single_part_chars': 160,
            'chars_per_multipart_segment': 153,
            'chars_remaining_in_segment': 160,
            'is_multipart': False,
            'non_gsm_characters': []
        }

    # Check for any non-GSM7 characters
    non_gsm = [c for c in text if c not in GSM7_BASIC and c not in GSM7_EXTENDED]

    if non_gsm:
        # UCS-2 / Unicode Encoding (e.g. Hindi Devanagari, emojis, special symbols)
        encoding = 'ucs2'
        raw_len = len(text)
        billable_len = raw_len
        single_max = 70
        multi_max = 67

        if raw_len <= single_max:
            segments = 1
            remaining = single_max - raw_len
        else:
            segments = math.ceil(raw_len / multi_max)
            remaining = (segments * multi_max) - raw_len

        return {
            'encoding': encoding,
            'raw_character_count': raw_len,
            'character_count': raw_len,
            'billable_character_count': billable_len,
            'segment_count': segments,
            'segments': segments,
            'max_single_part_chars': single_max,
            'chars_per_multipart_segment': multi_max,
            'chars_remaining_in_segment': remaining,
            'remaining_in_segment': remaining,
            'is_multipart': segments > 1,
            'non_gsm_characters': sorted(list(set(non_gsm)))
        }

    # Standard GSM 7-bit Encoding
    encoding = 'gsm7'
    raw_len = len(text)
    # Calculate billable characters: standard chars = 1, extension chars = 2
    billable_len = sum(2 if c in GSM7_EXTENDED else 1 for c in text)
    single_max = 160
    multi_max = 153

    if billable_len <= single_max:
        segments = 1
        remaining = single_max - billable_len
    else:
        segments = math.ceil(billable_len / multi_max)
        remaining = (segments * multi_max) - billable_len

    return {
        'encoding': encoding,
        'raw_character_count': raw_len,
        'character_count': raw_len,
        'billable_character_count': billable_len,
        'segment_count': segments,
        'segments': segments,
        'max_single_part_chars': single_max,
        'chars_per_multipart_segment': multi_max,
        'chars_remaining_in_segment': remaining,
        'remaining_in_segment': remaining,
        'is_multipart': segments > 1,
        'non_gsm_characters': []
    }


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
        self.base_url = base_url.rstrip('/') if base_url else ''

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
                    'status': 'accepted',  # Accepted by carrier, NOT terminal delivered yet!
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
    Format concise English alert message conforming to GSM 7-bit single-segment limits (<= 160 chars).
    Crucially includes emergency helpline disclaimer (1077).
    """
    ts = timestamp_str[:16].replace('T', ' ') if 'T' in timestamp_str else timestamp_str

    if category == 'FLOOD':
        stage_name = "DANGER" if severity == 'CRITICAL' else "WARNING"
        msg = f"[RiverSentinel] Ganga {station_name}: Water reached CWC {stage_name} level ({value}{unit}). Varanasi Control: 1077. {ts}"
    elif category == 'WATER_QUALITY':
        msg = f"[RiverSentinel] Ganga {station_name}: {param} ({value}{unit}) deviates from statutory CPCB Class B standard. Field team notified. {ts}"
    elif category == 'DEVICE_HEALTH':
        msg = f"[RiverSentinel Ops] Hardware node {station_name} offline. Technician check required. {ts}"
    elif category == 'POLLUTION_REPORT':
        msg = f"[RiverSentinel Ops] Citizen report #{value} logged at {station_name}. UPPCB review pending. {ts}"
    else:
        msg = f"[RiverSentinel Alert] {severity}: {station_name} - {param}: {value}{unit}. {ts}"

    # Ensure single segment (<= 160 GSM chars)
    seg_info = calculate_sms_segments(msg)
    if seg_info['billable_character_count'] > 160:
        msg = msg[:157] + "..."

    return msg


def format_sms_message_hindi(category: str, severity: str, station_name: str,
                             param: str, value: Any, unit: str, timestamp_str: Optional[str] = None) -> str:
    """
    Format concise Hindi Unicode alert message conforming to UCS-2 single-segment limits (<= 70 chars).
    Uses Devanagari script.
    """
    ts_val = timestamp_str or datetime.now().strftime('%Y-%m-%d')
    ts = ts_val[:10] if len(ts_val) >= 10 else ts_val

    if category == 'FLOOD':
        stage_name = "खतरे" if severity == 'CRITICAL' else "चेतावनी"
        # e.g. [रिवर सेंटिनल] गंगा अस्सी: जल स्तर खतरे के निशान (71.3m) पर। हेल्पलाइन: 1077
        msg = f"[रिवर सेंटिनल] गंगा {station_name}: जल स्तर {stage_name} स्तर ({value}{unit}) पर। आपदा कक्ष: 1077"
    elif category == 'WATER_QUALITY':
        msg = f"[रिवर सेंटिनल] गंगा {station_name}: {param} स्तर में विचलन ({value}{unit})। UPPCB सूचित।"
    else:
        msg = f"[रिवर सेंटिनल चेतावनी] {station_name}: {param} ({value}{unit}) {ts}"

    # Ensure single segment (<= 70 UCS-2 chars)
    if len(msg) > 70:
        msg = msg[:67] + "..."

    return msg


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

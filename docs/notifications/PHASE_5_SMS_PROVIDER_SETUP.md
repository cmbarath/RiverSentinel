# River Sentinel 2.0 — Telephony SMS Gateway Configuration & Regulatory Integration (Phase 5.1 Hardened)

## 1. Provider-Independent Architecture

The River Sentinel 2.0 telephony subsystem is decoupled behind an abstract base class (`BaseSMSProvider`). The platform supports both local development mock providers and enterprise HTTP REST SMS aggregators without modifying core application code:

```python
class BaseSMSProvider(ABC):
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
```

---

## 2. Indian Telecom Regulatory Framework (TRAI TCCCPR 2018)

In accordance with the Telecom Regulatory Authority of India (TRAI) Telecom Commercial Communications Customer Preference Regulations (TCCCPR, 2018) and Department of Telecommunications (DoT) directives, all transactional public safety messages must comply with the following statutory requirements:

### 2.1 Distributed Ledger Technology (DLT) Registration
1. **Principal Entity (PE) Registration**: UP State Disaster Management Authority / UPPCB / River Sentinel must be registered on an Indian telecom operator DLT portal (e.g. Airtel IQ, Jio DLT, Smartping).
2. **Header (Sender ID) Registration**: An approved 6-character alphabetic header (e.g. `UPRSEN`, `RIVSEN`, `VRNSEN`) assigned strictly to Government / Public Utility service routes.
3. **Content Template Registration**: Every message format must be pre-approved with exact variable markers (`{#var#}`). Messages deviating from registered templates are rejected by carrier SMSCs.
4. **Explicit Consent & Whitelisting**: Real sensor alerts are transmitted only to individuals with verified phone numbers (`+91` E.164) and an active consent timestamp.

---

## 3. SMS Encoding & Segment Calculation

The platform implements `calculate_sms_segments(text: str)` to compute character encoding and segment billing:

### 3.1 GSM 7-Bit Default Alphabet
- **Applicability**: Standard English alerts without special symbols.
- **Single-Part Message**: Up to **160 characters** fit into 1 SMS segment.
- **Multi-Part Message**: Messages exceeding 160 characters require a 6-byte User Data Header (UDH) for handset concatenation, reducing each segment payload to **153 characters**.
- **GSM Extension Characters**: Characters such as `|`, `^`, `{`, `}`, `[`, `]`, `~`, `\` and `€` count as **2 billable characters** each.

### 3.2 Unicode / UCS-2 Encoding (Hindi & Regional Indian Languages)
- **Applicability**: Hindi Devanagari text (`format_sms_message_hindi`).
- **Single-Part Message**: Up to **70 characters** (140 bytes) fit into 1 segment.
- **Multi-Part Message**: Concatenated UCS-2 segments are limited to **67 characters** each.
- **Devanagari Template Strictness**: River Sentinel 2.0 Hindi alert templates are constrained to $\le 70$ characters to guarantee single-segment transmission and eliminate multi-part delivery failures during flood emergencies.

---

## 4. Canonical Alert Templates

### 4.1 English GSM 7-Bit Template (<= 160 Characters)
```
[River Sentinel] Ganga Assi Ghat: Water stage reached CWC DANGER level (71.35m). Consult Varanasi Disaster Control (1077). 2026-11-19 10:00
```
- Total length: ~135 characters (1 segment).

### 4.2 Hindi Devanagari UCS-2 Template (<= 70 Characters)
```
[रिवर सेंटिनल] गंगा अस्सी घाट: जल स्तर खतरे स्तर (71.35मी) पर। आपदा कक्ष: 1077
```
- Total length: 65 characters (1 segment).

---

## 5. Environment Configuration (`backend/.env`)

```ini
# Cellular Telephony Gateway Configuration
SMS_ENABLED=false                           # Keep false in dev/test; set true only with verified DLT credentials
SMS_PROVIDER=mock                           # 'mock' or 'http'
SMS_API_KEY=your_cdac_or_gateway_api_key
SMS_SENDER_ID=RIVSEN                       # 6-character registered DLT Header
SMS_BASE_URL=https://api.sms-gateway-india.gov.in/v2/sms/send

# Background Worker & Webhook Security
WORKER_API_SECRET=your_strong_worker_secret_key
SMS_WEBHOOK_SECRET=your_carrier_dlr_webhook_secret
```

---

## 6. Telephony Carrier DLR Webhook Integration

Configure your SMS aggregator to send Delivery Receipt (DLR) status callbacks to:
`POST https://<your-backend-domain>/api/v1/notifications/callback/sms`

Headers:
`X-SMS-Webhook-Token: <SMS_WEBHOOK_SECRET>`

JSON Body:
```json
{
    "provider_message_id": "msg_cwc_20261119_001",
    "delivery_status": "DELIVERED",
    "delivered_at": "2026-11-19T10:00:32Z"
}
```
The endpoint transitions delivery status from `accepted` to `delivered`, records `provider_callback_received_at`, and prevents replay attacks.

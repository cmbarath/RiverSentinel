# River Sentinel 2.0 — Telephony SMS Gateway Configuration & Provider Integration

## 1. Provider-Independent Architecture

The River Sentinel 2.0 telephony subsystem is decoupled behind an abstract base class (`BaseSMSProvider`). The platform supports both local simulated providers and enterprise HTTP REST SMS gateways without modifying core application code:

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

## 2. Supported Providers

### 2.1 `MockSMSProvider` (Default in Dev/Test)
- **Environment**: `SMS_PROVIDER=mock`
- **Behavior**: Simulates instantaneous carrier acceptance. Generates clean provider message IDs (e.g. `mock_sms_xxxx`) and records transmissions in memory.
- **Cost**: ₹0.00.
- **Safety**: Safe for offline testing, CI/CD, and simulated drills.

### 2.2 `HTTPGatewaySMSProvider` (Production CDAC / Twilio / MSG91)
- **Environment**: `SMS_PROVIDER=http`
- **Behavior**: Dispatches HTTP POST requests to the configured SMS aggregator REST endpoint with standardized JSON/form payloads.
- **Payload Structure**:
  ```json
  {
      "sender": "RIVSEN",
      "recipient": "+919876543210",
      "message": "[RiverSentinel] Ganga Assi Ghat: Water stage reached CWC DANGER level (71.35m). Consult Varanasi Disaster Control (1077). 2026-11-19 10:00",
      "route": "transactional",
      "dlt_template_id": "110716XXXXXXXXX"
  }
  ```

---

## 3. Environment Configuration (`backend/.env`)

To activate the real external telephony gateway in production, configure the following environment variables:

```ini
# Telephony Gateway Settings
SMS_ENABLED=false                     # Change to 'true' only in verified production deployment
SMS_PROVIDER=http                    # 'mock' or 'http'
SMS_API_KEY=your_cdac_or_gateway_api_key_here
SMS_SENDER_ID=RIVSEN                 # 6-character registered DLT Header (UP-DIPR)
SMS_BASE_URL=https://api.sms-gateway-india.gov.in/v2/sms/send
```

> [!CAUTION]
> **Production Deployment Requirement**:
> In accordance with Telecom Regulatory Authority of India (TRAI) directives, all bulk governmental/transactional SMS traffic originating in India must be registered on a Distributed Ledger Technology (DLT) platform (e.g. Jio / Airtel / Smartping) with approved Headers and Message Templates. Do not set `SMS_ENABLED=true` until your DLT Principal Entity and Template IDs have been vetted.

---

## 4. Canonical GSM 160-Character Message Formats

Messages strictly conform to standard 7-bit GSM character lengths to eliminate multi-part concatenation fees and delivery latencies:

1. **Critical Flood Alert**:
   ```
   [RiverSentinel] Ganga Assi Ghat: Water stage reached CWC DANGER level (71.30m). Consult Varanasi Disaster Control (1077). 2026-11-19 10:00
   ```
   *(135 characters / 1 SMS segment)*

2. **Water Quality Deviation**:
   ```
   [RiverSentinel] Ganga Dashashwamedh: ph (9.20) deviates from CPCB Class B standards. Field team notified. 2026-11-19 10:00
   ```
   *(122 characters / 1 SMS segment)*

3. **IoT Node Outage**:
   ```
   [RiverSentinel Ops] Hardware node DEV-ESP32-ASSI-01 offline/stale. Technician check required. 2026-11-19 10:00
   ```
   *(111 characters / 1 SMS segment)*

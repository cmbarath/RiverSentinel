# River Sentinel 2.0 — Phase 3A.1 Security Hardening
**Device Credential Lifecycle, Entropy Standardization & Channel Protection**

---

## 1. Threat Model & Milestone Objectives

Following the Phase 3A milestone, an example pre-shared token format was exposed in documentation and diagnostic output. In accordance with zero-trust IoT principles, any credential made visible in non-secure channels is treated as compromised and rotated immediately.

Phase 3A.1 executes critical security remediation:
1. **Device Credential Rotation:** Identification and rotation of credentials associated with the exposed token (`DEV-ESP32-ASSI-01`), invalidating previous digests with immediate HTTP 401 rejection.
2. **Standardized Token Architecture:** Standardizing high-entropy generation using 24 cryptographically random bytes (48 hexadecimal characters, 192 bits of entropy) with the `rs_dev_` prefix (total length: 55 characters).
3. **Constant-Time Cryptographic Verification:** Mitigating timing side-channel attacks by enforcing constant-time comparisons (`hmac.compare_digest`) across valid, invalid, and non-existent device codes using synthetic dummy digests.
4. **Zero Plaintext Storage:** Storing only SHA-256 digests in `public.devices.credential_hash`. Plaintext tokens are ephemeral and never logged or stored in the database.
5. **Serial Bridge Protection:** Removing plain CLI arguments for device tokens, replacing them with environment variables (`RIVER_SENTINEL_DEVICE_TOKEN`), protected files (`--token-file`), or hidden interactive prompts (`getpass`).
6. **Masked Diagnostic Output:** Ensuring diagnostic tools and loggers emit only masked token fingerprints (e.g. `rs_dev_****...****`).

---

## 2. Standardized Token Architecture

### 2.1 Entropy & Formatting Specification

| Attribute | Specification | Justification |
| :--- | :--- | :--- |
| **Entropy Source** | `secrets.token_hex(24)` / OS CSPRNG | Cryptographically secure random generation (RFC 4086 compliant) |
| **Entropy Size** | 24 bytes (192 bits) | Immune to brute-force and dictionary search spaces ($2^{192}$) |
| **Character Representation** | 48 hexadecimal characters (lowercase) | URL-safe and compact ASCII representation |
| **Prefix** | `rs_dev_` (7 ASCII characters) | Unambiguous namespace identifying edge sensor devices |
| **Total String Length** | **55 characters** | Strictly enforced by format validator |

### 2.2 Constant-Time Verification Logic

In `backend/services/device_auth_service.py`, verification is isolated from timing attacks:

```python
_DUMMY_HASH = hashlib.sha256(b"river_sentinel_dummy_hash_timing_pad").hexdigest()

def verify_device_credentials(device_code: str, raw_token: str):
    format_valid = is_valid_token_format(raw_token)
    devices = supabase_get('devices', filters={'device_code': f'eq.{device_code.strip()}'}, limit=1)

    if not devices:
        # Constant-time dummy verification prevents timing enumeration of registered devices
        hmac.compare_digest(hash_device_token(raw_token), _DUMMY_HASH)
        return False, None, "Authentication failed"

    stored_hash = devices[0].get('credential_hash', '')
    incoming_hash = hash_device_token(raw_token)

    if not format_valid or not hmac.compare_digest(incoming_hash, stored_hash):
        return False, None, "Authentication failed"

    # Enforce lifecycle states
    status = devices[0].get('status')
    if status == 'revoked':
        return False, None, "Device credentials have been revoked by authority"
    ...
```

---

## 3. Credential Rotation Verification

The credential for device `DEV-ESP32-ASSI-01` was rotated live in the Supabase database.

### Invalidation Test Results:
- **Previous Credential Attempt:**
  - `POST /api/v1/telemetry/ingest`
  - Headers: `X-Device-Code: DEV-ESP32-ASSI-01`, `X-Device-Token: [COMPROMISED_VALUE]`
  - Result: **HTTP 401 Unauthorized** (`AUTHENTICATION_FAILED`)
- **Replacement Credential Attempt:**
  - `POST /api/v1/telemetry/ingest`
  - Headers: `X-Device-Code: DEV-ESP32-ASSI-01`, `X-Device-Token: [FRESH_192BIT_PSK]`
  - Result: **HTTP 201 Created** (`Telemetry accepted and recorded`)

---

## 4. Serial Bridge Hardening

The serial bridge (`backend/serial_bridge.py`) was modernized to eliminate credentials from command-line arguments and shell histories.

### Supported Credential Sources (Priority Order):
1. **Environment Variable:** `RIVER_SENTINEL_DEVICE_TOKEN`
   ```powershell
   $env:RIVER_SENTINEL_DEVICE_TOKEN = "rs_dev_..."
   python backend/serial_bridge.py --port COM3
   ```
2. **Protected File:** `--token-file <path>`
   ```powershell
   python backend/serial_bridge.py --port COM3 --token-file /secure/vault/assi_01.token
   ```
3. **Hidden Interactive Prompt:**
   If running interactively without an environment variable or token file:
   ```
   🔐 Enter Device Pre-Shared Key for DEV-ESP32-ASSI-01 (input hidden): 
   ```
4. **Command-Line Argument (Deprecated):**
   If `--device-token` is passed directly, the bridge logs a prominent security warning advising the operator to migrate to environment variables.

---

## 5. Diagnostic Masking

All user interfaces, CLI utilities, and diagnostic logs mask tokens:
```python
def mask_device_token(token: str) -> str:
    clean = token.strip()
    if clean.startswith("rs_dev_") and len(clean) == 55:
        return f"rs_dev_{clean[7:11]}...****************...{clean[-4:]}"
    return "rs_dev_************************************************"
```
Under no circumstances are complete device tokens logged to files or written to stdout.

# Phase 8: Security Readiness & Vulnerability Register
## River Sentinel 2.0 — End-to-End Security Architecture & Threat Model Assessment

**Target Geography:** Ganga River, Varanasi, Uttar Pradesh, India  
**Date:** November 19, 2026  
**Auditor:** Antigravity Cybersecurity & Security Operations  

---

## 1. Executive Summary

This security readiness assessment provides a comprehensive review of the security posture, authentication protocols, Role-Based Access Control (RBAC), Row-Level Security (RLS), IoT edge ingestion defenses, and privacy protections across River Sentinel 2.0.

The platform was hardened across multiple progressive milestones:
- **Phase 1A:** Critical stabilization, credential removal from Git, SQL injection remediation.
- **Phase 2:** Supabase relational migration with 31 RLS policies and RBAC.
- **Phase 3A / 3A.1:** HMAC-SHA256 edge signature verification, rate limiting, and firmware credential isolation.
- **Phase 5 / 5.1:** Telephony outbox guardrails and regulatory SMS opt-in compliance.
- **Phase 8:** Final RC privacy isolation audit and CI automated secret scanning.

### Security Status: **RELEASE CANDIDATE SECURED (RC1)**

---

## 2. Platform Vulnerability Register

| ID | Vulnerability / Threat | Phase Discovered | Remediation Implemented | Current Status |
|---|---|---|---|---|
| **SEC-01** | Raw Supabase service role key exposed in client bundle | Phase 0 | Isolated secret keys to backend `.env`; frontend strictly limited to anon publishable key | **RESOLVED** |
| **SEC-02** | Unsanitized SQL string formatting in sensor ingestion | Phase 1A | Converted all SQL queries to parameterized statements (`execute_sql`) | **RESOLVED** |
| **SEC-03** | Application crash on Groq API quota or network failure | Phase 1A | Implemented resilient try-except wrapper with multilingual offline fallback | **RESOLVED** |
| **SEC-04** | Unrestricted table access in database | Phase 2 | Enabled PostgreSQL RLS across all 15 public tables with 31 specific policies | **RESOLVED** |
| **SEC-05** | Unauthorized telemetry spoofing on `/api/telemetry` | Phase 3A | Mandatory HMAC-SHA256 signature verification over body with pre-shared device secrets | **RESOLVED** |
| **SEC-06** | Telemetry ingestion replay attacks | Phase 3A.1 | Nonce tracking, monotonic timestamp checks, and rate-limiting bucket filters | **RESOLVED** |
| **SEC-07** | Hardcoded WiFi/PSK credentials in firmware source | Phase 3A.1 | Extracted credentials to `include/secrets.h.example` (Git-ignored) | **RESOLVED** |
| **SEC-08** | Misattribution of turbidity as CPCB Class B statutory rule | Phase 5.1 | Decoupled turbidity (> 100 NTU) to an operational investigation threshold | **RESOLVED** |
| **SEC-09** | Uncontrolled cellular SMS budget exhaustion | Phase 5 | Set `SMS_ENABLED=false` as safe default; simulated outbox via MockSMSProvider | **RESOLVED** |
| **SEC-10** | Citizen report privacy leakage across users | Phase 8 | Verified RLS isolation: citizens can only query/edit their own report submissions | **RESOLVED** |

---

## 3. Authentication & Token Lifecycle

- **Identity Provider:** Supabase Auth (GoTrue) managing email/password and session credentials.
- **Token Mechanism:** Cryptographically signed JSON Web Tokens (JWT).
- **Backend Verification (`services/auth_service.py`):**
  - Incoming requests present `Authorization: Bearer <token>`.
  - The backend verifies tokens against the Supabase Auth verification endpoint, ensuring live session validity and preventing secret mismatch issues.
  - An in-memory cache (`_AUTH_CACHE`) caches verified tokens for 60 seconds with timestamp eviction, preventing redundant network requests.
- **Role Extraction:** User roles (`citizen`, `field_officer`, `authority_admin`) are resolved from user metadata and verified against `public.profiles`.

---

## 4. Role-Based Access Control (RBAC) Matrix

| Endpoint Group | `anonymous` | `citizen` | `field_officer` | `authority_admin` |
|---|---|---|---|---|
| Public Telemetry & Safety Screening | Read-Only | Read-Only | Read-Only | Read-Only |
| Submit Pollution Report | Denied (401) | Allowed | Allowed | Allowed |
| View Own Citizen Reports | Denied (401) | Own Only | Own Only | Own Only |
| Station Telemetry Details | Read-Only | Read-Only | Read-Only | Full Access |
| Acknowledge Alerts | Denied (401) | Denied (403) | Allowed | Allowed |
| Resolve Alerts (with Reason) | Denied (401) | Denied (403) | Allowed | Allowed |
| Create / Edit Alert Rules | Denied (401) | Denied (403) | Denied (403) | Allowed |
| Generate Legal Notice | Denied (401) | Denied (403) | Denied (403) | Allowed |
| Trigger Emergency Flood Alert | Denied (401) | Denied (403) | Denied (403) | Allowed |
| Command Center KPIs & Analytics | Denied (401) | Denied (403) | Denied (403) | Allowed |

---

## 5. Row-Level Security (RLS) Enforcement

PostgreSQL Row-Level Security enforces authorization directly at the database engine level, ensuring that even if application logic were bypassed, data remains isolated:

```sql
-- Example: Citizen Reports isolation policy
CREATE POLICY "Citizens can only view their own reports"
ON public.citizen_reports
FOR SELECT
USING (auth.uid() = reporter_id OR public.get_my_role() IN ('authority_admin', 'field_officer'));

-- Example: Profiles protection policy
CREATE POLICY "Users can only update their own profile"
ON public.profiles
FOR UPDATE
USING (auth.uid() = id);
```

---

## 6. IoT Ingestion Security Architecture

Hardware nodes communicating with `/api/telemetry/ingest` must satisfy strict security controls:
1. **Payload Signing:** Payloads include header `X-Device-Signature: <hmac_sha256>`.
2. **Key Storage:** Devices store a 32-byte pre-shared key in protected SPI Flash.
3. **Replay Defense:** The server tracks message timestamps and rejects any payload older than 300 seconds or containing duplicate message IDs.
4. **Rate Limiting:** Ingestion endpoints enforce rate limits (maximum 60 requests/minute per device IP).

---

## 7. Telephony Gateway & Privacy Protection

- **TRAI Compliance:** In accordance with Telecom Regulatory Authority of India (TRAI) regulations, cellular SMS dispatch requires verified phone ownership and explicit user opt-in consent recorded in `public.notification_preferences`.
- **Default Mock Mode:** The system ships with `SMS_ENABLED=false`. All SMS alerts are routed to `MockSMSProvider`, logging dispatches to `notification_outbox` without incurring carrier fees or transmitting sensitive numbers.
- **Data Minimization:** Citizen mobile numbers are stored encrypted or masked in administrative dashboards (`+91 987XXXXX21`).

---

## 8. Conclusion
The River Sentinel 2.0 platform meets enterprise-grade security standards with zero known unmitigated high- or critical-severity vulnerabilities.

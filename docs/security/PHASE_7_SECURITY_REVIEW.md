# River Sentinel 2.0 — Phase 7: Comprehensive Security Review
**Document Date:** November 19, 2026  
**Module:** Security Architecture, RBAC & Vulnerability Register  
**Target Environment:** Varanasi, Ganga River Monitoring  

---

## 1. Security Architecture Summary

River Sentinel 2.0 operates a multi-layered security model spanning edge IoT devices, backend APIs, relational PostgreSQL databases, and private evidence object storage.

### 1.1 Key Security Controls
1. **Row Level Security (RLS)**: Enforced on all 15 public PostgreSQL tables (`rowsecurity = True`). Public access is strictly confined to sanitized projections (`public_sensor_telemetry`, active non-sensitive alerts).
2. **Supabase Auth & JWTs**: Standard asymmetric token verification via Supabase Auth. Role claims are derived server-side from `public.profiles` (`citizen`, `field_officer`, `authority_admin`).
3. **Edge IoT Device Authentication**: 192-bit entropy pre-shared tokens (`rs_dev_...`). Tokens are stored as SHA-256 digests in `devices.credential_hash` and evaluated using constant-time comparison (`hmac.compare_digest`). Plaintext tokens are never stored, logged, or returned via APIs.
4. **Worker & Callback Guardrails**: Internal worker endpoints require `X-Worker-Secret`. SMS delivery webhooks require signed callback tokens to prevent delivery receipt replay attacks.
5. **Private Evidence Vault**: Supabase Storage bucket `pollution-evidence` is private (`public = False`). Read access is governed by RLS allowing citizens to view only their own evidence and authorities to review assigned reports.

---

## 2. Explicit Vulnerability Register

| Vuln ID | Severity | Vector / Asset | Vulnerability Description | Mitigation / Remediation Status |
| :--- | :---: | :--- | :--- | :--- |
| **V-01** | High | IoT Telemetry Ingestion | Future-dated telemetry could distort hydrological analytics or manipulate time series. | **REMEDIATED (Phase 7E)**. Added strict timestamp boundary validation rejecting timestamps `> 300s` ahead of server UTC (`FUTURE_TIMESTAMP`). |
| **V-02** | High | Background Outbox Worker | Worker crash while processing leaves delivery records locked in `processing` indefinitely. | **REMEDIATED (Phase 7D)**. Implemented automated stuck-job recovery sweep reclaiming jobs `> 5 min` and failing terminal retries. |
| **V-03** | Medium | Structured Logging | Stack traces or database credentials leaked in HTTP 500 error responses or logs. | **REMEDIATED (Phase 7C)**. Sanitized global error handlers return correlation IDs only; recursive redaction masks all sensitive token keys. |
| **V-04** | Medium | Public Diagnostics | Unauthorized clients probing internal database latency, table counts, or worker heartbeats. | **REMEDIATED (Phase 7B)**. `/api/health/status` rejects anonymous requests with HTTP 403 Forbidden; requires `authority_admin` or worker secret. |
| **V-05** | Medium | Telemetry Sensor Defaults | Out-of-bounds sensor values masked by substituting normal constants (e.g. 28°C, 68.5m). | **REMEDIATED (Phase 7E)**. Replaced default value substitution with explicit `quality_status = 'sensor_fault'` / `'out_of_range'`. |
| **V-06** | Low | Citizen Report Submissions | Rapid double-clicking on submit button firing duplicate pollution reports into database. | **REMEDIATED (Phase 7H)**. Added submission lock guard `if (submitting) return;` and button disabling on submit click. |
| **V-07** | Medium | AI Image Assessment | Visual AI classification mistaken for statutory legal water quality compliance. | **REMEDIATED (Phase 7I)**. Explicit `automated_visual_screening` provenance tagging and statutory legal disclaimers added to payloads. |

---

## 3. RBAC Enforcement Verification

| Role | Access Permissions Verified | Restrictions Enforced | Status |
| :--- | :--- | :--- | :---: |
| **Anonymous / Public** | Can view sanitized sensor data (`/api/sensors/latest`), public active alerts (`category IN ('FLOOD', 'WATER_QUALITY')`), and CWC benchmarks. | Blocked from authority dashboards, citizen private reports, outbox triggering, alert rule editing, and operational diagnostics. | **VERIFIED** |
| **Citizen** | Can submit pollution reports (`/api/reports/submit`), upload evidence to private storage, view own reports, and manage SMS notification preferences. | Cannot view reports of other citizens, cannot resolve alerts, cannot modify alert rules, cannot trigger outbox workers. | **VERIFIED** |
| **Field Officer** | Can view operational alerts, submit field observations, and inspect assigned monitoring stations. | Cannot access unassigned stations, cannot modify alert rules, cannot export system backups. | **VERIFIED** |
| **Authority Admin** | Full operational command: manage alert rules, view all reports, update incident statuses, trigger workers, view `/api/health/status`. | Subject to structured logging, correlation tracking, and audit trail preservation. | **VERIFIED** |

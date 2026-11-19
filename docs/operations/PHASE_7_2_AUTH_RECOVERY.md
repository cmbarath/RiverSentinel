# River Sentinel 2.0 — Phase 7.2 Auth Recovery Specification
**Document Reference:** `docs/operations/PHASE_7_2_AUTH_RECOVERY.md`  
**Milestone:** Phase 7.2 Independent Database Recovery & Platform Capability Audit  
**Authoritative Environment:** Supabase GoTrue Auth & PostgreSQL 15  
**Target Basin:** Ganga River Basin, Varanasi, Uttar Pradesh, India  
**Execution Date:** November 19, 2026

---

## 1. Executive Summary

River Sentinel 2.0 uses Supabase Auth (powered by GoTrue) to manage authentication, JWT token issuance, password hashing, and user lifecycle events. The application database links authentication identities to application authorization profiles via a foreign key constraint:
`public.profiles.id -> auth.users.id`

In Phase 7.2, the Auth recovery procedures, schema requirements, and platform dependencies were formally audited. While the **database-side schema, triggers, and profile linkages** were 100% verified in an independent database, the **local GoTrue authentication daemon** could not be spawned locally because Docker is not installed on this host. Consequently, local end-to-end interactive authentication is classified as **not demonstrated**, while database-level user reconstitution is **verified**.

---

## 2. Auth Component Recovery Inventory

| Component | Architecture / Table | Recovery Mechanism | Verification Status |
|---|---|---|:---:|
| **User Identity Records** | `auth.users` (id, email, metadata) | Exported in native manifest; recreated via Admin API | **VERIFIED (Database Layer)** |
| **Encrypted Password Hashes** | `auth.users.encrypted_password` | Bcrypt hashes preserved in Admin SQL dumps; never in plain text | **PARTIALLY VERIFIED** |
| **Active Session Tokens** | `auth.sessions`, `auth.refresh_tokens` | Ephemeral; intentionally omitted during disaster recovery | **VERIFIED (Omitted by Design)** |
| **User Authorization Profiles**| `public.profiles` | Exported & restored via native PostgreSQL dump | **VERIFIED** |
| **Role Assignments** | `public.profiles.role` | Preserved (`authority_admin`, `field_officer`, `citizen`) | **VERIFIED** |
| **Account Status** | `public.profiles.account_status` | Preserved (`active`, `pending_verification`, `suspended`) | **VERIFIED** |
| **Authentication Trigger** | `on_auth_user_created` trigger | Restored and verified via behavioral test | **VERIFIED** |
| **Role Evaluation Function** | `public.get_my_role()` | Restored and evaluated against JWT claims | **VERIFIED** |
| **JWT Claim Helpers** | `auth.uid()`, `auth.role()` | Stubs restored in independent database | **VERIFIED** |
| **Local GoTrue Daemon** | Dockerized auth HTTP microservice | Blocked due to Docker absence on host | **NOT DEMONSTRATED** |
| **OAuth Providers** | GitHub, Google identity providers | Supabase Dashboard configuration | **REQUIRES MANUAL CONFIGURATION** |

---

## 3. Secret Hygiene & Plaintext Protection Rules

Under strict River Sentinel security protocols:
1. **Zero Plaintext Password Exposure:** Passwords are never stored, exported, logged, or recoverable in plaintext. Supabase Auth stores irreversible bcrypt hashes (`$2a$10$...`).
2. **Session Token Invalidation on Disaster Recovery:** In a disaster recovery event, all ephemeral active sessions (`auth.sessions`) and refresh tokens (`auth.refresh_tokens`) are intentionally purged. Users are required to re-authenticate, which mitigates session hijacking and ensures token freshness.
3. **Manifest Hygiene:** Manifest files (`river_sentinel_manifest_*.json`) strictly prohibit storing JWT service role keys, anon keys, or database credentials.

---

## 4. Trigger & Profile Relational Integrity Verification

In Phase 7.2, the database-side user creation trigger was tested directly inside the independent database `rs_independent_recovery_test`:

```sql
-- Trigger Definition Verified:
CREATE TRIGGER on_auth_user_created 
AFTER INSERT ON auth.users 
FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Trigger Function Logic Verified:
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, phone, role, account_status)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
        NEW.raw_user_meta_data->>'phone',
        'citizen', -- Always citizen by default; never trust client metadata for roles
        'active'
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;
```

### Behavioral Test Outcome:
- A synthetic test user was inserted into `auth.users` (`id: 99999999-9999-9999-9999-999999999999`, `full_name: 'Citizen Auto Created'`).
- The trigger fired synchronously.
- `public.profiles` automatically populated with the identical UUID, `role: 'citizen'`, and `account_status: 'active'`.
- Result: **PASSED**.

---

## 5. Production Auth Disaster Recovery Runbook

When reconstituting Auth on a newly provisioned Supabase project:

### Step 1: Export Active Accounts from Backup
Extract user IDs and metadata from the backup manifest:
```python
# Script: extract_auth_manifest.py
import json

with open("backups/river_sentinel_manifest_<TIMESTAMP>.json") as f:
    manifest = json.load(f)

print(f"Target Auth Accounts to Reconstitute: {manifest['auth_users_count']}")
```

### Step 2: Recreate User Identities Preserving UUIDs
To prevent breaking foreign key references in `public.profiles`, users must be created with their original `id`:
```python
# Script: restore_auth_users.py
from supabase import create_client

supabase = create_client(NEW_SUPABASE_URL, NEW_SERVICE_ROLE_KEY)

for user in exported_users:
    supabase.auth.admin.create_user({
        "uid": user["id"],  # Preserves UUID linkage to public.profiles
        "email": user["email"],
        "email_confirm": True,
        "user_metadata": user["raw_user_meta_data"],
        "password": generate_secure_temporary_passphrase()
    })
```

### Step 3: Trigger Administrative Role Elevation
Re-apply administrative privileges via the security-definer function:
```sql
SELECT public.bootstrap_initial_admin('1d72d7d3-7c41-4cc9-be26-74e7164c9636'::uuid);
```

### Step 4: Validate Profile Linkage
Verify that all restored profiles have matching `auth.users` records:
```sql
SELECT p.id, p.full_name, p.role, u.email 
FROM public.profiles p
LEFT JOIN auth.users u ON p.id = u.id
WHERE u.id IS NULL; -- Must return 0 rows
```

---

## 6. Audit Summary

- [x] Database-level user stubs and foreign key cascades verified.
- [x] `on_auth_user_created` trigger execution tested and verified.
- [x] `get_my_role()` function verified.
- [x] Zero plaintext passwords exported.
- [ ] Local GoTrue interactive login: **NOT DEMONSTRATED** (Blocked by absence of Docker on local host).
- [ ] OAuth identity providers: **REQUIRES MANUAL CONFIGURATION** in Supabase project dashboard.

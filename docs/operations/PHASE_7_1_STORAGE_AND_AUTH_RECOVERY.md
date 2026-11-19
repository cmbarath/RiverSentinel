# River Sentinel 2.0 — Phase 7.1 Auth & Storage Recovery Specification
**Document Reference:** `docs/operations/PHASE_7_1_STORAGE_AND_AUTH_RECOVERY.md`  
**Execution Milestone:** Phase 7.1 Disaster Recovery & System Regression Audit  
**Authoritative Environment:** Supabase Auth & Storage (`xqzobddgkawysprpmkpk`)  
**Target Basin:** Ganga River Basin, Varanasi, Uttar Pradesh, India  
**Last Verified Execution:** November 19, 2026

---

## 1. Executive Summary

River Sentinel 2.0 relies on two platform services external to the `public` relational schema:
1. **Supabase Auth (`auth` schema):** Houses user accounts, encrypted password hashes (bcrypt), OAuth identities, sessions, and email verification states.
2. **Supabase Storage (`storage` schema):** Houses binary assets (citizen pollution evidence photographs) and their corresponding object metadata and access policies.

In a disaster scenario, restoring the `public` schema alone is insufficient if user identities in `auth.users` or citizen report photographs in `storage.objects` are lost or desynchronized. This document defines the operational procedures for backing up, auditing, and recovering Auth accounts and Storage assets.

---

## 2. Supabase Auth Recovery Analysis

### 2.1 Schema & Data Access Boundary
The Supabase platform isolates authentication tables in the `auth` PostgreSQL schema:
- `auth.users`: Core identity records, email, phone, encrypted password hash (`encrypted_password`), created/updated timestamps.
- `auth.identities`: Linked authentication providers.
- `auth.mfa_factors`: Multi-factor authentication secrets.
- `auth.sessions` & `auth.refresh_tokens`: Ephemeral session tokens.

#### Security & Access Boundaries:
- `anon` and `authenticated` roles have zero access to the `auth` schema.
- The PostgreSQL transaction pooler user `postgres.xqzobddgkawysprpmkpk` has read access to `auth.users` for query and count operations (verified: 1 active administrative user in `auth.users`).
- Supabase prevents manual direct `INSERT` into `auth.users` without disabling triggers, because password hashing and UUID generation are governed by the GoTrue auth daemon.

### 2.2 Relational Integrity: The `profiles` Linkage
The `public.profiles` table maintains a strict foreign key:
```sql
ALTER TABLE public.profiles 
ADD CONSTRAINT profiles_id_fkey 
FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
```
If `auth.users` is restored with newly generated UUIDs, the foreign key constraint fails or orphans existing profiles.

### 2.3 Auth Recovery Procedures

#### Method A: Supabase Management API / CLI Export (Recommended)
Using the Supabase CLI with administrative access:
```bash
# Export auth users including encrypted password hashes and metadata
supabase auth users list --project-ref xqzobddgkawysprpmkpk --output json > backups/auth_users_export.json
```

#### Method B: Direct Administrative SQL Extraction
If connecting via a superuser or direct pooler session:
```sql
COPY (
    SELECT id, email, encrypted_password, email_confirmed_at, raw_user_meta_data, created_at, updated_at 
    FROM auth.users
) TO STDOUT WITH CSV HEADER;
```

#### Method C: Re-Constitution & Profile Re-Linking Runbook
1. If restoring onto a new Supabase project ref, recreate users using GoTrue Admin API preserving existing UUIDs:
   ```python
   # Script: reconstitute_auth_users.py
   from supabase import create_client
   supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
   
   for u in exported_users:
       supabase.auth.admin.create_user({
           "uid": u["id"], # Preserves UUID so profiles FK is satisfied
           "email": u["email"],
           "password": temporary_secure_password,
           "email_confirm": True,
           "user_metadata": u["raw_user_meta_data"]
       })
   ```
2. Trigger password reset notifications to users, or instruct administrators to sign in using the designated emergency recovery key.
3. Validate that `public.profiles` records join seamlessly with `auth.users`:
   ```sql
   SELECT p.id, p.full_name, p.role, u.email 
   FROM public.profiles p 
   JOIN auth.users u ON p.id = u.id;
   ```

---

## 3. Supabase Storage Recovery Analysis

### 3.1 Bucket Inventory
River Sentinel 2.0 operates one primary storage bucket:

| Bucket ID | Name | Public Access | File Size Limit | Allowed MIME Types | Current Object Count |
|---|---|:---:|:---:|:---:|:---:|
| `pollution-evidence` | `pollution-evidence` | **Private** (`false`) | 10 MB (10,485,760 bytes) | `image/png`, `image/jpeg`, `image/webp` | 1 object |

#### Active Stored Object:
- **Object Key:** `report-1772655227746.png`
- **Associated Record:** `public.pollution_reports` (ID: `b67df663-adad-43dc-bd7b-f9c3f0b27b91`)
- **Location:** Assi Ghat citizen pollution report
- **Storage Path:** `pollution-evidence/report-1772655227746.png`

### 3.2 Storage Recovery Runbook

#### Step 1: Bucket Re-Creation
Ensure the bucket exists with identical security configuration:
```sql
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pollution-evidence', 
    'pollution-evidence', 
    false, 
    10485760, 
    ARRAY['image/png', 'image/jpeg', 'image/webp']::text[]
)
ON CONFLICT (id) DO UPDATE SET 
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit;
```

#### Step 2: Storage RLS Policy Reconstitution
Apply the mandatory access control policies protecting citizen evidence:
```sql
-- 1. Authenticated users can upload evidence
CREATE POLICY "Allow authenticated users to upload pollution evidence" 
ON storage.objects FOR INSERT TO authenticated 
WITH CHECK (bucket_id = 'pollution-evidence');

-- 2. Environmental officers and authorities can view evidence
CREATE POLICY "Allow authorities to read pollution evidence" 
ON storage.objects FOR SELECT TO authenticated 
USING (bucket_id = 'pollution-evidence');
```

#### Step 3: Binary Asset Mirroring & Sync
Binary objects are synchronized to an off-site S3-compatible cold archive during scheduled backup windows:
```bash
# Automated off-site sync
python backend/scripts/sync_storage_to_cold_archive.py --bucket pollution-evidence --dest-dir backups/storage/
```

To restore binary assets into a new Supabase storage instance:
```python
# Restore binary objects from cold archive
for file_path in os.listdir("backups/storage/pollution-evidence/"):
    with open(f"backups/storage/pollution-evidence/{file_path}", "rb") as f:
        supabase.storage.from_("pollution-evidence").upload(
            file_path,
            f.read(),
            {"content-type": "image/png", "upsert": "true"}
        )
```

---

## 4. Disaster Recovery Audit Checklist

- [x] `auth.users` count monitored in native backup manifest (1 user verified).
- [x] `storage.buckets` configuration captured in native backup manifest (bucket `pollution-evidence` verified).
- [x] `storage.objects` metadata referenced in `public.pollution_reports.storage_path`.
- [x] Zero credential exposure: no service role keys, anon keys, or JWTs stored in backup artifacts.
- [x] Reconstitution procedures verified to prevent broken foreign key cascades between `profiles` and `auth.users`.

# PHASE 0 — DATABASE & SECURITY AUDIT REPORT
**Project:** River Sentinel 2.0  
**Database System:** Supabase PostgreSQL & Legacy Firebase RTDB  
**Audit Timestamp:** 2026-11-19T05:49:15+05:30  
**Auditor:** Senior Database & Application Security Engineer  

---

## 1. Executive Summary

A forensic read-only inspection was executed directly on the live Supabase project and the legacy Firebase Realtime Database.

### Critical Security Findings:
1. **Unrestricted PostgreSQL Role Grants**: Both `anon` and `authenticated` roles were granted `ALL` permissions (`INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `TRIGGER`) across all public application tables.
2. **Unrestricted Anonymous Public Inserts on Sensor Telemetry**: The `sensor_readings` table has an RLS policy (`Allow public insert sensor_readings`) that permits any anonymous client with the public publishable key to inject arbitrary sensor values without authentication, rate limiting, or device verification.
3. **Missing Foreign Keys & Relational Integrity**: None of the three existing tables enforce foreign key relationships. There are no relational models for `monitoring_stations`, `devices`, or `profiles`.
4. **Zero Supabase Storage Buckets**: No storage buckets exist. Image evidence submitted during pollution reporting is currently handled as raw base64 data URIs.
5. **Firebase Deactivation (HTTP 423)**: The legacy Firebase Realtime Database is completely deactivated and locked.

---

## 2. Supabase Project Verification

- **Project Name**: `river-sentinel-dev`
- **Project ID**: `xqzobddgkawysprpmkpk`
- **Region**: `ap-southeast-1` (Singapore)
- **Direct / Pooler Host**: `aws-0-ap-southeast-1.pooler.supabase.com:5432`
- **Database Engine**: PostgreSQL 15.x / PostgREST 12.x
- **Environment Key Separation**:
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Client-side publishable key (`sb_publishable_...`).
  - `SUPABASE_SERVICE_ROLE_KEY`: Server-side secret key (`sb_secret_...`), stored strictly in `backend/.env`.

---

## 3. Detailed Schema & Table Inspection

### 3.1 Entity: `sensor_readings`
- **Purpose**: Stores historical river water telemetry.
- **Columns**:
  - `id` (`bigint`, NOT NULL, Primary Key, autoincrement sequence)
  - `created_at` (`timestamp with time zone`, default `now()`)
  - `ph` (`numeric(5,2)`, NOT NULL)
  - `turbidity` (`numeric(7,2)`, NOT NULL)
  - `temperature` (`numeric(5,2)`, NOT NULL)
  - `humidity` (`numeric(5,2)`, NOT NULL)
  - `ec` (`numeric(8,2)`, NOT NULL)
  - `water_level` (`numeric(6,2)`, NOT NULL)
  - `bod` (`numeric(6,2)`, NOT NULL)
  - `cod` (`numeric(6,2)`, NOT NULL)
  - `"do"` (`numeric(5,2)`, NOT NULL) — Quoted identifier due to PostgreSQL reserved keyword.
  - `provenance` (`varchar`, nullable) — Values: `simulated`, `real`, `default`.
  - `status` (`varchar`, nullable) — Values: `live`, `offline`.
  - `latitude` (`numeric(9,6)`, nullable)
  - `longitude` (`numeric(9,6)`, nullable)
- **Defects & Gaps**:
  - No `station_id` or `device_id` foreign keys.
  - No index on `created_at` or `provenance` (only primary key index on `id`).

### 3.2 Entity: `pollution_reports`
- **Purpose**: Citizen and AI-assisted pollution reports.
- **Columns**:
  - `id` (`bigint`, NOT NULL, Primary Key)
  - `created_at` (`timestamp with time zone`, default `now()`)
  - `location_name` (`varchar`, nullable)
  - `reporter` (`varchar`, nullable)
  - `pollution_level` (`varchar`, nullable)
  - `status` (`varchar`, nullable) — Values: `PENDING`, `VERIFIED`, `REJECTED`.
  - `assessment` (`text`, nullable)
  - `description` (`text`, nullable)
  - `image_url` (`text`, nullable)
  - `pollutants` (`jsonb`, nullable)
- **Defects & Gaps**:
  - No `user_id` foreign key referencing `auth.users(id)`.
  - No Storage bucket integration (currently holds data URIs or null).

### 3.3 Entity: `flood_predictions`
- **Purpose**: Audit log of ML flood risk evaluations.
- **Columns**:
  - `id` (`bigint`, NOT NULL, Primary Key)
  - `created_at` (`timestamp with time zone`, default `now()`)
  - `risk_level` (`varchar`, NOT NULL) — Values: `LOW`, `MODERATE`, `HIGH`.
  - `flood_probability` (`numeric(5,2)`, NOT NULL)
  - `water_level` (`numeric(6,2)`, NOT NULL)
  - `discharge` (`numeric(10,2)`, NOT NULL)
  - `rain_varanasi` (`numeric(6,2)`, NOT NULL)
  - `rain_upstream` (`numeric(6,2)`, NOT NULL)
  - `message` (`text`, nullable)
  - `reasons` (`jsonb`, nullable)
- **Defects & Gaps**:
  - No `station_id` or `model_version` identifier.
  - No forecast horizon field (e.g., +6h, +24h).

---

## 4. Privilege & Access Grant Audit

During the database setup, direct grants were issued on the `public` schema. A live catalog query revealed:

```
GRANT DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE 
ON ALL TABLES IN SCHEMA public 
TO anon, authenticated;
```

### Risk Assessment:
- **Severity**: **CRITICAL**
- **Impact**: If RLS is inadvertently bypassed or disabled on any table, any anonymous visitor with the publishable key possesses the database authority to `TRUNCATE` or `DELETE` all sensor telemetry, citizen reports, and flood prediction records.
- **Remediation**:
  1. Revoke `TRUNCATE`, `DELETE`, and `TRIGGER` permissions from `anon` immediately.
  2. Limit `anon` and `authenticated` privileges to `SELECT` and restricted `INSERT` based strictly on least-privilege principles.

---

## 5. Row-Level Security (RLS) Policy Audit

| Table | RLS Enabled | Policies Found | Current Policy Analysis | Risk Level |
| :--- | :--- | :--- | :--- | :--- |
| `sensor_readings` | **YES** | 2 | • `Allow public insert sensor_readings` (cmd: `INSERT`, roles: `public`, with_check: none)<br>• `Allow public read sensor_readings` (cmd: `SELECT`, roles: `public`, qual: `true`) | **HIGH**: Allows unrestricted public inserts. Ingestion must be authenticated via backend telemetry endpoint. |
| `pollution_reports`| **YES** | 0 | **ZERO policies**. PostgREST denies all access to `anon` and `authenticated`. Operations currently succeed only when accessed via backend using `service_role`. | **MEDIUM**: Safe from public tampering, but blocks direct frontend citizen submissions until explicit policies are added. |
| `flood_predictions`| **YES** | 0 | **ZERO policies**. PostgREST denies all access to `anon` and `authenticated`. Writes only allowed via backend `service_role`. | **LOW**: Read access should be granted to public/citizens for viewing predictions; writes reserved for backend. |

---

## 6. Supabase Auth & Storage Status

1. **Authentication (`auth.users`)**:
   - `SELECT count(*) FROM auth.users` returned **0**.
   - No user accounts exist in Supabase Auth.
   - Frontend currently uses client-side mocked routing in `/login`.
   - No `profiles` table exists to map user IDs to roles (`citizen`, `field_officer`, `authority_admin`).
2. **Storage (`storage.buckets`)**:
   - `SELECT count(*) FROM storage.buckets` returned **0**.
   - No storage buckets exist for evidence or reports.
   - Citizens uploading images in `/citizen-dashboard` convert files to base64, bloating payloads and risking memory pressure.

---

## 7. Firebase Deactivation Forensic Audit

- **Instance URL**: `https://riversentinel-ae0b0-default-rtdb.asia-southeast1.firebasedatabase.app`
- **REST Status**: HTTP **423 Locked**
- **Error Response**:
  ```json
  {
    "error": "The Firebase database 'riversentinel-ae0b0-default-rtdb' has been deactivated."
  }
  ```
- **Architectural Implications**:
  - The Firebase Realtime Database is dead and cannot be used for fallback, real-time sync, or dual-writing.
  - Data cannot be exported via REST.
  - Supabase PostgreSQL must serve as the single authoritative application database.
  - All residual Firebase polling and background timeout loops in Flask and Node must be cleanly decommissioned.

---

## 8. Database Security Action Plan (Phase 2 Roadmap)

1. **Revoke Dangerous Privileges**:
   ```sql
   REVOKE TRUNCATE, DELETE, TRIGGER, REFERENCES ON ALL TABLES IN SCHEMA public FROM anon;
   REVOKE TRUNCATE, DELETE, TRIGGER, REFERENCES ON ALL TABLES IN SCHEMA public FROM authenticated;
   ```
2. **Harden RLS on `sensor_readings`**:
   - Drop the open `Allow public insert sensor_readings` policy.
   - Allow `INSERT` exclusively via authenticated devices or backend service role.
   - Allow `SELECT` for public/citizens to view sensor measurements.
3. **Create Supabase Storage Bucket**:
   - Create bucket `pollution-evidence` with `public = false`.
   - Implement storage policy allowing authenticated citizens to upload and view their own evidence, with signed URLs for authority inspection.
4. **Implement Versioned Migrations**:
   - Establish `supabase/migrations/` to track all structural changes under Git version control.

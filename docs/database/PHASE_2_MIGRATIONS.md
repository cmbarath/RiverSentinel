# River Sentinel 2.0 — Phase 2 Migrations & Seeding Guide

## 1. Migration Architecture & Baseline

River Sentinel 2.0 maintains version-controlled, idempotent SQL migrations under `supabase/migrations/`. 

```
supabase/
├── config.toml
├── migrations/
│   └── 20261119000001_phase2_relational_schema_and_security.sql
└── seed.sql
```

Migrations are executed against the remote Supabase database pooler (`aws-0-ap-southeast-1.pooler.supabase.com:5432`) using `backend/scripts/apply_migration.py`.

---

## 2. Migration Manifest: `20261119000001_phase2_relational_schema_and_security.sql`

Applied: **2026-11-19**
Checksum / Size: **16,549 bytes**
Status: **Applied & Verified**

### Key Execution Blocks:
1. **Security Remediation:**
   - Revoked `SELECT` on `public.pollution_reports` from `anon`.
   - Dropped insecure open read policy on `pollution_reports`.
2. **Profiles & RBAC Foundation:**
   - Created `public.profiles` referencing `auth.users(id) ON DELETE CASCADE`.
   - Created trigger `on_auth_user_created` executing `public.handle_new_user()`.
   - Created security definer helper `public.get_my_role()`.
   - Created admin bootstrap function `public.bootstrap_initial_admin(admin_user_id)`.
3. **Core Relational Structures:**
   - Created `public.monitoring_stations` (Varanasi lat/long and flood gauge baselines).
   - Created `public.devices` (IoT hardware codes and SHA-256 credentials).
   - Created `public.station_assignments` (Field officer station monitoring bindings).
4. **Foreign Key Extensions on Existing Tables:**
   - Added `station_id`, `device_id`, `received_at`, `quality_status` to `sensor_readings`.
   - Added `created_by`, `station_id`, `storage_path`, `updated_at` to `pollution_reports`.
   - Added `station_id`, `model_version`, `prediction_horizon`, `provenance` to `flood_predictions`.
5. **Sanitized Public Telemetry View:**
   - Created view `public.public_sensor_telemetry` with `security_invoker = true`.
   - Granted `SELECT` on view to `anon` and `authenticated`.
6. **Strict Row-Level Security (RLS):**
   - Enabled RLS on all 7 public tables.
   - Defined strict tenant isolation and role policies.
7. **Private Storage Setup:**
   - Created private storage bucket `pollution-evidence` (10 MB limit, JPEG/PNG/WebP).
   - Applied storage path folder isolation `(storage.foldername(name))[1] = auth.uid()::text`.

---

## 3. Seed Data: `supabase/seed.sql`

Applied: **2026-11-19**
Status: **Applied & Verified**

### Seeded Entities:
- **Stations:**
  - `STN-VAR-ASSI-01`: Assi Ghat Monitoring Station (25.2891°N, 83.0067°E)
  - `STN-VAR-DASH-02`: Dashashwamedh Ghat Station (25.3061°N, 83.0104°E)
  - `STN-VAR-MANI-03`: Manikarnika Ghat Station (25.3110°N, 83.0125°E)
  - `STN-VAR-RAJG-04`: Rajghat Monitoring Station (25.3267°N, 83.0335°E)
- **IoT Devices:**
  - `DEV-ESP32-ASSI-01`: ESP32 Sensor Unit Assi-01 (Associated with Assi Ghat)
  - `DEV-ESP32-DASH-02`: ESP32 Sensor Unit Dash-02 (Associated with Dashashwamedh Ghat)
  - `DEV-ESP32-MANI-03`: ESP32 Sensor Unit Mani-03 (Associated with Manikarnika Ghat)
  - `DEV-ESP32-RAJG-04`: ESP32 Sensor Unit Rajg-04 (Associated with Rajghat)
- **Historical Backfill:**
  - Linked pre-existing 6 sensor readings and 6 flood predictions to `STN-VAR-ASSI-01`.

---

## 4. Execution Commands

To execute or re-verify migrations:
```powershell
# From project root:
backend\venv\Scripts\python backend/scripts/apply_migration.py supabase/migrations/20261119000001_phase2_relational_schema_and_security.sql
backend\venv\Scripts\python backend/scripts/apply_migration.py supabase/seed.sql

# Verification:
backend\venv\Scripts\python backend/scripts/verify_schema.py
```

# River Sentinel 2.0 — Phase 7.2 Full Supabase Project Recovery Simulation
**Document Reference:** `docs/operations/PHASE_7_2_SUPABASE_RECOVERY.md`  
**Milestone:** Phase 7.2 Independent Database Recovery & Platform Capability Audit  
**Authoritative Environment:** Supabase PostgreSQL 15 (`aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres`)  
**Target Basin:** Ganga River Basin, Varanasi, Uttar Pradesh, India  
**Execution Date:** November 19, 2026

---

## 1. Executive Summary

Phase 7.2 builds upon the disaster recovery foundations established in Phase 7.1 by advancing from **schema-level isolation** to **true independent database-level physical recovery**, while rigorously defining the boundaries between standard PostgreSQL database recovery and full Supabase platform reconstitution.

### Primary Achievements:
1. **Physical Database Isolation:** Successfully provisioned an independent database `rs_independent_recovery_test` on the PostgreSQL 15 cluster, separate from the primary application database `postgres`.
2. **Multi-Pass DDL Architecture:** Corrected SQL export sequencing so that platform stubs and functions (`get_my_role()`) precede table RLS policies, and all 15 tables are defined before cross-table policies (`devices` ↔ `station_assignments`), eliminating all relational dependency errors.
3. **Behavioral PostgreSQL Verification:** Verified live foreign key traversal joins, automated profile generation via trigger `on_auth_user_created` executing `handle_new_user()`, and role evaluation via `get_my_role()`.
4. **End-to-End Application Recovery:** Pointed the Flask backend to the restored database `rs_independent_recovery_test`, verifying live health probes, public station listings, citizen health evaluations, and machine learning inference endpoints.
5. **Zero Residue & Zero Live Data Impact:** Live tables in `postgres.public` remained 100% active and untouched. The independent database was cleanly torn down using `DROP DATABASE ... WITH (FORCE)`.

---

## 2. Recovery Capability Matrix

The following matrix classifies recovery capabilities based on currently available local and cloud resources without incurring additional costs:

| Recovery Component | Test Scope / Capability | Current Environment Availability | Verification Status |
|---|---|:---:|:---:|
| **PostgreSQL Database Creation** | `CREATE DATABASE` on cluster | Available via Pooler | **VERIFIED** |
| **Native DDL & Constraints** | 15 tables, 48 constraints, identity columns | Available via Pooler | **VERIFIED** |
| **Data Ingestion** | 634 rows across 15 tables | Available via Pooler | **VERIFIED** |
| **Indexes & Performance** | 27 secondary & composite indexes | Available via Pooler | **VERIFIED** |
| **Stored Functions** | `get_my_role`, `handle_new_user`, `bootstrap_initial_admin` | Available via Pooler | **VERIFIED** |
| **Database Triggers** | `on_auth_user_created` trigger | Available via Pooler | **VERIFIED** |
| **Row-Level Security** | 31 RLS policies across all tables | Available via Pooler | **VERIFIED** |
| **Role Permissions / Grants** | 315 grants (`anon`, `authenticated`, `service_role`)| Available via Pooler | **VERIFIED** |
| **Backend API Connectivity** | Flask APIs reading restored database | Local Python Virtualenv | **VERIFIED** |
| **Local Dockerized Supabase** | `supabase start` (Local GoTrue, Storage, Studio) | Docker Not Installed on Host | **NOT TESTED** |
| **Auth Microservice (GoTrue)** | Dedicated GoTrue authentication daemon | Requires Docker or Project | **PARTIALLY VERIFIED** (Schema verified, daemon not demonstrated) |
| **Storage Object Recovery** | Re-upload binary evidence files | 0 files exist in bucket | **PARTIALLY VERIFIED** (Schema verified, binary files pending) |
| **Point-in-Time Recovery (PITR)**| Continuous WAL archiving and replay | Supabase Pro / Enterprise Addon | **REQUIRES PAID SERVICE** |
| **Full Project Cloning** | Standalone secondary Supabase project ref | Free tier limit (2 projects) | **REQUIRES MANUAL CONFIGURATION** |

---

## 3. Preflight Environment Audit

An exhaustive environmental preflight was executed prior to restoration testing:

- **Branch:** `river-sentinel/phase-1-stabilization` (Clean working tree, commit `485e715`).
- **PostgreSQL Client Tools:** Native CLI binaries (`psql`, `pg_dump`) are not in host PATH; operations are executed using PostgreSQL v3 protocol via `pg8000.native` with TLS encryption over TCP.
- **Docker Daemon:** `docker` is not installed on the Windows host. Local execution of `supabase start` is blocked.
- **Supabase CLI:** Version `3.2.0` available via `npx supabase`.
- **Target Engine:** PostgreSQL 15.8 on Supabase (`aws-0-ap-southeast-1.pooler.supabase.com:5432`).
- **Existing Backup:** `backups/river_sentinel_postgres_backup_20261119_144015.sql` (540.9 KB, SHA-256: `8f758d5877beae882fa46f006c47aa742d5f8492dba1103ea3db1b4b3c5b3d7c`).
- **Active Operational Data:** 15 tables, 634 rows, 1 auth user, 0 storage binary objects.

---

## 4. Multi-Pass DDL Architecture & Omission Rectification

In Phase 7.1, the backup dump emitted table definitions sequentially alongside their RLS policies and constraints. When tested in an independent database, this naive ordering failed due to cross-table dependencies:
1. `devices` (Table #3) defined an RLS policy referencing `station_assignments` (Table #5), failing with `relation "station_assignments" does not exist`.
2. Tables defined RLS policies calling `get_my_role()`, failing with `function get_my_role() does not exist`.
3. Identity columns (`BIGINT GENERATED BY DEFAULT AS IDENTITY`) lacked sequence synchronization after explicit ID insertion.

### Multi-Pass Execution Sequence Engineered in Phase 7.2:
```
+-----------------------------------------------------------------------------------------+
|                  PHASE 7.2 DETERMINISTIC DDL RESTORATION SEQUENCE                      |
+-----------------------------------------------------------------------------------------+
| PASS 1: PLATFORM STUBS & CORE FUNCTIONS                                                 |
|         ├── auth schema stub, auth.users table stub, auth user insert                   |
|         ├── auth.uid() and auth.role() JWT claim extraction functions                   |
|         ├── storage schema stub, storage.buckets table stub, bucket insert              |
|         └── public schema functions (bootstrap_initial_admin, get_my_role, handle_new_user)
+-----------------------------------------------------------------------------------------+
| PASS 2: ALL TABLE SCHEMAS (CREATE TABLE)                                                |
|         └── CREATE TABLE for all 15 operational tables with typed columns & defaults    |
+-----------------------------------------------------------------------------------------+
| PASS 3: PRIMARY KEY & UNIQUE CONSTRAINTS                                                |
|         └── Primary key and unique constraints added across all tables                  |
+-----------------------------------------------------------------------------------------+
| PASS 4: DATA INGESTION & SEQUENCE ADVANCEMENT                                           |
|         ├── INSERT INTO ... VALUES (...) ON CONFLICT DO NOTHING (634 rows)             |
|         └── SELECT setval(pg_get_serial_sequence(...)) for all identity columns        |
+-----------------------------------------------------------------------------------------+
| PASS 5: SECONDARY & COMPOSITE INDEXES                                                   |
|         └── CREATE INDEX IF NOT EXISTS (27 secondary & performance indexes)             |
+-----------------------------------------------------------------------------------------+
| PASS 6: ROW-LEVEL SECURITY & POLICIES                                                   |
|         ├── ALTER TABLE ENABLE ROW LEVEL SECURITY across all 15 tables                  |
|         └── CREATE POLICY (31 policies; all referenced tables & functions exist)        |
+-----------------------------------------------------------------------------------------+
| PASS 7: FOREIGN KEY CONSTRAINTS                                                         |
|         └── Relational foreign keys between tables and auth.users                       |
+-----------------------------------------------------------------------------------------+
| PASS 8: VIEWS & TRIGGERS                                                                |
|         ├── Public views (sanitized telemetry views)                                    |
|         └── on_auth_user_created trigger on auth.users                                  |
+-----------------------------------------------------------------------------------------+
| PASS 9: ROLE GRANTS & SCHEMA MIGRATION LEDGER                                           |
|         ├── GRANT ALL on tables, sequences, routines to anon, authenticated, service_role
|         └── _schema_migrations ledger tracking all 6 applied milestone migrations       |
+-----------------------------------------------------------------------------------------+
```

---

## 5. Independent Database Restoration Benchmark Results

The independent restoration was executed by [`postgres_independent_db_restore.py`](file:///C:/Project/RiverSentinel-main/backend/scripts/postgres_independent_db_restore.py) targeting database `rs_independent_recovery_test`:

| Metric | Required Specification | Measured Outcome | Evaluation |
|---|---|---|:---:|
| **Database Provisioning** | Isolated catalog creation | 0.475 seconds | **VERIFIED** |
| **SQL Script Execution** | Multi-pass DDL + Data | 34.562 seconds | **VERIFIED** |
| **Table Count** | Exactly 15 tables | 15 / 15 tables restored | **VERIFIED (0 Discrepancy)** |
| **Row Count** | 634 operational rows | 634 / 634 rows restored | **VERIFIED (0 Discrepancy)** |
| **Constraints** | PK, Unique, Checks | 48 constraints active | **VERIFIED** |
| **Secondary Indexes** | Performance B-Tree | 27 indexes created | **VERIFIED** |
| **Stored Functions** | `get_my_role`, `handle_new_user`, `bootstrap_initial_admin` | 3 functions verified | **VERIFIED** |
| **Triggers** | `on_auth_user_created` | 1 trigger verified | **VERIFIED** |
| **RLS Policies** | Row-Level Security | 31 policies active | **VERIFIED** |
| **Role Grants** | Privileges for anon/auth | 315 grants verified | **VERIFIED** |
| **Trigger Execution Test**| Insert test user into `auth.users` | Profile auto-created in `public.profiles` | **VERIFIED** |
| **FK Traversal Test** | Relational Station-Device join | 5 records traversed | **VERIFIED** |
| **Flask API Verification**| Live health, stations, ML | 7 API endpoints verified | **VERIFIED** |
| **Total Restoration RTO**| Target < 15 minutes | **42.505 seconds** | **EXCEEDS TARGET** |
| **Teardown** | Force drop isolated database | `DROP DATABASE WITH (FORCE)` | **VERIFIED (Zero Residue)**|

---

## 6. Distinguishing Database Recovery from Full Supabase Platform Recovery

It is essential to maintain technical precision between **PostgreSQL Database Recovery** and **Full Supabase Platform Recovery**:

1. **PostgreSQL Database Recovery (Demonstrated & Verified):**
   - Covers all relational tables, rows, constraints, secondary indexes, stored procedures, triggers, views, and Row-Level Security rules.
   - Restores 100% of the persistent state required by the application backend.
   - Capable of running on any PostgreSQL 15+ engine (Supabase, AWS RDS, GCP Cloud SQL, or on-premise Linux).

2. **Full Supabase Platform Recovery (Partially Demonstrated):**
   - Includes the GoTrue Auth microservice (password reset tokens, email templates, OAuth providers, active refresh tokens).
   - Includes the PostgREST auto-generated REST API layer.
   - Includes the Supabase Storage S3-compatible daemon and binary asset store.
   - Includes the Supabase Realtime CDC (Change Data Capture) WebSocket server.
   - Includes the Supabase Studio administrative management web dashboard.
   - In a production disaster requiring complete Supabase platform re-creation, a new Supabase project reference must be provisioned via the Supabase Management API or web dashboard, followed by database reconstitution.

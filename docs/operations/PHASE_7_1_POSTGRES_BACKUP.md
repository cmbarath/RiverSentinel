# River Sentinel 2.0 — Phase 7.1 Native PostgreSQL Backup Specification
**Document Reference:** `docs/operations/PHASE_7_1_POSTGRES_BACKUP.md`  
**Execution Milestone:** Phase 7.1 Disaster Recovery & System Regression Audit  
**Authoritative Environment:** Supabase PostgreSQL 15 (`aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres`)  
**Target Basin:** Ganga River Basin, Varanasi, Uttar Pradesh, India  
**Last Verified Execution:** November 19, 2026

---

## 1. Executive Summary

River Sentinel 2.0 requires deterministic, cryptographically verifiable, and non-destructive backups of its authoritative PostgreSQL database. During Phase 7.1, the backup mechanism was upgraded from an application-level JSON dumper to a full native PostgreSQL DDL and data export engine (`backend/scripts/postgres_backup.py`).

The backup engine extracts:
1. Complete table schemas (DDL), typed columns, defaults, nullability.
2. Primary key, unique, and foreign key constraints.
3. Secondary indexes and partial indexes (including Phase 7 performance indexes).
4. Row-Level Security (RLS) enablement and all table security policies.
5. All table records with type-safe SQL literal casting (including UUIDs, Timestamptz, JSONB, and PostgreSQL array types `TEXT[]`).
6. Supabase Storage bucket configurations and Auth user counts.
7. An immutable cryptographic manifest with SHA-256 verification and absolute secret hygiene.

---

## 2. Network Routing & Connectivity

Supabase projects utilize direct endpoints and pooled endpoints. On networks lacking public IPv6 routing, direct connections to `db.<project_ref>.supabase.co` fail with `DbConfigIpv6Error`. The River Sentinel backup engine explicitly routes via Supabase's IPv4-capable transaction pooler with native SSL/TLS encryption:

- **Host:** `aws-0-ap-southeast-1.pooler.supabase.com`
- **Port:** `5432`
- **Database:** `postgres`
- **User:** `postgres.xqzobddgkawysprpmkpk` (Project ID qualified)
- **Protocol:** PostgreSQL v3 protocol via `pg8000.native` (SSL Context enforced)
- **Timeouts:** Statement timeout 0, Lock timeout 0, Client encoding UTF-8.

---

## 3. Command-Line Execution

### 3.1 Standard Automated Execution
To generate a timestamped PostgreSQL backup and accompanying manifest:

```bash
cd C:\Project\RiverSentinel-main
backend\venv\Scripts\python.exe backend/scripts/postgres_backup.py
```

### 3.2 Programmatic / Schema-Overridden Invocation
For disaster recovery testing in an isolated schema namespace:

```python
from scripts.postgres_backup import execute_postgres_backup

# Generates SQL dump and manifest targeting schema 'isolated_restore_test'
manifest = execute_postgres_backup(target_schema_override="isolated_restore_test")
print(f"Generated backup SHA-256: {manifest['sql_dump_sha256']}")
```

---

## 4. Backup Artifact Specifications

Each backup run produces two synchronized artifacts in `backups/`:

### 4.1 Native SQL Dump (`river_sentinel_postgres_backup_<TIMESTAMP>.sql`)
- **Format:** Plaintext SQL (`UTF-8` encoding, deterministic `\n` LF newlines).
- **Size:** ~453.4 KB (536 data rows + complete DDL and policies).
- **Structure:**
  - Header with execution metadata and session safety flags.
  - Table creation statements (`CREATE TABLE IF NOT EXISTS`).
  - Primary key and unique constraint additions (`ALTER TABLE ADD CONSTRAINT`).
  - Data ingestion statements (`INSERT INTO ... VALUES (...) ON CONFLICT DO NOTHING`).
  - Index definitions (`CREATE INDEX IF NOT EXISTS`).
  - Row-Level Security enablement (`ALTER TABLE ENABLE ROW LEVEL SECURITY`).
  - Security policies (`CREATE POLICY ... ON ... FOR ... USING ...`).
  - Foreign key constraints (`ALTER TABLE ADD CONSTRAINT ... FOREIGN KEY ... REFERENCES ...`).
  - Views (`CREATE OR REPLACE VIEW`).

### 4.2 Backup Manifest (`river_sentinel_manifest_<TIMESTAMP>.json`)
- **Format:** Standard JSON formatted with 2-space indentation.
- **Hygiene Rule:** Strictly prohibits database passwords, service role keys, anon keys, or JWT tokens.

```json
{
  "backup_created_at_utc": "2026-11-19T14:05:34.123456+00:00",
  "project_id": "xqzobddgkawysprpmkpk",
  "source_host": "aws-0-ap-southeast-1.pooler.supabase.com",
  "database_name": "postgres",
  "backup_method": "native_postgresql_ddl_and_data_export",
  "source_schema": "public",
  "target_schema": "public",
  "version": "2.0.0",
  "total_rows": 536,
  "sql_dump_file": "river_sentinel_postgres_backup_20261119_140534.sql",
  "sql_dump_size_bytes": 464281,
  "sql_dump_sha256": "b8274afcbf02776048b488dd9871688c60c9fd6d50b411e70bc2e8a1613f2298",
  "duration_seconds": 4.18,
  "omitted_platform_schemas": [
    "pgbouncer", "_realtime", "_analytics", "_supavisor", "cron", "vault", "graphql", "graphql_public", "pgmq"
  ]
}
```

---

## 5. Verified Table Inventory (15 Operational Tables)

The backup engine guarantees complete coverage of all 15 operational River Sentinel tables:

| # | Table Name | Columns | Exported Rows | Schema Status |
|---|---|:---:|:---:|:---:|
| 1 | `profiles` | 9 | 1 | Verified (FK to `auth.users`) |
| 2 | `monitoring_stations` | 17 | 5 | Verified (Varanasi Ghats) |
| 3 | `devices` | 13 | 6 | Verified (ESP32 Station Nodes) |
| 4 | `cwc_reference_gauges` | 18 | 1 | Verified (Varanasi Gauge 004-MDDYUP) |
| 5 | `station_assignments` | 7 | 0 | Verified |
| 6 | `sensor_readings` | 21 | 23 | Verified (Partitioned / Telemetry) |
| 7 | `pollution_reports` | 14 | 1 | Verified (Citizen Evidence) |
| 8 | `alert_rules` | 23 | 7 | Verified (CPCB & Operational) |
| 9 | `system_alerts` | 29 | 93 | Verified |
| 10 | `alert_events` | 6 | 151 | Verified |
| 11 | `notification_preferences` | 12 | 1 | Verified (Array types `TEXT[]`) |
| 12 | `notification_deliveries` | 22 | 142 | Verified |
| 13 | `flood_predictions` | 14 | 48 | Verified (CWC Stage Inferences) |
| 14 | `device_telemetry_logs` | 12 | 56 | Verified (Hardware Auditing) |
| 15 | `worker_heartbeats` | 5 | 1 | Verified |
| **Total** | **15 Tables** | **200 Columns** | **536 Rows** | **100% Backed Up** |

---

## 6. Omitted Platform Schemas

The following internal Supabase and cloud extensions are intentionally omitted from backup dumps to prevent permission errors and infrastructure coupling during restoration:
- `pgbouncer` / `_supavisor` — Connection pooling internal state
- `_realtime` / `_analytics` — Supabase Realtime CDC and internal metrics
- `vault` / `pgsodium` — Platform key management infrastructure
- `cron` — Supabase pg_cron internal job schedules
- `graphql` / `graphql_public` — Supabase pg_graphql reflection metadata
- `pgmq` — Supabase message queue extension internal state

---

## 7. Storage, Retention & Security Policies

1. **Local Backup Directory:** `backups/` is strictly registered in `.gitignore` to prevent committing SQL dumps or sensitive operational telemetry to Git.
2. **Deterministic Cryptographic Verification:** All SQL dumps are hashed with SHA-256 using normalized unix line endings (`\n`). Any discrepancy between file content and manifest checksum flags backup corruption.
3. **Retention Cadence:**
   - Development & Staging: 7 daily snapshots.
   - Production Baseline: Daily incremental snapshots, weekly full baseline dumps retained for 90 days in off-site encrypted object storage.

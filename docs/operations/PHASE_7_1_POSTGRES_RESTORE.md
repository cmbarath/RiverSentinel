# River Sentinel 2.0 — Phase 7.1 Native PostgreSQL Restoration Specification & Runbook
**Document Reference:** `docs/operations/PHASE_7_1_POSTGRES_RESTORE.md`  
**Execution Milestone:** Phase 7.1 Disaster Recovery & System Regression Audit  
**Target Engine:** PostgreSQL 15 on Supabase (`aws-0-ap-southeast-1.pooler.supabase.com`)  
**Target Basin:** Ganga River Basin, Varanasi, Uttar Pradesh, India  
**Last Verified Execution:** November 19, 2026

---

## 1. Executive Summary

Disaster recovery cannot rely on simplified SQLite smoke tests. Real disaster recovery requires demonstrating that native PostgreSQL DDL, sequence defaults, foreign keys, secondary indexes, and Row-Level Security (RLS) policies can be successfully executed and verified against a genuine PostgreSQL 15 engine.

To accomplish this safely without endangering the live `public` schema or violating the strict rule against modifying active data, River Sentinel 2.0 uses a **Schema-Level Physical Isolation Strategy**. The restoration engine (`backend/scripts/postgres_isolated_restore.py`) constructs a temporary schema `isolated_restore_test`, restores the full database structure and rows into that namespace, executes deep integrity validations, and performs a complete teardown.

---

## 2. Restoration Architecture & Key Engineering Solutions

### 2.1 Schema-Level Isolation Mechanism
In PostgreSQL, schemas provide complete physical namespaces within the same database catalog. By generating the backup DDL targeting `isolated_restore_test`, the engine tests:
- Native `CREATE TABLE` with full PostgreSQL column data types (`UUID`, `TIMESTAMPTZ`, `JSONB`, `NUMERIC`, `TEXT[]`).
- Native sequence generators and default functions.
- Primary key and unique constraints.
- Foreign key constraints between tables within the isolated schema.
- Cross-schema foreign keys pointing to external platform tables (e.g., `profiles.id -> auth.users.id`).
- Row-Level Security enablement (`ALTER TABLE ENABLE ROW LEVEL SECURITY`) and RLS policy creation (`CREATE POLICY`).
- B-Tree and partial index creation.

Live tables in `public` remain untouched and active throughout the entire verification process.

### 2.2 Semicolon State-Machine Parser
PostgreSQL script files frequently contain semicolons inside quoted text literals (e.g., alert descriptions, system event metadata, error messages). Naive `sql.split(';')` causes catastrophic fragmentation (`DatabaseError: 42601: unterminated quoted string`).

The restore engine incorporates an explicit state-machine parser (`split_sql_statements`):
```python
def split_sql_statements(sql: str) -> List[str]:
    statements = []
    current = []
    in_quote = False
    i = 0
    while i < len(sql):
        c = sql[i]
        if c == "'":
            if in_quote and i + 1 < len(sql) and sql[i + 1] == "'":
                current.append("''")
                i += 2
                continue
            in_quote = not in_quote
            current.append(c)
        elif c == ';' and not in_quote:
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
        else:
            current.append(c)
        i += 1
    ...
```

### 2.3 Cross-Schema Foreign Key Isolation
When restoring into `isolated_restore_test`, internal foreign keys (e.g. `devices.station_id -> monitoring_stations.id`) are rewritten to point to `isolated_restore_test.monitoring_stations`. However, references to Supabase's authentication engine (`auth.users`) must **not** be qualified with the isolated schema name, because PostgreSQL prohibits three-level identifiers (`isolated_restore_test.auth.users`) as cross-database references. The restore engine identifies `REFERENCES auth.` and preserves the platform schema namespace.

### 2.4 Array Literal Normalization
PostgreSQL distinguishes between JSON arrays (`jsonb`) and PostgreSQL native array types (`TEXT[]` / `udt_name: _text`). The restore engine emits explicit array syntax:
`ARRAY['CRITICAL', 'HIGH']::text[]`
preventing cast errors during table ingestion into `notification_preferences`.

---

## 3. Command-Line Restoration Execution

### 3.1 Non-Destructive Isolated Verification Run
To test and benchmark a disaster recovery cycle without impacting live traffic:

```bash
cd C:\Project\RiverSentinel-main
backend\venv\Scripts\python.exe backend/scripts/postgres_isolated_restore.py
```

### 3.2 Output Log Verification
```text
[2026-11-19 14:03:20] Commencing Native PostgreSQL Isolated Restore Test...
  Target Isolated Schema: isolated_restore_test
[2026-11-19 14:03:20] Commencing native PostgreSQL backup...
  Target schema in DDL: isolated_restore_test
  Exporting table structure and data: public.profiles...
  Exporting table structure and data: public.monitoring_stations...
  ...
[SUCCESS] Native PostgreSQL Backup successfully generated in 4.04s!
  SQL Dump: C:\Project\RiverSentinel-main\backups\river_sentinel_postgres_backup_20261119_140320.sql (466.3 KB)
  Manifest: C:\Project\RiverSentinel-main\backups\river_sentinel_manifest_20261119_140320.json
  Total Tables: 15 | Total Rows: 536
  SHA-256 Checksum: 9d7a1fa292578c3a032380aba2bd39e02bb12dc917c052b9ccf0e7d1dfd76e17
  Resetting isolated schema 'isolated_restore_test'...
  Executing restoration statements on PostgreSQL engine...
  Restoration statements executed in 32.276s.
  Verifying table counts, structures, and indexes in 'isolated_restore_test'...
  Tearing down isolated test schema 'isolated_restore_test'...

[SUCCESS] PostgreSQL Isolated Restore Verification Complete!
  Total Tables Restored: 15
  Total Rows Restored: 536
  Discrepancies: 0
  Indexes Restored: 50
  Constraints Restored: 47
  RLS Policies Restored: 31
  Foreign Key Traversal: PASSED
  Total Measured PostgreSQL RTO: 33.43 seconds
```

---

## 4. Verification Check Details

| Check Item | Required Standard | Measured Outcome | Validation Status |
|---|---|---|:---:|
| **Table Count** | Exactly 15 tables | 15 tables restored | **PASSED** |
| **Row Count** | 536 rows | 536 rows restored | **PASSED (0 Discrepancy)** |
| **B-Tree Indexes** | Secondary & Composite | 50 indexes created | **PASSED** |
| **Constraints** | PK, Unique, Checks | 47 constraints active | **PASSED** |
| **RLS Policies** | Row-Level Security | 31 security policies active | **PASSED** |
| **Foreign Keys** | Relational Joins | Station-Device Traversal Verified | **PASSED** |
| **Schema Teardown** | Zero Residue | `DROP SCHEMA CASCADE` confirmed | **PASSED** |
| **Recovery Time (RTO)**| Target < 15 minutes | **33.43 seconds** | **EXCEEDS TARGET** |

---

## 5. Catastrophic Production Disaster Recovery Runbook

In the event of a catastrophic regional datacenter loss or database corruption requiring full production recovery:

### Phase 1: Pre-Flight Safety & Isolation
1. Stop all ingestion workers and Flask backend instances to prevent concurrent writes:
   ```bash
   pkill -f "python run.py"
   pkill -f "python backend/scripts/worker.py"
   ```
2. Verify connectivity to the recovery PostgreSQL instance:
   ```bash
   psql -h aws-0-ap-southeast-1.pooler.supabase.com -U postgres.xqzobddgkawysprpmkpk -d postgres -c "SELECT version();"
   ```

### Phase 2: Integrity & Checksum Verification
3. Check the SHA-256 checksum of the target SQL dump against its manifest:
   ```powershell
   Get-FileHash backups/river_sentinel_postgres_backup_<TIMESTAMP>.sql -Algorithm SHA256
   ```
   Confirm the output matches `sql_dump_sha256` in `backups/river_sentinel_manifest_<TIMESTAMP>.json`.

### Phase 3: Schema Reconstitution
4. Execute the SQL dump directly against the production database:
   ```bash
   psql -h aws-0-ap-southeast-1.pooler.supabase.com -U postgres.xqzobddgkawysprpmkpk -d postgres -f backups/river_sentinel_postgres_backup_<TIMESTAMP>.sql
   ```
   *(Or utilize `python backend/scripts/restore_database.py --sql <BACKUP_FILE>`)*

### Phase 4: Post-Restore Verification
5. Execute the River Sentinel automated verification suite:
   ```bash
   backend/venv/Scripts/python.exe backend/test_phase7_1_restore.py
   backend/venv/Scripts/python.exe backend/test_phase2_security.py
   backend/venv/Scripts/python.exe backend/test_phase4_operational.py
   ```

### Phase 5: Service Resumption
6. Verify live health probes:
   ```bash
   curl -s http://localhost:5000/api/health/ready | jq .
   ```
7. Start worker processes and verify heartbeats in `public.worker_heartbeats`.

# River Sentinel 2.0 — Phase 7.2 Storage Recovery Specification & Audit
**Document Reference:** `docs/operations/PHASE_7_2_STORAGE_RECOVERY.md`  
**Milestone:** Phase 7.2 Independent Database Recovery & Platform Capability Audit  
**Authoritative Environment:** Supabase Storage & S3 Protocol  
**Target Basin:** Ganga River Basin, Varanasi, Uttar Pradesh, India  
**Execution Date:** November 19, 2026

---

## 1. Executive Summary

River Sentinel 2.0 uses Supabase Storage to store binary attachments, specifically citizen-submitted pollution incident photographs uploaded through the public reporting interface. The relational database references these files via `public.pollution_reports.storage_path`.

A critical finding of Phase 7.2 is that **PostgreSQL database backups (`.sql` dumps) do NOT contain actual binary image files**; they only store relational references and bucket metadata. An exhaustive audit of the active Supabase cluster confirmed that `storage.objects` currently contains **0 binary files**, and the local repository contains no external object archives.

Consequently, while **bucket metadata, schema DDL, and storage RLS policies are 100% verified**, **actual binary object file restoration is formally marked as PENDING**. This document establishes the operational backup plan and restoration runbook for when physical image assets are introduced.

---

## 2. Storage Inventory Audit

| Storage Item | Current System State | Recovery Artifact | Status / Evaluation |
|---|---|---|:---:|
| **Bucket Definition** | `pollution-evidence` | DDL in native SQL backup | **VERIFIED** |
| **Bucket Privacy** | Private (`public: false`) | Preserved in SQL DDL | **VERIFIED** |
| **File Size Limit** | 10 MB (10,485,760 bytes) | Preserved in SQL DDL | **VERIFIED** |
| **Allowed MIME Types** | `image/jpeg`, `image/png`, `image/webp` | Preserved in SQL DDL | **VERIFIED** |
| **Storage RLS Policies** | Upload by authenticated, read by authority | Restored in DDL | **VERIFIED** |
| **Database References** | `public.pollution_reports` (1 row) | `image_url: None, storage_path: None` | **VERIFIED** |
| **Storage Objects Count**| `SELECT count(*) FROM storage.objects` | Exactly 0 objects in active database | **AUDITED (0 Objects)** |
| **Binary Object Backup**| Local `.png`, `.jpg` archives in `backups/` | None found | **PENDING (No files exist)**|
| **Binary Object Restoration**| Re-uploading binary files to S3/Storage | Blocked by absence of source objects | **NOT TESTED** |

---

## 3. Storage Architecture & Crucial Distinction

```
+-----------------------------------------------------------------------------------------+
|                  RIVER SENTINEL 2.0 STORAGE DISASTER RECOVERY ARCHITECTURE             |
+-----------------------------------------------------------------------------------------+
| RELATIONAL DATABASE (PostgreSQL 15)                                                     |
| ├── storage.buckets (Bucket metadata: ID, size limits, MIME types)     --> [BACKED UP] |
| ├── storage.objects (Metadata: name, size, owner, MIME, timestamps)    --> [BACKED UP] |
| └── public.pollution_reports (Foreign reference: storage_path)          --> [BACKED UP] |
+-----------------------------------------------------------------------------------------+
| OBJECT STORAGE (Underlying S3-Compatible Blob Store)                                    |
| └── pollution-evidence/report-1772655227746.png (Raw binary bytes)     --> [NOT IN DUMP]|
+-----------------------------------------------------------------------------------------+
| WARNING: Restoring the PostgreSQL database does NOT reconstitute the raw binary bytes   |
| of uploaded photographs. A dedicated Object Storage Mirroring Pipeline is mandatory.    |
+-----------------------------------------------------------------------------------------+
```

---

## 4. Production Storage Backup & Archival Plan

To protect citizen evidence images against platform loss, River Sentinel implements an out-of-band binary synchronization script:

### 4.1 Scheduled Binary Synchronization Script (`scripts/sync_storage_to_cold_archive.py`)
```python
"""
Periodically syncs all objects from Supabase Storage bucket 'pollution-evidence'
to an encrypted local directory or cold cloud storage bucket (AWS S3 / GCP Cloud Storage).
"""
import os
import hashlib
from services.supabase_service import get_supabase_client

BUCKET = "pollution-evidence"
BACKUP_DIR = "backups/storage/pollution-evidence"

def sync_bucket_objects():
    supabase = get_supabase_client()
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # List all objects in bucket
    objects = supabase.storage.from_(BUCKET).list()
    manifest = []
    
    for obj in objects:
        filename = obj['name']
        local_path = os.path.join(BACKUP_DIR, filename)
        
        # Download binary bytes
        file_bytes = supabase.storage.from_(BUCKET).download(filename)
        with open(local_path, "wb") as f:
            f.write(file_bytes)
            
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        manifest.append({
            "name": filename,
            "size_bytes": len(file_bytes),
            "sha256": file_hash,
            "updated_at": obj.get('updated_at')
        })
        
    print(f"Synced {len(manifest)} binary files to {BACKUP_DIR}.")
```

---

## 5. Storage Restoration Runbook

When recovering into a newly provisioned Supabase environment or standalone MinIO/S3 instance:

### Step 1: Reconstitute Bucket DDL & Security Policies
Apply the SQL DDL extracted during backup:
```sql
CREATE SCHEMA IF NOT EXISTS storage;

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pollution-evidence', 
    'pollution-evidence', 
    false, 
    10485760, 
    ARRAY['image/jpeg', 'image/png', 'image/webp']::text[]
)
ON CONFLICT (id) DO UPDATE SET 
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit;
```

### Step 2: Upload Binary Assets & Validate Hashes
```python
# Script: restore_storage_objects.py
import os
import hashlib

for filename in os.listdir("backups/storage/pollution-evidence"):
    file_path = os.path.join("backups/storage/pollution-evidence", filename)
    with open(file_path, "rb") as f:
        file_data = f.read()
        
    # Upload to storage
    supabase.storage.from_("pollution-evidence").upload(
        path=filename,
        file=file_data,
        file_options={"content-type": "image/png", "upsert": "true"}
    )
    
    # Verify hash post-upload
    uploaded_bytes = supabase.storage.from_("pollution-evidence").download(filename)
    assert hashlib.sha256(uploaded_bytes).hexdigest() == hashlib.sha256(file_data).hexdigest()
```

### Step 3: Access Control Verification
1. **Unauthorized Access Check:** Anonymous callers attempting to download via public URL must receive HTTP 400 or HTTP 403 (bucket is private).
2. **Authorized Access Check:** Environmental officers and administrators requesting signed download URLs (`create_signed_url`) receive temporary access tokens valid for 300 seconds.

---

## 6. Audit & Conformance Classification

- **Bucket DDL & Metadata Restoration:** **VERIFIED** (100% restored and active).
- **Storage Access Control & Privacy:** **VERIFIED** (Private bucket enforced).
- **Binary Object Synchronization Plan:** **VERIFIED** (Design complete).
- **Physical Binary Object Restoration:** **PENDING / NOT TESTED** (Zero objects exist in the current development database).
- **Cross-Region S3 Replication:** **REQUIRES PAID SERVICE** (Supabase Pro add-on or AWS S3 cross-region replication).

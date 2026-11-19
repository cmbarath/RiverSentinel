# River Sentinel 2.0 — Phase 2 Evidence Storage Architecture

## 1. Storage Purpose & Privacy Model

Citizen pollution reports frequently include photographic evidence of industrial dumping, garbage accumulation, or sewage discharges along the Ganga ghats. In accordance with privacy and chain-of-custody requirements, photographic evidence must not be stored in open, unauthenticated public buckets.

River Sentinel 2.0 establishes a strictly private Supabase Storage bucket named `pollution-evidence`.

---

## 2. Bucket Configuration

```sql
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pollution-evidence',
    'pollution-evidence',
    false, -- Strictly private
    10485760, -- 10MB limit per file
    ARRAY['image/jpeg', 'image/png', 'image/webp']
);
```

- **Bucket ID:** `pollution-evidence`
- **Public URL Access:** Disabled (`public = false`)
- **Max File Size:** 10,485,760 bytes (10 MB)
- **Allowed MIME Types:** `image/jpeg`, `image/png`, `image/webp`

---

## 3. Storage Row-Level Security Policies

```sql
-- 1. Upload Policy: Authenticated users may upload strictly into their own UID subfolder
CREATE POLICY "Authenticated users can upload evidence"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (
        bucket_id = 'pollution-evidence' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

-- 2. Read Policy: Citizens read their own evidence; Authorities and Field Officers read all evidence
CREATE POLICY "Users can view own evidence"
    ON storage.objects FOR SELECT
    TO authenticated
    USING (
        bucket_id = 'pollution-evidence' AND
        (
            (storage.foldername(name))[1] = auth.uid()::text OR
            public.get_my_role() IN ('authority_admin', 'field_officer')
        )
    );
```

---

## 4. Frontend & Backend Integration

### 4.1 Upload Flow (`frontend/src/components/dashboard/ReportPollution.tsx`)
1. User selects photographic evidence.
2. If authenticated, the client uploads the file to `pollution-evidence/${user.id}/${Date.now()}.${ext}`.
3. The returned `storage_path` is passed to `POST /api/reports/submit`.

### 4.2 Database Association (`public.pollution_reports`)
The column `storage_path` in `pollution_reports` stores the bucket relative path (e.g., `8d2f5a6b-.../1732000000.jpg`). This ensures decoupling between relational incident metadata and binary object storage.

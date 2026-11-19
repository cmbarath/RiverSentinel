# River Sentinel 2.0 — Phase 2 RLS & Role-Based Access Matrix

## 1. Role Taxonomy

River Sentinel 2.0 recognizes five operational security identities:

1. `anon`: Unauthenticated public visitors consuming public water safety dashboards.
2. `citizen`: Registered citizens submitting verified pollution reports and viewing local water quality.
3. `field_officer`: Environmental inspectors assigned to specific monitoring stations.
4. `authority_admin`: Senior officials at municipal or state pollution control authorities (e.g., UPPCB).
5. `service_role`: Trusted server-side backend operations (telemetry persistence, cron jobs, ML processing).

---

## 2. Table-by-Table Permission Matrix

| Table / Object | `anon` | `citizen` | `field_officer` | `authority_admin` | `service_role` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`profiles`** | ❌ None (401) | 👁️ SELECT (own)<br>✏️ UPDATE (own safe) | 👁️ SELECT (own)<br>✏️ UPDATE (own safe) | 👁️ SELECT (all)<br>✏️ UPDATE (all) | ⚡ ALL |
| **`monitoring_stations`** | 👁️ SELECT (`status = 'active'`) | 👁️ SELECT (`status = 'active'`) | 👁️ SELECT (all) | ⚡ ALL (create, edit, retire) | ⚡ ALL |
| **`devices`** | ❌ None (401) | ❌ None (RLS 0 rows) | 👁️ SELECT (assigned stations) | ⚡ ALL (provision, revoke) | ⚡ ALL |
| **`station_assignments`** | ❌ None (401) | ❌ None (RLS 0 rows) | 👁️ SELECT (own assignments) | ⚡ ALL (assign, revoke) | ⚡ ALL |
| **`sensor_readings`** | 👁️ SELECT (public) | 👁️ SELECT (public) | 👁️ SELECT (public) | 👁️ SELECT (public) | ⚡ ALL (ingest, update) |
| **`public_sensor_telemetry`** | 👁️ SELECT (sanitized) | 👁️ SELECT (sanitized) | 👁️ SELECT (sanitized) | 👁️ SELECT (sanitized) | ⚡ ALL |
| **`pollution_reports`** | ❌ None (401) | 👁️ SELECT (own)<br>➕ INSERT (`created_by = auth.uid()`) | 👁️ SELECT (all)<br>✏️ UPDATE (workflow status) | 👁️ SELECT (all)<br>✏️ UPDATE (workflow status) | ⚡ ALL |
| **`flood_predictions`** | 👁️ SELECT (public) | 👁️ SELECT (public) | 👁️ SELECT (public) | 👁️ SELECT (public) | ⚡ ALL (ML persistence) |
| **Storage: `pollution-evidence`** | ❌ None | ➕ INSERT (own prefix)<br>👁️ SELECT (own prefix) | 👁️ SELECT (all evidence) | ⚡ ALL | ⚡ ALL |

---

## 3. Policy Details & Security Definer Functions

### 3.1 Role Resolution Function
```sql
CREATE OR REPLACE FUNCTION public.get_my_role()
RETURNS TEXT LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
    SELECT COALESCE(
        (SELECT role FROM public.profiles WHERE id = auth.uid()),
        'anonymous'
    );
$$;
```

### 3.2 Role Elevation Defense
In standard Supabase apps, users can pass `raw_user_meta_data->>'role'` during signup. In River Sentinel 2.0, this attack vector is eliminated:
```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, phone, role, account_status)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
        NEW.raw_user_meta_data->>'phone',
        'citizen', -- HARDCODED: Client cannot specify authority or admin
        'active'
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;
```

### 3.3 Administrative Elevation Procedure
Promotion to `authority_admin` or `field_officer` is restricted to explicit invocation via `public.bootstrap_initial_admin(admin_user_id)` executable exclusively by `service_role` and superuser connections.

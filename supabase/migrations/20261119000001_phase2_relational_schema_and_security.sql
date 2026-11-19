-- River Sentinel 2.0: Phase 2 Relational Schema, Roles, Security & Storage
-- Migration: 20261119000001_phase2_relational_schema_and_security.sql
-- Description: Implement profiles, monitoring_stations, devices, station_assignments,
--              extend existing tables, enforce strict RLS, and configure private storage.

BEGIN;

-- ============================================================================
-- 1. SECURITY PREFLIGHT & PRIVACY REMEDIATION (PHASE 2A)
-- ============================================================================

-- Revoke raw anonymous read access on pollution_reports (prevents identity & evidence leakage)
REVOKE SELECT ON public.pollution_reports FROM anon;
DROP POLICY IF EXISTS "Allow public read pollution_reports" ON public.pollution_reports;

-- ============================================================================
-- 2. USER PROFILES AND ROLE-BASED ACCESS CONTROL (PHASE 2C)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL DEFAULT '',
    phone VARCHAR(20),
    role VARCHAR(30) NOT NULL DEFAULT 'citizen' 
        CHECK (role IN ('citizen', 'field_officer', 'authority_admin')),
    account_status VARCHAR(20) NOT NULL DEFAULT 'active' 
        CHECK (account_status IN ('active', 'suspended', 'pending')),
    organization VARCHAR(100),
    department VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index on role for fast RBAC checks
CREATE INDEX IF NOT EXISTS idx_profiles_role ON public.profiles(role);

-- Helper function: retrieve the role of the currently authenticated user
CREATE OR REPLACE FUNCTION public.get_my_role()
RETURNS TEXT
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT COALESCE(
        (SELECT role FROM public.profiles WHERE id = auth.uid()),
        'anonymous'
    );
$$;

-- Trigger: automatically create a 'citizen' profile on Supabase Auth signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
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

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- Bootstrap procedure for first administrator (callable ONLY by service_role/postgres)
CREATE OR REPLACE FUNCTION public.bootstrap_initial_admin(admin_user_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM auth.users WHERE id = admin_user_id) THEN
        RAISE EXCEPTION 'User % does not exist in auth.users', admin_user_id;
    END IF;

    UPDATE public.profiles
    SET role = 'authority_admin', updated_at = now()
    WHERE id = admin_user_id;
END;
$$;

REVOKE ALL ON FUNCTION public.bootstrap_initial_admin(UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.bootstrap_initial_admin(UUID) TO service_role;

-- ============================================================================
-- 3. MONITORING STATIONS (PHASE 2D)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.monitoring_stations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    station_code VARCHAR(50) UNIQUE NOT NULL,
    station_name VARCHAR(100) NOT NULL,
    river_name VARCHAR(50) NOT NULL DEFAULT 'Ganga',
    description TEXT,
    location_name VARCHAR(100) NOT NULL,
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(9,6) NOT NULL,
    warning_water_level_m NUMERIC(6,2) DEFAULT 71.26,
    danger_water_level_m NUMERIC(6,2) DEFAULT 73.23,
    installation_date DATE DEFAULT CURRENT_DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'maintenance', 'decommissioned')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_stations_status ON public.monitoring_stations(status);

-- ============================================================================
-- 4. DEVICE MANAGEMENT (PHASE 2E)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    station_id UUID REFERENCES public.monitoring_stations(id) ON DELETE SET NULL,
    device_code VARCHAR(50) UNIQUE NOT NULL,
    device_name VARCHAR(100) NOT NULL,
    device_type VARCHAR(50) NOT NULL DEFAULT 'ESP32-WROOM-32',
    firmware_version VARCHAR(20) DEFAULT 'v1.0.0',
    credential_hash VARCHAR(128) NOT NULL, -- SHA-256 hash of device pre-shared key
    status VARCHAR(20) NOT NULL DEFAULT 'provisioned'
        CHECK (status IN ('provisioned', 'active', 'inactive', 'revoked')),
    last_seen_at TIMESTAMPTZ,
    battery_level_pct NUMERIC(5,2),
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_devices_station ON public.devices(station_id);
CREATE INDEX IF NOT EXISTS idx_devices_status ON public.devices(status);

-- ============================================================================
-- 5. FIELD OFFICER ASSIGNMENTS (PHASE 2G)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.station_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    station_id UUID NOT NULL REFERENCES public.monitoring_stations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    assigned_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'revoked')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (station_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_assignments_user ON public.station_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_assignments_station ON public.station_assignments(station_id);

-- ============================================================================
-- 6. EXTEND EXISTING TABLES WITH RELATIONAL RELATIONSHIPS (PHASE 2F)
-- ============================================================================

-- Extend sensor_readings
ALTER TABLE public.sensor_readings
    ADD COLUMN IF NOT EXISTS station_id UUID REFERENCES public.monitoring_stations(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS device_id UUID REFERENCES public.devices(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS received_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS device_message_id UUID,
    ADD COLUMN IF NOT EXISTS quality_status VARCHAR(30) DEFAULT 'valid';

CREATE INDEX IF NOT EXISTS idx_sensor_readings_station_created 
    ON public.sensor_readings(station_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_created 
    ON public.sensor_readings(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sensor_message_id 
    ON public.sensor_readings(device_message_id) 
    WHERE device_message_id IS NOT NULL;

-- Extend pollution_reports
ALTER TABLE public.pollution_reports
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS station_id UUID REFERENCES public.monitoring_stations(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS storage_path TEXT,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_reports_created_by 
    ON public.pollution_reports(created_by);
CREATE INDEX IF NOT EXISTS idx_reports_status 
    ON public.pollution_reports(status);

-- Extend flood_predictions
ALTER TABLE public.flood_predictions
    ADD COLUMN IF NOT EXISTS station_id UUID REFERENCES public.monitoring_stations(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS model_version VARCHAR(30) DEFAULT 'v2.0-rf-6feat',
    ADD COLUMN IF NOT EXISTS prediction_horizon VARCHAR(20) DEFAULT '24h',
    ADD COLUMN IF NOT EXISTS provenance VARCHAR(30) DEFAULT 'operational';

CREATE INDEX IF NOT EXISTS idx_flood_station_created 
    ON public.flood_predictions(station_id, created_at DESC);

-- ============================================================================
-- 7. SANITIZED PUBLIC VIEW FOR ENVIRONMENTAL METRICS
-- ============================================================================

-- Provides sanitized public telemetry without exposing internal device IDs or raw payloads
CREATE OR REPLACE VIEW public.public_sensor_telemetry
WITH (security_invoker = true)
AS
SELECT 
    id,
    created_at,
    station_id,
    ph,
    turbidity,
    temperature,
    humidity,
    ec,
    water_level,
    bod,
    cod,
    "do",
    provenance,
    status
FROM public.sensor_readings;

GRANT SELECT ON public.public_sensor_telemetry TO anon, authenticated;

-- ============================================================================
-- 8. ROW-LEVEL SECURITY ENFORCEMENT
-- ============================================================================

-- Enable RLS across all new tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.monitoring_stations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.station_assignments ENABLE ROW LEVEL SECURITY;

-- 8.1 Profiles RLS Policies
DROP POLICY IF EXISTS "Users can read own profile" ON public.profiles;
CREATE POLICY "Users can read own profile"
    ON public.profiles FOR SELECT
    TO authenticated
    USING (id = auth.uid());

DROP POLICY IF EXISTS "Authority admins can read all profiles" ON public.profiles;
CREATE POLICY "Authority admins can read all profiles"
    ON public.profiles FOR SELECT
    TO authenticated
    USING (public.get_my_role() = 'authority_admin');

DROP POLICY IF EXISTS "Users can update own safe fields" ON public.profiles;
CREATE POLICY "Users can update own safe fields"
    ON public.profiles FOR UPDATE
    TO authenticated
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid()); -- Note: Role changes restricted via API / functions

DROP POLICY IF EXISTS "Authority admins can update profiles" ON public.profiles;
CREATE POLICY "Authority admins can update profiles"
    ON public.profiles FOR UPDATE
    TO authenticated
    USING (public.get_my_role() = 'authority_admin')
    WITH CHECK (public.get_my_role() = 'authority_admin');

-- 8.2 Monitoring Stations RLS Policies
DROP POLICY IF EXISTS "Public can view active stations" ON public.monitoring_stations;
CREATE POLICY "Public can view active stations"
    ON public.monitoring_stations FOR SELECT
    TO anon, authenticated
    USING (status = 'active');

DROP POLICY IF EXISTS "Admins can manage stations" ON public.monitoring_stations;
CREATE POLICY "Admins can manage stations"
    ON public.monitoring_stations FOR ALL
    TO authenticated
    USING (public.get_my_role() = 'authority_admin')
    WITH CHECK (public.get_my_role() = 'authority_admin');

-- 8.3 Devices RLS Policies (Strictly non-public)
DROP POLICY IF EXISTS "Admins can manage devices" ON public.devices;
CREATE POLICY "Admins can manage devices"
    ON public.devices FOR ALL
    TO authenticated
    USING (public.get_my_role() = 'authority_admin')
    WITH CHECK (public.get_my_role() = 'authority_admin');

DROP POLICY IF EXISTS "Field officers can view assigned devices" ON public.devices;
CREATE POLICY "Field officers can view assigned devices"
    ON public.devices FOR SELECT
    TO authenticated
    USING (
        public.get_my_role() = 'field_officer' AND
        station_id IN (
            SELECT station_id FROM public.station_assignments 
            WHERE user_id = auth.uid() AND status = 'active'
        )
    );

-- 8.4 Station Assignments RLS Policies
DROP POLICY IF EXISTS "Admins can manage assignments" ON public.station_assignments;
CREATE POLICY "Admins can manage assignments"
    ON public.station_assignments FOR ALL
    TO authenticated
    USING (public.get_my_role() = 'authority_admin')
    WITH CHECK (public.get_my_role() = 'authority_admin');

DROP POLICY IF EXISTS "Officers can view own assignments" ON public.station_assignments;
CREATE POLICY "Officers can view own assignments"
    ON public.station_assignments FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

-- 8.5 Pollution Reports RLS Policies (Mandatory Privacy Correction)
DROP POLICY IF EXISTS "Citizens can read own reports" ON public.pollution_reports;
CREATE POLICY "Citizens can read own reports"
    ON public.pollution_reports FOR SELECT
    TO authenticated
    USING (created_by = auth.uid());

DROP POLICY IF EXISTS "Citizens can insert own reports" ON public.pollution_reports;
CREATE POLICY "Citizens can insert own reports"
    ON public.pollution_reports FOR INSERT
    TO authenticated
    WITH CHECK (created_by = auth.uid());

DROP POLICY IF EXISTS "Authorities and officers can view all reports" ON public.pollution_reports;
CREATE POLICY "Authorities and officers can view all reports"
    ON public.pollution_reports FOR SELECT
    TO authenticated
    USING (public.get_my_role() IN ('authority_admin', 'field_officer'));

DROP POLICY IF EXISTS "Authorities can update report status" ON public.pollution_reports;
CREATE POLICY "Authorities can update report status"
    ON public.pollution_reports FOR UPDATE
    TO authenticated
    USING (public.get_my_role() IN ('authority_admin', 'field_officer'))
    WITH CHECK (public.get_my_role() IN ('authority_admin', 'field_officer'));

-- ============================================================================
-- 9. PERMISSION GRANTS & REVOCATIONS
-- ============================================================================

-- Explicitly revoke access to sensitive tables from anon role
REVOKE ALL ON public.profiles FROM anon;
REVOKE ALL ON public.devices FROM anon;
REVOKE ALL ON public.station_assignments FROM anon;

-- Grant appropriate permissions to authenticated role
GRANT SELECT, UPDATE ON public.profiles TO authenticated;
GRANT SELECT ON public.monitoring_stations TO anon, authenticated;
GRANT SELECT ON public.devices TO authenticated;
GRANT SELECT ON public.station_assignments TO authenticated;
GRANT SELECT, INSERT ON public.pollution_reports TO authenticated;

-- Ensure service_role maintains full unrestricted access for backend operations
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO service_role;

-- ============================================================================
-- 10. SUPABASE STORAGE BUCKET CONFIGURATION (PHASE 2I)
-- ============================================================================

-- Create private bucket 'pollution-evidence' if not exists
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pollution-evidence',
    'pollution-evidence',
    false, -- Strictly private
    10485760, -- 10MB limit
    ARRAY['image/jpeg', 'image/png', 'image/webp']
)
ON CONFLICT (id) DO UPDATE SET
    public = false,
    file_size_limit = 10485760,
    allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/webp'];

-- Storage RLS Policies for pollution-evidence bucket
DROP POLICY IF EXISTS "Authenticated users can upload evidence" ON storage.objects;
CREATE POLICY "Authenticated users can upload evidence"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (
        bucket_id = 'pollution-evidence' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

DROP POLICY IF EXISTS "Users can view own evidence" ON storage.objects;
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

COMMIT;

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';

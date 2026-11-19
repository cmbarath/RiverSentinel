-- River Sentinel 2.0: Phase 3A CWC Reference Gauge & Device Lifecycle Migration
-- Migration: 20261119000002_phase3a_cwc_and_device_lifecycle.sql
-- Description: Correct CWC Varanasi reference levels, update station & device lifecycle
--              enums, purge fabricated device values, and decouple simulated readings.

BEGIN;

-- ============================================================================
-- 1. CWC OFFICIAL REFERENCE GAUGES TABLE (PHASE 3A - PART 2)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.cwc_reference_gauges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gauge_code VARCHAR(50) UNIQUE NOT NULL,
    site_name VARCHAR(100) NOT NULL,
    river_name VARCHAR(50) NOT NULL DEFAULT 'Ganga',
    basin_name VARCHAR(50) NOT NULL DEFAULT 'Ganga Basin',
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(9,6) NOT NULL,
    warning_level_m NUMERIC(6,2) NOT NULL,
    danger_level_m NUMERIC(6,2) NOT NULL,
    highest_flood_level_m NUMERIC(6,2) NOT NULL,
    hfl_date DATE,
    reference_datum VARCHAR(100) NOT NULL DEFAULT 'Mean Sea Level (GTS MSL)',
    source_authority VARCHAR(100) NOT NULL DEFAULT 'Central Water Commission (CWC), Government of India',
    source_document VARCHAR(255) NOT NULL DEFAULT 'CWC Flood Forecasting and Warning Network Performance Appraisal Report 2024, Annex II',
    verification_date DATE NOT NULL DEFAULT '2024-05-15',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable RLS and grant read access to anon & authenticated
ALTER TABLE public.cwc_reference_gauges ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public can view CWC reference gauges" ON public.cwc_reference_gauges;
CREATE POLICY "Public can view CWC reference gauges"
    ON public.cwc_reference_gauges FOR SELECT
    TO anon, authenticated
    USING (true);

GRANT SELECT ON public.cwc_reference_gauges TO anon, authenticated;

-- Seed Official CWC Varanasi Reference Gauge (Lat ~25.33, Lon ~83.04)
INSERT INTO public.cwc_reference_gauges (
    gauge_code, site_name, river_name, latitude, longitude,
    warning_level_m, danger_level_m, highest_flood_level_m, hfl_date,
    reference_datum, source_authority, source_document, notes
) VALUES (
    'CWC-VARANASI-01',
    'Varanasi CWC Hydro-Meteorological Gauge Site',
    'Ganga',
    25.330000,
    83.040000,
    70.26,  -- Official Warning Level: 70.26m
    71.26,  -- Official Danger Level: 71.26m
    73.90,  -- Official HFL: 73.90m
    '2016-09-09',
    'Mean Sea Level (GTS MSL)',
    'Central Water Commission (CWC), Ministry of Jal Shakti, Government of India',
    'CWC Flood Forecasting and Warning Network Performance Appraisal Report 2024, Annex II',
    'Official statutory CWC river gauge site for Varanasi. River Sentinel local ghat sensors measure relative stage and require a documented datum conversion offset before equating to this GTS gauge.'
)
ON CONFLICT (gauge_code) DO UPDATE SET
    warning_level_m = EXCLUDED.warning_level_m,
    danger_level_m = EXCLUDED.danger_level_m,
    highest_flood_level_m = EXCLUDED.highest_flood_level_m,
    updated_at = now();


-- ============================================================================
-- 2. STATION LIFECYCLE & DATUM CONVERSION EXTENSIONS (PHASE 3A - PART 2 & 3)
-- ============================================================================

-- Add datum conversion offset column and link to CWC gauge
ALTER TABLE public.monitoring_stations
    ADD COLUMN IF NOT EXISTS cwc_reference_gauge_id UUID REFERENCES public.cwc_reference_gauges(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS datum_offset_to_msl_m NUMERIC(6,2) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS installation_type VARCHAR(50) DEFAULT 'uninstalled_proposed';

-- Update status constraint on monitoring_stations to support full lifecycle
ALTER TABLE public.monitoring_stations DROP CONSTRAINT IF EXISTS monitoring_stations_status_check;
ALTER TABLE public.monitoring_stations ADD CONSTRAINT monitoring_stations_status_check
    CHECK (status IN ('planned', 'installation_pending', 'installed', 'active', 'inactive', 'maintenance'));

-- Update RLS policy so public dashboards can view planned, installed, and active stations
DROP POLICY IF EXISTS "Public can view active stations" ON public.monitoring_stations;
CREATE POLICY "Public can view active stations"
    ON public.monitoring_stations FOR SELECT
    TO anon, authenticated
    USING (status IN ('active', 'planned', 'installed', 'maintenance'));

-- Update the 4 planned ghat stations:
-- 1. Correct status from premature 'active' to 'planned'
-- 2. Associate with CWC reference gauge
-- 3. Adjust threshold labels to reflect local sensor gauge limits vs reference datum
UPDATE public.monitoring_stations
SET status = 'planned',
    cwc_reference_gauge_id = (SELECT id FROM public.cwc_reference_gauges WHERE gauge_code = 'CWC-VARANASI-01'),
    warning_water_level_m = 70.26,
    danger_water_level_m = 71.26,
    description = description || ' [Local sensor relative calibration pending physical survey].',
    updated_at = now()
WHERE station_code IN ('STN-VAR-ASSI-01', 'STN-VAR-DASH-02', 'STN-VAR-MANI-03', 'STN-VAR-RAJG-04');


-- ============================================================================
-- 3. DEVICE LIFECYCLE & FABRICATED DATA PURGE (PHASE 3A - PART 3)
-- ============================================================================

-- First update existing devices to 'provisioned' and purge fabricated values
UPDATE public.devices
SET status = 'provisioned',
    battery_level_pct = NULL,
    last_seen_at = NULL,
    firmware_version = 'v1.0.0-framework',
    updated_at = now()
WHERE device_code IN ('DEV-ESP32-ASSI-01', 'DEV-ESP32-DASH-02', 'DEV-ESP32-MANI-03', 'DEV-ESP32-RAJG-04')
   OR status NOT IN ('registered', 'awaiting_installation', 'provisioned', 'online', 'offline', 'revoked', 'maintenance');

-- Update status constraint on devices to support full lifecycle
ALTER TABLE public.devices DROP CONSTRAINT IF EXISTS devices_status_check;
ALTER TABLE public.devices ADD CONSTRAINT devices_status_check
    CHECK (status IN ('registered', 'awaiting_installation', 'provisioned', 'online', 'offline', 'revoked', 'maintenance'));


-- ============================================================================
-- 4. CLEANUP SENSOR READINGS PROVENANCE INTEGRITY & OBSERVED_AT (PHASE 3A)
-- ============================================================================

-- Add observed_at timestamp column to decouple edge sampling time from server receipt time
ALTER TABLE public.sensor_readings
    ADD COLUMN IF NOT EXISTS observed_at TIMESTAMPTZ;

-- Drop legacy NOT NULL constraints on measurement columns to support missing,
-- disconnected, or uncalibrated physical sensors without silent zero substitution
ALTER TABLE public.sensor_readings
    ALTER COLUMN ph DROP NOT NULL,
    ALTER COLUMN turbidity DROP NOT NULL,
    ALTER COLUMN temperature DROP NOT NULL,
    ALTER COLUMN humidity DROP NOT NULL,
    ALTER COLUMN ec DROP NOT NULL,
    ALTER COLUMN water_level DROP NOT NULL,
    ALTER COLUMN bod DROP NOT NULL,
    ALTER COLUMN cod DROP NOT NULL,
    ALTER COLUMN "do" DROP NOT NULL;

-- Disassociate simulated readings from physical device IDs (simulated != physical device)
UPDATE public.sensor_readings
SET device_id = NULL
WHERE provenance = 'simulated' AND device_id IS NOT NULL;


-- ============================================================================
-- 5. DEVICE TELEMETRY AUDIT LOG TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.device_telemetry_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES public.devices(id) ON DELETE SET NULL,
    device_code VARCHAR(50) NOT NULL,
    message_id UUID NOT NULL,
    sequence_number BIGINT,
    observed_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address VARCHAR(45),
    payload_size_bytes INT,
    validation_status VARCHAR(30) NOT NULL DEFAULT 'valid',
    processing_time_ms NUMERIC(6,2),
    error_details TEXT
);

CREATE INDEX IF NOT EXISTS idx_telemetry_logs_device ON public.device_telemetry_logs(device_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_logs_message ON public.device_telemetry_logs(message_id);

ALTER TABLE public.device_telemetry_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Admins and officers can read telemetry logs" ON public.device_telemetry_logs;
CREATE POLICY "Admins and officers can read telemetry logs"
    ON public.device_telemetry_logs FOR SELECT
    TO authenticated
    USING (public.get_my_role() IN ('authority_admin', 'field_officer'));

GRANT SELECT ON public.device_telemetry_logs TO authenticated;
GRANT ALL ON public.device_telemetry_logs TO service_role;

COMMIT;

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';

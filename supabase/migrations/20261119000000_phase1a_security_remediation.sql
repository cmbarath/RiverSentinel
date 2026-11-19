-- River Sentinel 2.0: Phase 1A Security Remediation Migration
-- Migration: 20261119000000_phase1a_security_remediation.sql
-- Description: Revoke excessive grants from anon and authenticated, remove public sensor insert, enforce least-privilege RLS.

BEGIN;

-- 1. Revoke destructive and excessive permissions from anon role
REVOKE TRUNCATE, DELETE, TRIGGER, REFERENCES, INSERT, UPDATE 
ON ALL TABLES IN SCHEMA public 
FROM anon;

-- Revoke destructive permissions from authenticated role
REVOKE TRUNCATE, DELETE, TRIGGER, REFERENCES 
ON ALL TABLES IN SCHEMA public 
FROM authenticated;

-- 2. Grant least-privilege read access to anon and authenticated
GRANT SELECT ON public.sensor_readings TO anon, authenticated;
GRANT SELECT ON public.flood_predictions TO anon, authenticated;
GRANT SELECT ON public.pollution_reports TO anon, authenticated;

-- Reaffirm full operational privileges for backend service_role
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO service_role;

-- 3. Ensure Row-Level Security is strictly enabled on all application tables
ALTER TABLE public.sensor_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pollution_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.flood_predictions ENABLE ROW LEVEL SECURITY;

-- 4. Remediate RLS Policies on sensor_readings
-- DROP the dangerous unrestricted public insert policy
DROP POLICY IF EXISTS "Allow public insert sensor_readings" ON public.sensor_readings;

-- Re-affirm clean read-only policy for sensor readings
DROP POLICY IF EXISTS "Allow public read sensor_readings" ON public.sensor_readings;
CREATE POLICY "Allow public read sensor_readings" 
ON public.sensor_readings 
FOR SELECT 
USING (true);

-- 5. Establish clean read-only policies on flood predictions and citizen reports
DROP POLICY IF EXISTS "Allow public read flood_predictions" ON public.flood_predictions;
CREATE POLICY "Allow public read flood_predictions" 
ON public.flood_predictions 
FOR SELECT 
USING (true);

DROP POLICY IF EXISTS "Allow public read pollution_reports" ON public.pollution_reports;
CREATE POLICY "Allow public read pollution_reports" 
ON public.pollution_reports 
FOR SELECT 
USING (status IN ('PENDING', 'VERIFIED', 'RESOLVED'));

COMMIT;

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';

-- Rollback Script for 20261119000000_phase1a_security_remediation.sql
-- Use only if emergency restoration of Phase 0 open access is explicitly required.

BEGIN;

GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

DROP POLICY IF EXISTS "Allow public insert sensor_readings" ON public.sensor_readings;
CREATE POLICY "Allow public insert sensor_readings" 
ON public.sensor_readings 
FOR INSERT 
WITH CHECK (true);

COMMIT;

NOTIFY pgrst, 'reload schema';

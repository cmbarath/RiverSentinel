-- Migration: 20261119000005_phase7_performance_indexes.sql
-- Description: Targeted performance indexes, stuck worker recovery indexes, and worker heartbeat registry table.

-- 1. Index for notification outbox stuck-job recovery sweeps (status = 'processing' AND updated_at < threshold)
CREATE INDEX IF NOT EXISTS idx_notification_deliveries_processing_recovery
ON public.notification_deliveries (status, updated_at)
WHERE status = 'processing';

-- 2. Composite index for sensor telemetry retrieval and station status queries
CREATE INDEX IF NOT EXISTS idx_sensor_readings_station_quality_created
ON public.sensor_readings (station_id, created_at DESC, quality_status);

-- 3. Chronological index for alert lifecycle events audit queries
CREATE INDEX IF NOT EXISTS idx_alert_events_created_desc
ON public.alert_events (alert_id, created_at DESC);

-- 4. Index for authority pollution report review queries
CREATE INDEX IF NOT EXISTS idx_pollution_reports_status_created
ON public.pollution_reports (status, created_at DESC);

-- 5. Worker heartbeat and observability registry table
CREATE TABLE IF NOT EXISTS public.worker_heartbeats (
    worker_name TEXT PRIMARY KEY,
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'unknown',
    metrics JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE public.worker_heartbeats ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Admins and Service Role can manage heartbeats
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
          AND tablename = 'worker_heartbeats' 
          AND policyname = 'worker_heartbeats_admin_all'
    ) THEN
        CREATE POLICY worker_heartbeats_admin_all ON public.worker_heartbeats
        FOR ALL USING (
            auth.role() = 'service_role' OR 
            EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'authority_admin')
        );
    END IF;
END $$;

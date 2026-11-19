-- ============================================================================
-- River Sentinel 2.0 — Phase 5: Alert Engine, Notification System & Telephony
-- Migration: 20261119000003_phase5_alerts_and_notifications.sql
-- ============================================================================

-- 1. ALERT RULES TABLE
CREATE TABLE IF NOT EXISTS public.alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_code VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(64) NOT NULL, -- 'FLOOD', 'WATER_QUALITY', 'DEVICE_HEALTH', 'POLLUTION_REPORT'
    station_id UUID REFERENCES public.monitoring_stations(id) ON DELETE CASCADE, -- NULL = global rule
    parameter VARCHAR(64) NOT NULL, -- 'water_level', 'ph', 'turbidity', 'do', 'device_status', 'pollution_report'
    operator VARCHAR(16) NOT NULL, -- '>=', '>', '<=', '<', '=', 'out_of_range', 'stale_seconds'
    threshold_value NUMERIC(10,2),
    threshold_value_max NUMERIC(10,2), -- for out_of_range windowing
    threshold_unit VARCHAR(32), -- 'm', 'pH', 'NTU', 'mg/L', 'seconds'
    severity VARCHAR(32) NOT NULL DEFAULT 'MEDIUM', -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL'
    enabled BOOLEAN DEFAULT true NOT NULL,
    minimum_duration_seconds INTEGER DEFAULT 0 NOT NULL,
    recovery_threshold NUMERIC(10,2),
    recovery_duration_seconds INTEGER DEFAULT 300 NOT NULL,
    cooldown_seconds INTEGER DEFAULT 900 NOT NULL,
    rule_version INTEGER DEFAULT 1 NOT NULL,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 2. SYSTEM ALERTS TABLE
CREATE TABLE IF NOT EXISTS public.system_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_code VARCHAR(64) UNIQUE NOT NULL,
    rule_id UUID REFERENCES public.alert_rules(id) ON DELETE SET NULL,
    station_id UUID REFERENCES public.monitoring_stations(id) ON DELETE SET NULL,
    device_id UUID REFERENCES public.devices(id) ON DELETE SET NULL,
    category VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    source_type VARCHAR(64) NOT NULL, -- 'sensor_reading', 'device_telemetry', 'pollution_report', 'manual_audit'
    source_record_id VARCHAR(128),
    provenance VARCHAR(32) DEFAULT 'real_sensor' NOT NULL,
    quality_status VARCHAR(32) DEFAULT 'valid' NOT NULL,
    measured_value NUMERIC(10,2),
    expected_threshold NUMERIC(10,2),
    threshold_unit VARCHAR(32),
    rule_version INTEGER DEFAULT 1 NOT NULL,
    deduplication_key VARCHAR(255) NOT NULL,
    status VARCHAR(32) DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'acknowledged', 'resolved')),
    occurrence_count INTEGER DEFAULT 1 NOT NULL,
    first_triggered_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    last_triggered_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    acknowledged_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    resolved_at TIMESTAMPTZ,
    resolution_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 3. ALERT EVENTS AUDIT LOG TABLE
CREATE TABLE IF NOT EXISTS public.alert_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID REFERENCES public.system_alerts(id) ON DELETE CASCADE NOT NULL,
    event_type VARCHAR(64) NOT NULL, -- 'triggered', 'repeated', 'escalated', 'acknowledged', 'resolved', 'reopened', 'delivery_failed', 'delivery_succeeded'
    actor_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 4. USER NOTIFICATION PREFERENCES TABLE
CREATE TABLE IF NOT EXISTS public.notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    in_app_enabled BOOLEAN DEFAULT true NOT NULL,
    email_enabled BOOLEAN DEFAULT false NOT NULL,
    sms_enabled BOOLEAN DEFAULT false NOT NULL,
    preferred_severities TEXT[] DEFAULT ARRAY['CRITICAL', 'HIGH']::text[] NOT NULL,
    preferred_categories TEXT[] DEFAULT ARRAY['FLOOD', 'WATER_QUALITY', 'POLLUTION_REPORT']::text[] NOT NULL,
    phone_number_verified BOOLEAN DEFAULT false NOT NULL,
    email_verified BOOLEAN DEFAULT false NOT NULL,
    consent_timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 5. NOTIFICATION DELIVERIES (TRANSACTIONAL OUTBOX) TABLE
CREATE TABLE IF NOT EXISTS public.notification_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID REFERENCES public.system_alerts(id) ON DELETE CASCADE NOT NULL,
    recipient_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    recipient_phone VARCHAR(32),
    recipient_email VARCHAR(255),
    channel VARCHAR(32) NOT NULL CHECK (channel IN ('in_app', 'sms', 'email')),
    provider VARCHAR(64) DEFAULT 'mock' NOT NULL,
    status VARCHAR(32) DEFAULT 'queued' NOT NULL CHECK (status IN ('queued', 'processing', 'accepted', 'delivered', 'failed', 'cancelled')),
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,
    attempt_count INTEGER DEFAULT 0 NOT NULL,
    max_attempts INTEGER DEFAULT 5 NOT NULL,
    next_attempt_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    provider_message_id VARCHAR(128),
    message_payload JSONB DEFAULT '{}'::jsonb NOT NULL,
    accepted_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    last_error_code VARCHAR(64),
    last_error_message TEXT,
    read_at TIMESTAMPTZ, -- for in_app notifications
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 6. PERFORMANCE & OUTBOX INDEXES
CREATE INDEX IF NOT EXISTS idx_alert_rules_category ON public.alert_rules(category, enabled);
CREATE INDEX IF NOT EXISTS idx_alert_rules_station ON public.alert_rules(station_id) WHERE station_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_system_alerts_status ON public.system_alerts(status);
CREATE INDEX IF NOT EXISTS idx_system_alerts_station ON public.system_alerts(station_id);
CREATE INDEX IF NOT EXISTS idx_system_alerts_category ON public.system_alerts(category);
CREATE INDEX IF NOT EXISTS idx_system_alerts_active_dedup ON public.system_alerts(deduplication_key) WHERE status != 'resolved';

CREATE INDEX IF NOT EXISTS idx_alert_events_alert_id ON public.alert_events(alert_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notification_deliveries_outbox ON public.notification_deliveries(status, next_attempt_at) WHERE status IN ('queued', 'processing');
CREATE INDEX IF NOT EXISTS idx_notification_deliveries_user_in_app ON public.notification_deliveries(recipient_user_id, channel, read_at, created_at DESC);

-- 7. ENABLE ROW-LEVEL SECURITY (RLS)
ALTER TABLE public.alert_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alert_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_deliveries ENABLE ROW LEVEL SECURITY;

-- 8. RLS POLICIES

-- Alert Rules:
-- Authority Admins: full access
CREATE POLICY "alert_rules_admin_all" ON public.alert_rules
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'authority_admin'))
    WITH CHECK (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'authority_admin'));

-- Field Officers: view rules
CREATE POLICY "alert_rules_field_officer_select" ON public.alert_rules
    FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('field_officer', 'authority_admin')));

-- System Alerts:
-- Authority Admins: full access
CREATE POLICY "system_alerts_admin_all" ON public.system_alerts
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'authority_admin'))
    WITH CHECK (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'authority_admin'));

-- Field Officers: view all alerts, acknowledge/resolve alerts for assigned stations
CREATE POLICY "system_alerts_field_officer_select" ON public.system_alerts
    FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'field_officer'));

CREATE POLICY "system_alerts_field_officer_update" ON public.system_alerts
    FOR UPDATE TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles p
            JOIN public.station_assignments sa ON sa.user_id = p.id
            WHERE p.id = auth.uid() 
              AND p.role = 'field_officer' 
              AND (sa.station_id = system_alerts.station_id OR system_alerts.station_id IS NULL)
              AND sa.status = 'active'
        )
    );

-- Citizens & Public: view active public environmental alerts (FLOOD, WATER_QUALITY)
CREATE POLICY "system_alerts_public_select" ON public.system_alerts
    FOR SELECT TO authenticated
    USING (category IN ('FLOOD', 'WATER_QUALITY') AND status != 'resolved');

CREATE POLICY "system_alerts_anon_select" ON public.system_alerts
    FOR SELECT TO anon
    USING (category IN ('FLOOD', 'WATER_QUALITY') AND status != 'resolved');

-- Alert Events:
-- Authority Admins & Field Officers can inspect event history
CREATE POLICY "alert_events_officers_select" ON public.alert_events
    FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('authority_admin', 'field_officer')));

-- Notification Preferences:
-- Users manage their own preferences
CREATE POLICY "notification_preferences_user_select" ON public.notification_preferences
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "notification_preferences_user_upsert" ON public.notification_preferences
    FOR ALL TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Notification Deliveries:
-- Users can view their own in-app/delivery records and mark in-app notifications read
CREATE POLICY "notification_deliveries_user_select" ON public.notification_deliveries
    FOR SELECT TO authenticated
    USING (recipient_user_id = auth.uid());

CREATE POLICY "notification_deliveries_user_update" ON public.notification_deliveries
    FOR UPDATE TO authenticated
    USING (recipient_user_id = auth.uid() AND channel = 'in_app')
    WITH CHECK (recipient_user_id = auth.uid() AND channel = 'in_app');

-- 9. SEED CANONICAL DEFAULT ALERT RULES
INSERT INTO public.alert_rules (
    rule_code, name, description, category, parameter, operator,
    threshold_value, threshold_unit, severity, minimum_duration_seconds, recovery_threshold, recovery_duration_seconds, cooldown_seconds
) VALUES 
(
    'RULE-CWC-FLOOD-WARN',
    'CWC River Stage Warning Stage Exceeded',
    'Ganga River stage at Varanasi reference gauge reaches or exceeds CWC Warning Level (70.26m GTS Datum MSL).',
    'FLOOD',
    'water_level',
    '>=',
    70.26,
    'm',
    'HIGH',
    0,
    70.10,
    600,
    1800
),
(
    'RULE-CWC-FLOOD-DANGER',
    'CWC River Stage Danger Stage Exceeded',
    'Ganga River stage at Varanasi reference gauge reaches or exceeds CWC Danger Level (71.26m GTS Datum MSL). Immediate riparian evacuation advisory.',
    'FLOOD',
    'water_level',
    '>=',
    71.26,
    'm',
    'CRITICAL',
    0,
    71.10,
    600,
    900
),
(
    'RULE-CPCB-PH-RANGE',
    'CPCB Class B pH Deviation',
    'Surface water pH deviates from CPCB Class B Outdoor Bathing statutory benchmark (6.5 to 8.5).',
    'WATER_QUALITY',
    'ph',
    'out_of_range',
    6.50,
    'pH',
    'MEDIUM',
    300,
    6.60,
    600,
    3600
),
(
    'RULE-CPCB-DO-MIN',
    'CPCB Class B Dissolved Oxygen Depletion',
    'Dissolved oxygen falls below CPCB Class B minimum threshold of 5.0 mg/L, indicating organic overload or stagnant hypoxia.',
    'WATER_QUALITY',
    'do',
    '<',
    5.00,
    'mg/L',
    'HIGH',
    300,
    5.20,
    600,
    1800
),
(
    'RULE-TURB-HIGH',
    'High Turbidity / Silt Sediment Peak',
    'Turbidity exceeds 50 NTU, indicating severe surface sediment runoff, industrial discharge, or dredging disturbance.',
    'WATER_QUALITY',
    'turbidity',
    '>',
    50.00,
    'NTU',
    'MEDIUM',
    300,
    40.00,
    600,
    3600
),
(
    'RULE-DEV-OFFLINE',
    'Active IoT Hardware Node Disconnected',
    'Provisioned and deployed physical ESP32 node has not sent telemetry touch in greater than 900 seconds.',
    'DEVICE_HEALTH',
    'device_status',
    'stale_seconds',
    900,
    'seconds',
    'HIGH',
    0,
    0,
    0,
    1800
),
(
    'RULE-POLLUTION-NEW',
    'New Citizen Pollution Incident Lodged',
    'A citizen report with image evidence and location coordinates has been submitted for UPPCB authority review.',
    'POLLUTION_REPORT',
    'pollution_report',
    '=',
    1,
    'count',
    'HIGH',
    0,
    0,
    0,
    300
)
ON CONFLICT (rule_code) DO NOTHING;

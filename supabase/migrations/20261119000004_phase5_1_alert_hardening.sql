-- ============================================================================
-- River Sentinel 2.0 - Phase 5.1 Migration
-- Alert Accuracy, Deduplication and Notification Hardening
-- ============================================================================

-- 1. Add metadata & statutory flag columns to alert_rules if missing
ALTER TABLE public.alert_rules
ADD COLUMN IF NOT EXISTS is_cpcb_statutory BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS source_reference VARCHAR(150) DEFAULT 'Project Specification v2.0';

-- 2. Update RULE-TURB-HIGH: Remove attribution to CPCB Class B
-- Label as configurable project-specific operational investigation threshold
UPDATE public.alert_rules
SET name = 'High Turbidity Investigation (Operational Screening)',
    description = 'Turbidity exceeds project-specific riparian investigation threshold (100 NTU). Operational screening indicator for suspended sediment, surface runoff, or dredging - NOT an official CPCB Class B criterion. (Source: Project Investigation Guideline v2.0).',
    threshold_value = 100.00,
    recovery_threshold = 85.00,
    threshold_unit = 'NTU',
    is_cpcb_statutory = FALSE,
    source_reference = 'Project Investigation Guideline v2.0',
    rule_version = 2,
    updated_at = NOW()
WHERE rule_code = 'RULE-TURB-HIGH';

-- 3. Update CPCB Class B statutory rules with explicit source references
UPDATE public.alert_rules
SET is_cpcb_statutory = TRUE,
    source_reference = 'CPCB Primary Water Quality Criteria for Class B (Outdoor Bathing)',
    rule_version = 2,
    updated_at = NOW()
WHERE rule_code IN ('RULE-CPCB-PH-RANGE', 'RULE-CPCB-DO-MIN');

-- 4. Update CWC Flood Stage rules with CWC source reference
UPDATE public.alert_rules
SET is_cpcb_statutory = FALSE,
    source_reference = 'Central Water Commission (CWC) Varanasi Reference Gauge (GTS MSL Datum)',
    rule_version = 2,
    updated_at = NOW()
WHERE rule_code IN ('RULE-CWC-FLOOD-WARN', 'RULE-CWC-FLOOD-DANGER');

-- 5. Ensure notification_deliveries status constraint contains all valid lifecycle states
ALTER TABLE public.notification_deliveries 
DROP CONSTRAINT IF EXISTS notification_deliveries_status_check;

ALTER TABLE public.notification_deliveries 
ADD CONSTRAINT notification_deliveries_status_check 
CHECK (status IN ('queued', 'processing', 'accepted', 'delivered', 'failed', 'cancelled', 'suppressed'));

-- 6. Add accepted_at, delivered_at, failed_at timestamps and provider_callback_received_at if missing
ALTER TABLE public.notification_deliveries
ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS provider_callback_received_at TIMESTAMPTZ;

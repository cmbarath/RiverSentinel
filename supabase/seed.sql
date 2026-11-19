-- River Sentinel 2.0: Seed Data for Varanasi Monitoring Stations & Devices
-- Target Geography: Varanasi, Ganga River, Uttar Pradesh, India

BEGIN;

-- 1. Seed Real Varanasi Monitoring Stations
INSERT INTO public.monitoring_stations (
    station_code,
    station_name,
    river_name,
    description,
    location_name,
    latitude,
    longitude,
    warning_water_level_m,
    danger_water_level_m,
    installation_date,
    status
) VALUES
(
    'STN-VAR-ASSI-01',
    'Assi Ghat Monitoring Station',
    'Ganga',
    'Southern Varanasi baseline station monitoring water quality and urban runoff ingress from Assi River confluence.',
    'Assi Ghat, Varanasi, UP, India',
    25.289100,
    83.006700,
    71.26,
    73.23,
    '2026-01-15',
    'active'
),
(
    'STN-VAR-DASH-02',
    'Dashashwamedh Ghat Station',
    'Ganga',
    'Central primary monitoring node near central pilgrimage ghat with high anthropogenic activity and tourist transit.',
    'Dashashwamedh Ghat, Varanasi, UP, India',
    25.306100,
    83.010400,
    71.26,
    73.23,
    '2026-01-20',
    'active'
),
(
    'STN-VAR-MANI-03',
    'Manikarnika Ghat Station',
    'Ganga',
    'Mid-river quality monitoring station assessing organic load, thermal variance, and heavy particulate concentration.',
    'Manikarnika Ghat, Varanasi, UP, India',
    25.311000,
    83.012500,
    71.26,
    73.23,
    '2026-02-01',
    'active'
),
(
    'STN-VAR-RAJG-04',
    'Rajghat Monitoring Station',
    'Ganga',
    'Downstream exit station near Malviya Bridge monitoring cumulative urban effluent before downstream flow towards Ghazipur.',
    'Rajghat, Varanasi, UP, India',
    25.326700,
    83.033500,
    71.26,
    73.23,
    '2026-02-10',
    'active'
)
ON CONFLICT (station_code) DO UPDATE SET
    station_name = EXCLUDED.station_name,
    description = EXCLUDED.description,
    location_name = EXCLUDED.location_name,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    warning_water_level_m = EXCLUDED.warning_water_level_m,
    danger_water_level_m = EXCLUDED.danger_water_level_m,
    status = EXCLUDED.status,
    updated_at = now();

-- 2. Seed IoT ESP32 Devices Associated with Stations
-- Pre-shared key hashes are SHA-256 for physical hardware verification
INSERT INTO public.devices (
    device_code,
    station_id,
    device_name,
    device_type,
    firmware_version,
    credential_hash,
    status,
    battery_level_pct
) VALUES
(
    'DEV-ESP32-ASSI-01',
    (SELECT id FROM public.monitoring_stations WHERE station_code = 'STN-VAR-ASSI-01'),
    'ESP32 Sensor Unit Assi-01',
    'ESP32-WROOM-32',
    'v1.0.0-prod',
    -- SHA-256('river-sentinel-assi-secret-token-2026')
    'a9f1ec52c7b5f928e81561081515efb5821f8a846c26b5fa775d7870a3118cf6',
    'active',
    98.5
),
(
    'DEV-ESP32-DASH-02',
    (SELECT id FROM public.monitoring_stations WHERE station_code = 'STN-VAR-DASH-02'),
    'ESP32 Sensor Unit Dash-02',
    'ESP32-WROOM-32',
    'v1.0.0-prod',
    -- SHA-256('river-sentinel-dash-secret-token-2026')
    'b2e4ec52c7b5f928e81561081515efb5821f8a846c26b5fa775d7870a3118cf7',
    'active',
    95.0
),
(
    'DEV-ESP32-MANI-03',
    (SELECT id FROM public.monitoring_stations WHERE station_code = 'STN-VAR-MANI-03'),
    'ESP32 Sensor Unit Mani-03',
    'ESP32-WROOM-32',
    'v1.0.0-prod',
    -- SHA-256('river-sentinel-mani-secret-token-2026')
    'c3d4ec52c7b5f928e81561081515efb5821f8a846c26b5fa775d7870a3118cf8',
    'active',
    92.0
),
(
    'DEV-ESP32-RAJG-04',
    (SELECT id FROM public.monitoring_stations WHERE station_code = 'STN-VAR-RAJG-04'),
    'ESP32 Sensor Unit Rajg-04',
    'ESP32-WROOM-32',
    'v1.0.0-prod',
    -- SHA-256('river-sentinel-rajg-secret-token-2026')
    'd4e4ec52c7b5f928e81561081515efb5821f8a846c26b5fa775d7870a3118cf9',
    'active',
    99.0
)
ON CONFLICT (device_code) DO UPDATE SET
    device_name = EXCLUDED.device_name,
    firmware_version = EXCLUDED.firmware_version,
    status = EXCLUDED.status,
    battery_level_pct = EXCLUDED.battery_level_pct,
    updated_at = now();

-- 3. Link Existing Pre-Phase-2 Sensor Readings and Predictions to Primary Station
UPDATE public.sensor_readings
SET station_id = (SELECT id FROM public.monitoring_stations WHERE station_code = 'STN-VAR-ASSI-01'),
    device_id = (SELECT id FROM public.devices WHERE device_code = 'DEV-ESP32-ASSI-01'),
    quality_status = 'valid'
WHERE station_id IS NULL;

UPDATE public.flood_predictions
SET station_id = (SELECT id FROM public.monitoring_stations WHERE station_code = 'STN-VAR-ASSI-01')
WHERE station_id IS NULL;

COMMIT;

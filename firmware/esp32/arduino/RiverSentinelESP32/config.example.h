/*
 * River Sentinel 2.0 - ESP32 Firmware Configuration Template
 * Target: ESP32-WROOM-32 (Varanasi Ganga River Monitoring Network)
 *
 * Instructions:
 * 1. Copy this file to 'config.h' in the same directory.
 * 2. Update WIFI_SSID, WIFI_PASSWORD, and DEVICE_TOKEN.
 * 3. Never commit 'config.h' to public version control.
 */

#ifndef CONFIG_H
#define CONFIG_H

// ============================================================================
// 1. WI-FI CREDENTIALS
// ============================================================================
#define WIFI_SSID             "YOUR_WIFI_SSID"
#define WIFI_PASSWORD         "YOUR_WIFI_PASSWORD"

// ============================================================================
// 2. BACKEND API CONFIGURATION
// ============================================================================
// For local testing: set to your development machine's LAN IP (e.g., "192.168.1.100")
// For Render production: set to "river-sentinel-backend.onrender.com"
#define BACKEND_HOST          "river-sentinel-backend.onrender.com"
#define BACKEND_PORT          443               // 443 for HTTPS, 5000 for local HTTP
#define USE_TLS               true              // true for HTTPS, false for local dev
#define INGEST_ENDPOINT       "/api/v1/telemetry/ingest"

// ============================================================================
// 3. DEVICE IDENTITY & AUTHENTICATION
// ============================================================================
// Registered device code in public.devices table (Varanasi monitoring stations):
// - STN-VAR-ASSI-01 -> DEV-ESP32-ASSI-01
// - STN-VAR-DASH-02 -> DEV-ESP32-DASH-02
// - STN-VAR-MANI-03 -> DEV-ESP32-MANI-03
// - STN-VAR-RAJG-04 -> DEV-ESP32-RAJG-04
#define DEVICE_CODE           "DEV-ESP32-ASSI-01"
#define DEVICE_TOKEN          "rs_dev_assi01_replace_with_actual_token"
#define FIRMWARE_VERSION      "2.1.0-arduino"

// ============================================================================
// 4. TELEMETRY & NETWORK TIMING
// ============================================================================
#define TELEMETRY_INTERVAL_MS 60000             // Telemetry cadence: 60 seconds
#define WIFI_TIMEOUT_MS       15000             // Wi-Fi connection timeout
#define HTTP_TIMEOUT_MS       10000             // Backend HTTP request timeout
#define GMT_OFFSET_SEC        0                 // UTC 0 offset (server expects UTC)
#define DAYLIGHT_OFFSET_SEC   0                 // UTC daylight offset

// ============================================================================
// 5. HARDWARE PIN ALLOCATIONS (ESP32-WROOM-32)
// ============================================================================
#define PIN_STATUS_LED        2                 // Onboard status LED
#define PIN_PH_SENSOR_ADC     34                // Analog pH probe (ADC1_CH6)
#define PIN_TURBIDITY_ADC     35                // Analog Turbidity (ADC1_CH7)
#define PIN_TEMP_ONEWIRE      4                 // DS18B20 digital temperature
#define PIN_US_TRIG           5                 // Ultrasonic Water Level Trig
#define PIN_US_ECHO           18                // Ultrasonic Water Level Echo
#define PIN_EC_ADC            32                // Electrical Conductivity (ADC1_CH4)
#define PIN_DO_ADC            33                // Dissolved Oxygen (ADC1_CH5)
#define PIN_BATTERY_ADC       36                // Voltage divider for LiPo (ADC1_CH0)

// ============================================================================
// 6. SENSOR DEPLOYMENT STATE (SAFETY GUARDRAIL)
// ============================================================================
// IMPORTANT: Physical sensor installation is deferred for River Sentinel 2.0.
// Keep SENSORS_PHYSICALLY_ATTACHED set to 'false' during bench / prototype testing.
// When false:
//   - The node sends diagnostic benchmark telemetry
//   - sensor_status is tagged as "bench_simulation" or "not_configured"
//   - Physical pins are NOT misread as live Ganga river observations
// When set to 'true' after physical installation:
//   - The node samples calibrated hardware probes via ADC and OneWire
#define SENSORS_PHYSICALLY_ATTACHED false

// ============================================================================
// 7. OFFLINE QUEUE CAPACITY
// ============================================================================
#define OFFLINE_BUFFER_CAPACITY 50              // Max readings held in SRAM during outage

#endif // CONFIG_H

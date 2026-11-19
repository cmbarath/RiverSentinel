#ifndef CONFIG_H
#define CONFIG_H

// River Sentinel 2.0 - ESP32 Firmware Configuration Template
// Copy this file to config.h and fill in deployment values.
// NEVER commit the real config.h file to Git!

// ============================================================================
// 1. NETWORK & WI-FI CONFIGURATION
// ============================================================================
#define WIFI_SSID           "YOUR_DEPLOYMENT_WIFI_SSID"
#define WIFI_PASSWORD       "YOUR_DEPLOYMENT_WIFI_PASSWORD"
#define WIFI_CONNECT_TIMEOUT_MS 15000
#define WIFI_MAX_RETRIES        5

// ============================================================================
// 2. BACKEND API & SECURITY
// ============================================================================
// Target Flask Ingestion Host (HTTPS production endpoint or HTTP development proxy)
#define BACKEND_HOST        "api.riversentinel.org"
#define BACKEND_PORT        443
#define USE_TLS             true
#define INGEST_ENDPOINT     "/api/v1/telemetry/ingest"

// Device Hardware Identification & Authentication
// Generated during administrative provisioning via backend/scripts/provision_device.py
#define DEVICE_CODE         "DEV-ESP32-ASSI-01"
#define DEVICE_TOKEN        "rs_dev_REPLACE_WITH_HIGH_ENTROPY_TOKEN"
#define FIRMWARE_VERSION    "v2.0.0-phase3a"
#define SCHEMA_VERSION      "2.0"

// ============================================================================
// 3. NTP TIME SYNCHRONIZATION
// ============================================================================
#define NTP_SERVER_PRIMARY  "pool.ntp.org"
#define NTP_SERVER_BACKUP   "time.google.com"
#define GMT_OFFSET_SEC      19800  // IST is UTC + 5:30 (5.5 * 3600 = 19800)
#define DAYLIGHT_OFFSET_SEC 0

// ============================================================================
// 4. SAMPLING INTERVALS & OFFLINE BUFFER
// ============================================================================
#define TELEMETRY_INTERVAL_MS   30000   // 30 seconds between sensor transmissions
#define OFFLINE_QUEUE_CAPACITY  50      // In-RAM circular buffer capacity (bounded)
#define RETRY_BACKOFF_BASE_MS   2000    // Exponential backoff base
#define RETRY_BACKOFF_MAX_MS    30000   // Max backoff ceiling

// ============================================================================
// 5. HARDWARE PIN ASSIGNMENTS (DRAFT / PENDING PHYSICAL VERIFICATION)
// Note: ESP32 ADC1 pins (GPIO 32-39) are preferred when Wi-Fi is active.
// ADC2 pins are unavailable while Wi-Fi transmitter is engaged.
// ============================================================================
#define PIN_STATUS_LED          2       // Onboard blue LED
#define PIN_BATTERY_ADC         34      // Voltage divider for battery sensing
#define PIN_PH_ANALOG           32      // pH Sensor analog output (Draft)
#define PIN_TURBIDITY_ANALOG    35      // Turbidity Sensor analog output (Draft)
#define PIN_TEMP_ONEWIRE        4       // DS18B20 digital bus (Draft)
#define PIN_EC_ANALOG           33      // Electrical Conductivity (Draft)
#define PIN_WATER_LEVEL_TRIG    5       // Ultrasonic Trigger (Draft)
#define PIN_WATER_LEVEL_ECHO    18      // Ultrasonic Echo (Draft)

#endif // CONFIG_H

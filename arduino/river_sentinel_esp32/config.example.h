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
// 2.1 TRUSTED ROOT CA CERTIFICATE (STRICT TLS VALIDATION)
// Standard ISRG Root X1 certificate for validating HTTPS endpoints.
// NEVER use setInsecure() in production.
// ============================================================================
static const char ROOT_CA_CERT[] PROGMEM = 
"-----BEGIN CERTIFICATE-----\n"
"MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRQB4+/SmAiMwDQYJKoZIhvcNAQELBQAw\n"
"TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh\n"
"cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4\n"
"WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu\n"
"ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY\n"
"MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oQ6HgJhmgCAZGl+8Z\n"
"nrvTy2dUOocKlq8AqGyqhWHTx24sbIG4ODAnCzmjeZvKDHxIDEGZUQ+/EI5qmpHD\n"
"3eGMU1Wefe9vdYJaGOVCClGPAbeshN77OXureBoImDG+88sp8JEGpfIA2V57QYTS\n"
"3g2OiBRWGDfMp+tubSfZELJvtkoUOvCE220Ldt6tAqhhnU59ZFsdTaJW40/Ns4OM\n"
"GptgJSi+DiDZexPR/INGLD85QnCQKEzyXZWqhKq7DoDGOTeye/tQpGicmgHQXptPY\n"
"gwFYF682bq87VTNWghstR+cBCgdfgkC6zEQzqORJE5BI5gLLEtQvbpfcSpTmpcVP\n"
"PamhU9QV80exPXKGAbMt6444oxZ8bIPhBQsnCgHXQFqdBehgOHzcEW8UTZXKePCv\n"
"GsXYSkTXWGA14gz6EC9UMn3ETcurcvVCdrlh9CQlmV400fZ31/ovVScWD5Sg5bpN\n"
"V69463qhUUAnKGv29QjA2uhjODAWvgkgMx8zAVCgAvGq5W2qVgnwDNt03nR8GqA1\n"
"GQhldvdQXOtVoAzM/+Pnmphm6vMq70Cuh11UpLCaOk6uvDYqOT08baMQAXyU69Z3\n"
"dXlhnD5076EDuiNmBOAZdZLO7qaWBqOvJzlDX6o379mVVC8TQj7UHRMB826Jwxq3\n"
"ZnU3YVUAO8VvfvZgePr2Pml0Z2OEqJBKhpd7iHNFeORpPprJzKSFuidbMbAFsjZ7\n"
"41nj8dd35qqit5KsNJKignqGQV25nC9kyvE569YhU3BpSODAZBSc3RJMGenyqpFj\n"
"bPnWTOH5RzeVJ+qDnUKxu860sJWWtzJKvd8LGLKEBA==\n"
"-----END CERTIFICATE-----\n";

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

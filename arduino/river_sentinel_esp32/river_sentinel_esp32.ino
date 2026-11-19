/*
 * River Sentinel 2.0 - ESP32-WROOM-32 Modular IoT Telemetry Node
 * Target Geography: Varanasi, Ganga River, Uttar Pradesh, India
 * 
 * Hardware Architecture:
 * - Microcontroller: ESP32-WROOM-32 (Xtensa dual-core 240MHz, 520KB SRAM)
 * - Security: HTTPS with Pre-Shared Key (SHA-256 header auth), zero-credential serial logging
 * - Reliability: SNTP UTC time sync, bounded offline queue, duplicate-safe retransmission
 * - Sensor Bus: Abstract ISensor driver interfaces, explicit quality & range checking
 */

#if __has_include("config.h")
#include "config.h"
#else
#include "config.example.h"
#endif

#include "wifi_manager.h"
#include "time_sync.h"
#include "device_auth.h"
#include "device_status.h"
#include "offline_queue.h"
#include "sensor_manager.h"
#include "telemetry_client.h"

// ============================================================================
// SYSTEM INSTANCES & GLOBAL STATE
// ============================================================================

WiFiManager wifiManager(WIFI_SSID, WIFI_PASSWORD, PIN_STATUS_LED);
TimeSyncManager timeSync;
DeviceAuth deviceAuth(DEVICE_CODE, DEVICE_TOKEN);
DeviceStatus deviceStatus(PIN_BATTERY_ADC);
OfflineQueue offlineQueue(OFFLINE_QUEUE_CAPACITY);
SensorManager sensorManager;
TelemetryClient telemetryClient(BACKEND_HOST, BACKEND_PORT, USE_TLS, INGEST_ENDPOINT, deviceAuth);

unsigned long lastSampleTime = 0;
unsigned long sequenceCounter = 1;

// Helper to generate a pseudorandom UUID v4 for message identification
String generateMessageUUID() {
    char uuidStr[37];
    uint32_t r1 = esp_random();
    uint32_t r2 = esp_random();
    uint32_t r3 = esp_random();
    uint32_t r4 = esp_random();

    snprintf(uuidStr, sizeof(uuidStr),
             "%08x-%04x-4%03x-%02x%02x-%08x%04x",
             r1,
             (uint16_t)(r2 >> 16),
             (uint16_t)(r2 & 0x0FFF),
             (uint8_t)((r3 >> 24) & 0x3F) | 0x80, // variant RFC 4122
             (uint8_t)((r3 >> 16) & 0xFF),
             r3,
             (uint16_t)r4);
    return String(uuidStr);
}

// ============================================================================
// SETUP
// ============================================================================

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println(F("\n========================================================"));
    Serial.println(F("🌊 River Sentinel 2.0 - ESP32 Telemetry Node Initializing"));
    Serial.println(F("========================================================"));

    deviceAuth.printRedactedIdentity();
    Serial.print(F("[System] Firmware Version: "));
    Serial.println(FIRMWARE_VERSION);

    // 1. Initialize Wi-Fi
    wifiManager.begin();

    // 2. Initialize Hardware Sensors
    deviceStatus.begin();
    sensorManager.begin();

    // 3. Synchronize UTC Time
    if (wifiManager.isConnected()) {
        timeSync.begin(NTP_SERVER_PRIMARY, NTP_SERVER_BACKUP, GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC);
    }

    Serial.println(F("[System] Node initialization completed. Entering main telemetry loop.\n"));
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
    // Background connection maintenance
    wifiManager.handleBackgroundReconnect();

    unsigned long currentMillis = millis();

    // Periodic telemetry sampling
    if (currentMillis - lastSampleTime >= TELEMETRY_INTERVAL_MS || lastSampleTime == 0) {
        lastSampleTime = currentMillis;

        Serial.println(F("\n------ SAMPLING TELEMETRY CYCLE ------"));
        String msgId = generateMessageUUID();
        String observedAt = timeSync.getISO8601UTC();
        float batteryPct = deviceStatus.getBatteryPercentage();

        // Sample attached sensors
        SensorBundle sensors = sensorManager.sampleAll();

        // Format Schema 2.0 JSON payload
        String payload = telemetryClient.formatPayload(
            msgId,
            sequenceCounter,
            observedAt,
            FIRMWARE_VERSION,
            sensors,
            batteryPct
        );

        // Also output structured JSON over Serial for debugging and Serial Bridge ingestion
        Serial.println(payload);

        // Transmit or Queue
        if (wifiManager.isConnected()) {
            // First flush any queued offline messages
            while (!offlineQueue.isEmpty()) {
                QueuedMessage qMsg;
                if (offlineQueue.peek(qMsg)) {
                    Serial.print(F("[Queue] Transmitting buffered message: "));
                    Serial.println(qMsg.messageId);
                    int res = telemetryClient.sendTelemetry(qMsg.jsonPayload);
                    if (res == 201 || res == 409) {
                        offlineQueue.dequeue();
                    } else {
                        Serial.println(F("[Queue] Buffered transmit failed. Retaining queue."));
                        break;
                    }
                }
            }

            // Transmit current message
            int res = telemetryClient.sendTelemetry(payload);
            if (res != 201 && res != 409) {
                // Buffer to offline queue if server error
                Serial.println(F("[System] Live send failed. Enqueueing to offline buffer."));
                offlineQueue.enqueue(msgId, sequenceCounter, payload);
            }
        } else {
            Serial.println(F("[WiFi] Disconnected. Enqueueing reading to offline buffer."));
            offlineQueue.enqueue(msgId, sequenceCounter, payload);
        }

        sequenceCounter++;
    }

    delay(100);
}

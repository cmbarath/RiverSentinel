#ifndef TELEMETRY_CLIENT_H
#define TELEMETRY_CLIENT_H

#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include "device_auth.h"
#include "sensor_manager.h"
#include "device_status.h"
#include "time_sync.h"

class TelemetryClient {
private:
    const char* _host;
    int _port;
    bool _useTls;
    const char* _endpoint;
    const DeviceAuth& _auth;
    const char* _caCert;

public:
    TelemetryClient(const char* host, int port, bool useTls, const char* endpoint, const DeviceAuth& auth, const char* caCert = nullptr)
        : _host(host), _port(port), _useTls(useTls), _endpoint(endpoint), _auth(auth), _caCert(caCert) {}

    String formatPayload(
        const String& messageId,
        unsigned long sequenceNumber,
        const String& observedAt,
        const char* firmwareVersion,
        const SensorBundle& sensors,
        float batteryPct
    ) {
        String json = "{";
        json += "\"schema_version\":\"2.0\",";
        json += "\"device_code\":\"" + String(_auth.getDeviceCode()) + "\",";
        json += "\"message_id\":\"" + messageId + "\",";
        json += "\"sequence_number\":" + String(sequenceNumber) + ",";
        json += "\"observed_at\":\"" + observedAt + "\",";
        json += "\"firmware_version\":\"" + String(firmwareVersion) + "\",";

        // Sensor readings object
        json += "\"sensor_readings\":{";
        bool first = true;
        if (String(sensors.ph_status) != "not_configured" && sensors.ph >= 0) {
            json += "\"ph\":" + String(sensors.ph, 2);
            first = false;
        }
        if (String(sensors.turbidity_status) != "not_configured" && sensors.turbidity >= 0) {
            if (!first) json += ",";
            json += "\"turbidity\":" + String(sensors.turbidity, 2);
            first = false;
        }
        if (String(sensors.temperature_status) != "not_configured" && sensors.temperature >= -50) {
            if (!first) json += ",";
            json += "\"temperature\":" + String(sensors.temperature, 2);
            first = false;
        }
        if (String(sensors.ec_status) != "not_configured" && sensors.ec >= 0) {
            if (!first) json += ",";
            json += "\"ec\":" + String(sensors.ec, 2);
            first = false;
        }
        if (String(sensors.water_level_status) != "not_configured" && sensors.water_level >= 0) {
            if (!first) json += ",";
            json += "\"water_level\":" + String(sensors.water_level, 2);
            first = false;
        }
        if (String(sensors.do_status) != "not_configured" && sensors.do_val >= 0) {
            if (!first) json += ",";
            json += "\"do\":" + String(sensors.do_val, 2);
            first = false;
        }
        if (batteryPct >= 0.0f) {
            if (!first) json += ",";
            json += "\"battery_pct\":" + String(batteryPct, 1);
        }
        json += "},";

        // Sensor status object
        json += "\"sensor_status\":{";
        json += "\"ph\":\"" + String(sensors.ph_status) + "\",";
        json += "\"turbidity\":\"" + String(sensors.turbidity_status) + "\",";
        json += "\"temperature\":\"" + String(sensors.temperature_status) + "\",";
        json += "\"ec\":\"" + String(sensors.ec_status) + "\",";
        json += "\"water_level\":\"" + String(sensors.water_level_status) + "\",";
        json += "\"do\":\"" + String(sensors.do_status) + "\"";
        json += "}";

        json += "}";
        return json;
    }

    int sendTelemetry(const String& jsonPayload) {
        WiFiClient* client = nullptr;
        WiFiClientSecure secureClient;
        WiFiClient plainClient;

        if (_useTls) {
            // Strict Certificate Validation:
            // 1. Verify NTP clock is synchronized prior to TLS handshake.
            time_t now = time(nullptr);
            if (now < 1700000000) { // Timestamp before Nov 2023 indicates uninitialized RTC
                Serial.println(F("[TLS] ❌ Error: NTP time not synchronized. Refusing TLS connection without valid clock to prevent accepting expired or forged certificates."));
                return -2;
            }

            // 2. Set trusted root CA certificate (NEVER use setInsecure)
            if (_caCert != nullptr && strlen(_caCert) > 0) {
                secureClient.setCACert(_caCert);
            } else {
                Serial.println(F("[TLS] ❌ Error: No Root CA certificate configured for HTTPS validation. Rejecting insecure connection."));
                return -3;
            }

            secureClient.setTimeout(8);
            client = &secureClient;
        } else {
            plainClient.setTimeout(5);
            client = &plainClient;
        }

        HTTPClient http;
        String protocol = _useTls ? "https://" : "http://";
        String url = protocol + String(_host) + ":" + String(_port) + String(_endpoint);

        if (!http.begin(*client, url)) {
            Serial.println(F("[HTTP] Failed to initialize connection to ingestion endpoint."));
            return -1;
        }

        http.addHeader("Content-Type", "application/json");
        http.addHeader("X-Device-Code", _auth.getDeviceCode());
        http.addHeader("X-Device-Token", _auth.getDeviceToken());

        int httpResponseCode = http.POST(jsonPayload);

        if (httpResponseCode == 201) {
            Serial.println(F("[HTTP] ✅ Telemetry accepted by backend (201 Created)."));
        } else if (httpResponseCode == 200) {
            Serial.println(F("[HTTP] ℹ️ Duplicate message already persisted by backend (200 OK duplicate acknowledged)."));
        } else if (httpResponseCode == 409) {
            Serial.println(F("[HTTP] ℹ️ Duplicate message conflict acknowledged by server (409 Conflict)."));
        } else if (httpResponseCode == 401 || httpResponseCode == 403) {
            Serial.print(F("[HTTP] ❌ Authorization failed (HTTP "));
            Serial.print(httpResponseCode);
            Serial.println(F("): Device credential invalid or revoked."));
        } else {
            Serial.print(F("[HTTP] ⚠️ Telemetry transmission error: HTTP "));
            Serial.println(httpResponseCode);
            String respBody = http.getString();
            if (respBody.length() > 0) {
                Serial.print(F("[HTTP Response] "));
                Serial.println(respBody.substring(0, 100));
            }
        }

        http.end();
        return httpResponseCode;
    }
};

#endif // TELEMETRY_CLIENT_H

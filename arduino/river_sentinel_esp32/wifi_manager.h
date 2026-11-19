#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <WiFi.h>

class WiFiManager {
private:
    const char* _ssid;
    const char* _password;
    int _statusLedPin;
    unsigned long _lastReconnectAttempt;
    int _retryCount;

public:
    WiFiManager(const char* ssid, const char* password, int statusLedPin = -1)
        : _ssid(ssid), _password(password), _statusLedPin(statusLedPin),
          _lastReconnectAttempt(0), _retryCount(0) {}

    void begin() {
        if (_statusLedPin >= 0) {
            pinMode(_statusLedPin, OUTPUT);
            digitalWrite(_statusLedPin, LOW);
        }
        Serial.print(F("[WiFi] Initializing connection to SSID: "));
        Serial.println(_ssid);

        WiFi.mode(WIFI_STA);
        WiFi.begin(_ssid, _password);

        int attempts = 0;
        while (WiFi.status() != WL_CONNECTED && attempts < 30) {
            delay(500);
            Serial.print(F("."));
            if (_statusLedPin >= 0) {
                digitalWrite(_statusLedPin, !digitalRead(_statusLedPin));
            }
            attempts++;
        }

        if (WiFi.status() == WL_CONNECTED) {
            Serial.println(F("\n[WiFi] Connected successfully!"));
            Serial.print(F("[WiFi] IP Address: "));
            Serial.println(WiFi.localIP());
            Serial.print(F("[WiFi] Signal RSSI: "));
            Serial.print(WiFi.RSSI());
            Serial.println(F(" dBm"));
            if (_statusLedPin >= 0) digitalWrite(_statusLedPin, HIGH);
        } else {
            Serial.println(F("\n[WiFi] Initial connection timed out. Background retry enabled."));
            if (_statusLedPin >= 0) digitalWrite(_statusLedPin, LOW);
        }
    }

    bool isConnected() {
        return (WiFi.status() == WL_CONNECTED);
    }

    void handleBackgroundReconnect() {
        if (isConnected()) {
            _retryCount = 0;
            return;
        }

        unsigned long now = millis();
        // Exponential backoff up to 60 seconds
        unsigned long backoff = min(60000UL, (1000UL << min(_retryCount, 6)));

        if (now - _lastReconnectAttempt >= backoff) {
            _lastReconnectAttempt = now;
            _retryCount++;
            Serial.print(F("[WiFi] Disconnected. Reconnect attempt #"));
            Serial.print(_retryCount);
            Serial.print(F(" (backoff: "));
            Serial.print(backoff / 1000);
            Serial.println(F("s)..."));

            WiFi.reconnect();
        }
    }

    int getRSSI() {
        return isConnected() ? WiFi.RSSI() : -100;
    }
};

#endif // WIFI_MANAGER_H

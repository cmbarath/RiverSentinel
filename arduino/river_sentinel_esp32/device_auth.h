#ifndef DEVICE_AUTH_H
#define DEVICE_AUTH_H

#include <Arduino.h>

class DeviceAuth {
private:
    const char* _deviceCode;
    const char* _deviceToken;

public:
    DeviceAuth(const char* deviceCode, const char* deviceToken)
        : _deviceCode(deviceCode), _deviceToken(deviceToken) {}

    const char* getDeviceCode() const {
        return _deviceCode;
    }

    const char* getDeviceToken() const {
        return _deviceToken;
    }

    void printRedactedIdentity() const {
        Serial.print(F("[Auth] Device Code: "));
        Serial.println(_deviceCode);
        Serial.print(F("[Auth] Pre-Shared Token: "));
        int len = strlen(_deviceToken);
        if (len > 10) {
            for (int i = 0; i < 7; i++) Serial.print(_deviceToken[i]);
            Serial.print(F("...[REDACTED]..."));
            for (int i = len - 4; i < len; i++) Serial.print(_deviceToken[i]);
            Serial.println();
        } else {
            Serial.println(F("[CONFIGURED]"));
        }
    }
};

#endif // DEVICE_AUTH_H

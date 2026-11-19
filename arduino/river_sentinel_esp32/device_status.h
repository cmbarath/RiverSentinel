#ifndef DEVICE_STATUS_H
#define DEVICE_STATUS_H

#include <Arduino.h>
#include <esp_system.h>

class DeviceStatus {
private:
    int _batteryAdcPin;
    float _voltageDividerRatio;

public:
    DeviceStatus(int batteryAdcPin = -1, float voltageDividerRatio = 2.0f)
        : _batteryAdcPin(batteryAdcPin), _voltageDividerRatio(voltageDividerRatio) {}

    void begin() {
        if (_batteryAdcPin >= 0) {
            analogSetAttenuation(ADC_11db); // 0-3.3V range
            pinMode(_batteryAdcPin, INPUT);
        }
    }

    uint32_t getFreeHeapBytes() {
        return esp_get_free_heap_size();
    }

    unsigned long getUptimeSeconds() {
        return millis() / 1000UL;
    }

    float getBatteryVoltage() {
        if (_batteryAdcPin < 0) return -1.0f;
        int raw = analogRead(_batteryAdcPin);
        float pinVoltage = (raw / 4095.0f) * 3.3f;
        return pinVoltage * _voltageDividerRatio;
    }

    float getBatteryPercentage() {
        float voltage = getBatteryVoltage();
        if (voltage < 0.0f) return -1.0f; // Sensor not equipped
        // Approximate 1S Li-Ion curve: 3.2V (0%) to 4.2V (100%)
        if (voltage >= 4.2f) return 100.0f;
        if (voltage <= 3.2f) return 0.0f;
        return (voltage - 3.2f) / (4.2f - 3.2f) * 100.0f;
    }
};

#endif // DEVICE_STATUS_H

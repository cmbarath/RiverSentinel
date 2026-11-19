#ifndef I_SENSOR_H
#define I_SENSOR_H

#include <Arduino.h>

enum SensorQuality {
    QUALITY_VALID,
    QUALITY_OUT_OF_RANGE,
    QUALITY_DISCONNECTED,
    QUALITY_UNCALIBRATED,
    QUALITY_NOT_CONFIGURED
};

class ISensor {
public:
    virtual ~ISensor() {}
    virtual bool begin() = 0;
    virtual bool isConfigured() = 0;
    virtual float readValue() = 0;
    virtual SensorQuality getStatus() = 0;
    virtual const char* getName() = 0;
    virtual const char* getUnit() = 0;
    virtual const char* getStatusString() {
        switch (getStatus()) {
            case QUALITY_VALID: return "valid";
            case QUALITY_OUT_OF_RANGE: return "out_of_range";
            case QUALITY_DISCONNECTED: return "disconnected";
            case QUALITY_UNCALIBRATED: return "uncalibrated";
            case QUALITY_NOT_CONFIGURED: return "not_configured";
            default: return "suspect";
        }
    }
};

#endif // I_SENSOR_H

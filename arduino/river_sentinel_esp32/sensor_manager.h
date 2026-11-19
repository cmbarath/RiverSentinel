#ifndef SENSOR_MANAGER_H
#define SENSOR_MANAGER_H

#include "sensor_interfaces/ISensor.h"

struct SensorBundle {
    float ph;
    const char* ph_status;
    float turbidity;
    const char* turbidity_status;
    float temperature;
    const char* temperature_status;
    float ec;
    const char* ec_status;
    float water_level;
    const char* water_level_status;
    float do_val;
    const char* do_status;
};

class SensorManager {
private:
    ISensor* _phSensor;
    ISensor* _turbiditySensor;
    ISensor* _tempSensor;
    ISensor* _ecSensor;
    ISensor* _waterLevelSensor;
    ISensor* _doSensor;

public:
    SensorManager()
        : _phSensor(nullptr), _turbiditySensor(nullptr), _tempSensor(nullptr),
          _ecSensor(nullptr), _waterLevelSensor(nullptr), _doSensor(nullptr) {}

    void setPHSensor(ISensor* s) { _phSensor = s; }
    void setTurbiditySensor(ISensor* s) { _turbiditySensor = s; }
    void setTempSensor(ISensor* s) { _tempSensor = s; }
    void setECSensor(ISensor* s) { _ecSensor = s; }
    void setWaterLevelSensor(ISensor* s) { _waterLevelSensor = s; }
    void setDOSensor(ISensor* s) { _doSensor = s; }

    void begin() {
        Serial.println(F("[SensorManager] Initializing attached sensor drivers..."));
        if (_phSensor && _phSensor->isConfigured()) _phSensor->begin();
        if (_turbiditySensor && _turbiditySensor->isConfigured()) _turbiditySensor->begin();
        if (_tempSensor && _tempSensor->isConfigured()) _tempSensor->begin();
        if (_ecSensor && _ecSensor->isConfigured()) _ecSensor->begin();
        if (_waterLevelSensor && _waterLevelSensor->isConfigured()) _waterLevelSensor->begin();
        if (_doSensor && _doSensor->isConfigured()) _doSensor->begin();
    }

    SensorBundle sampleAll() {
        SensorBundle bundle;

        // pH
        if (_phSensor && _phSensor->isConfigured()) {
            bundle.ph = _phSensor->readValue();
            bundle.ph_status = _phSensor->getStatusString();
        } else {
            bundle.ph = -1.0f;
            bundle.ph_status = "not_configured";
        }

        // Turbidity
        if (_turbiditySensor && _turbiditySensor->isConfigured()) {
            bundle.turbidity = _turbiditySensor->readValue();
            bundle.turbidity_status = _turbiditySensor->getStatusString();
        } else {
            bundle.turbidity = -1.0f;
            bundle.turbidity_status = "not_configured";
        }

        // Temperature
        if (_tempSensor && _tempSensor->isConfigured()) {
            bundle.temperature = _tempSensor->readValue();
            bundle.temperature_status = _tempSensor->getStatusString();
        } else {
            bundle.temperature = -1.0f;
            bundle.temperature_status = "not_configured";
        }

        // Electrical Conductivity (EC)
        if (_ecSensor && _ecSensor->isConfigured()) {
            bundle.ec = _ecSensor->readValue();
            bundle.ec_status = _ecSensor->getStatusString();
        } else {
            bundle.ec = -1.0f;
            bundle.ec_status = "not_configured";
        }

        // Water Level
        if (_waterLevelSensor && _waterLevelSensor->isConfigured()) {
            bundle.water_level = _waterLevelSensor->readValue();
            bundle.water_level_status = _waterLevelSensor->getStatusString();
        } else {
            bundle.water_level = -1.0f;
            bundle.water_level_status = "not_configured";
        }

        // Dissolved Oxygen
        if (_doSensor && _doSensor->isConfigured()) {
            bundle.do_val = _doSensor->readValue();
            bundle.do_status = _doSensor->getStatusString();
        } else {
            bundle.do_val = -1.0f;
            bundle.do_status = "not_configured";
        }

        return bundle;
    }
};

#endif // SENSOR_MANAGER_H

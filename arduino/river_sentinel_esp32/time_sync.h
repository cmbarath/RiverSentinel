#ifndef TIME_SYNC_H
#define TIME_SYNC_H

#include <time.h>
#include <Arduino.h>

class TimeSyncManager {
private:
    bool _isSynced;
    unsigned long _lastSyncCheck;

public:
    TimeSyncManager() : _isSynced(false), _lastSyncCheck(0) {}

    void begin(const char* ntpServerPrimary, const char* ntpServerBackup = nullptr, long gmtOffsetSec = 19800, int daylightOffsetSec = 0) {
        Serial.print(F("[TimeSync] Initializing SNTP with: "));
        Serial.println(ntpServerPrimary);

        configTime(gmtOffsetSec, daylightOffsetSec, ntpServerPrimary, ntpServerBackup);
        syncTime(10);
    }

    bool syncTime(int maxSecondsWait = 10) {
        struct tm timeinfo;
        int attempts = 0;
        while (!getLocalTime(&timeinfo) && attempts < maxSecondsWait * 2) {
            delay(500);
            attempts++;
        }

        if (getLocalTime(&timeinfo)) {
            _isSynced = true;
            char timeStr[64];
            strftime(timeStr, sizeof(timeStr), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
            Serial.print(F("[TimeSync] Clock synchronized: "));
            Serial.println(timeStr);
            return true;
        }

        _isSynced = false;
        Serial.println(F("[TimeSync] ⚠️ Warning: Failed to obtain NTP time. Operating on unsynchronized local clock."));
        return false;
    }

    bool isSynchronized() {
        return _isSynced;
    }

    String getISO8601UTC() {
        time_t now;
        time(&now);
        struct tm* utc = gmtime(&now);

        char buf[30];
        if (_isSynced && utc && utc->tm_year > (2020 - 1900)) {
            strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", utc);
            return String(buf);
        }

        // Fallback for unsynchronized clock: return 1970 baseline with millis offset
        snprintf(buf, sizeof(buf), "1970-01-01T00:00:%02luZ", (millis() / 1000) % 60);
        return String(buf);
    }

    const char* getTimeQuality() {
        return _isSynced ? "synced_utc" : "unsynchronized_local";
    }
};

#endif // TIME_SYNC_H

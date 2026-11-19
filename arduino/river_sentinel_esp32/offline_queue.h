#ifndef OFFLINE_QUEUE_H
#define OFFLINE_QUEUE_H

#include <Arduino.h>

struct QueuedMessage {
    String messageId;
    unsigned long sequenceNumber;
    String jsonPayload;
    bool inUse;
};

class OfflineQueue {
private:
    int _capacity;
    QueuedMessage* _buffer;
    int _head;
    int _tail;
    int _count;

public:
    OfflineQueue(int capacity = 50) : _capacity(capacity), _head(0), _tail(0), _count(0) {
        _buffer = new QueuedMessage[_capacity];
        for (int i = 0; i < _capacity; i++) {
            _buffer[i].inUse = false;
        }
    }

    ~OfflineQueue() {
        delete[] _buffer;
    }

    bool enqueue(const String& messageId, unsigned long seq, const String& jsonPayload) {
        if (_count >= _capacity) {
            // Drop oldest item to prevent memory exhaustion and flash wear
            Serial.println(F("[Queue] ⚠️ Buffer full. Dropping oldest untransmitted message."));
            dequeue();
        }

        _buffer[_tail].messageId = messageId;
        _buffer[_tail].sequenceNumber = seq;
        _buffer[_tail].jsonPayload = jsonPayload;
        _buffer[_tail].inUse = true;

        _tail = (_tail + 1) % _capacity;
        _count++;
        return true;
    }

    bool peek(QueuedMessage& outMessage) {
        if (_count == 0) return false;
        outMessage = _buffer[_head];
        return true;
    }

    bool dequeue() {
        if (_count == 0) return false;
        _buffer[_head].inUse = false;
        _buffer[_head].jsonPayload = "";
        _head = (_head + 1) % _capacity;
        _count--;
        return true;
    }

    int count() const {
        return _count;
    }

    bool isEmpty() const {
        return (_count == 0);
    }
};

#endif // OFFLINE_QUEUE_H

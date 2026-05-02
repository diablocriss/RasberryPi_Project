#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include "config.h"
#include "motor.h"

// ─── Khởi tạo UART ───────────────────────────────────────────────────────────
inline void command_init() {
    Serial1.begin(UART_BAUD, SERIAL_8N1, PIN_UART_RX, PIN_UART_TX);
}

// ─── Xử lý 1 dòng JSON ───────────────────────────────────────────────────────
// Khớp với các packet FsdTree gửi từ Pi:
//   {"cmd":"MOVE","dir":"FORWARD","speed":120,"time_ms":1000}
//   {"cmd":"TURN","dir":"LEFT","speed":120,"time_ms":1000}
//   {"cmd":"STOP","reason":"USER_COMMAND"}
//   {"cmd":"SPEED","delta":10}
//   {"cmd":"REJECT","reason":"UNKNOWN_COMMAND","text":"..."}
static void _handle_json(const char* json_str) {
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, json_str);

    if (err) {
        Serial0.printf("[CMD] Parse error: %s | raw: %s\n", err.c_str(), json_str);
        return;
    }

    // In nguyên chuỗi JSON nhận được từ Pi
    Serial0.printf("[CMD] << %s\n", json_str);
}

// ─── Gọi trong loop() — đọc từng dòng kết thúc '\n' ─────────────────────────
static String _uart_buf;

inline void command_tick() {
    while (Serial1.available()) {
        char c = (char)Serial1.read();
        if (c == '\n') {
            _uart_buf.trim();
            if (_uart_buf.length() > 0) {
                _handle_json(_uart_buf.c_str());
            }
            _uart_buf = "";
        } else {
            _uart_buf += c;
            // Tránh tràn buffer nếu Pi gửi sai format
            if (_uart_buf.length() > 256) _uart_buf = "";
        }
    }
}

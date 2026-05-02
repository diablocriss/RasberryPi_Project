#pragma once

// ─── I2S Microphone (INMP441) ────────────────────────────────────────────────
#define I2S_PORT            I2S_NUM_0
#define PIN_I2S_BCK         17      // SCK  → GPIO17
#define PIN_I2S_WS          18      // WS   → GPIO18
#define PIN_I2S_DATA_IN     16      // SD   → GPIO16

#define AUDIO_SAMPLE_RATE   16000
#define AUDIO_BITS          16
#define AUDIO_CHANNELS      1

#define FRAME_SAMPLES       256
#define FRAME_BYTES         (FRAME_SAMPLES * 2)   // 512 bytes

// ─── USB CDC (Audio → Pi) ────────────────────────────────────────────────────
// ESP32-S3 native USB, baud rate không ảnh hưởng nhưng để khớp settings.py
#define USB_CDC_BAUD        921600

// Frame protocol: [0xAA][0x55][len_lo][len_hi][...payload...][checksum]
#define FRAME_HEADER_0      0xAA
#define FRAME_HEADER_1      0x55

// ─── UART (Pi → ESP32, JSON lệnh điều khiển) ─────────────────────────────────
#define UART_NUM            1           // dùng Serial1
#define PIN_UART_RX         8
#define PIN_UART_TX         9
#define UART_BAUD           115200

// ─── Motor / Relay (stub — đổi theo hardware thực tế) ────────────────────────
#define PIN_MOTOR_IN1       4
#define PIN_MOTOR_IN2       5
#define PIN_MOTOR_IN3       6
#define PIN_MOTOR_IN4       7

#define DEFAULT_SPEED       120         // khớp ROBOT_DEFAULT_SPEED Pi
#define DEFAULT_MOVE_MS     1000        // khớp ROBOT_DEFAULT_MOVE_TIME_MS Pi

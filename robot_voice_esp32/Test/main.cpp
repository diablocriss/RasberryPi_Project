//  ███████╗███████╗██████╗ ██████╗ ██████╗     ██████╗  ██████╗ ██████╗  ██████╗ ████████╗
//  ██╔════╝██╔════╝██╔══██╗╚════██╗╚════██╗    ██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗╚══██╔══╝
//  █████╗  ███████╗██████╔╝ █████╔╝ █████╔╝    ██████╔╝██║   ██║██████╔╝██║   ██║   ██║
//  ██╔══╝  ╚════██║██╔═══╝  ╚═══██╗██╔═══╝     ██╔══██╗██║   ██║██╔══██╗██║   ██║   ██║
//  ███████╗███████║██║     ██████╔╝███████╗     ██║  ██║╚██████╔╝██████╔╝╚██████╔╝   ██║
//  ╚══════╝╚══════╝╚═╝     ╚═════╝ ╚══════╝     ╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝   ╚═╝
//
//  ESP32-S3 N16R8  |  I2S Mic → USB CDC → Pi STT/FSD → UART JSON → Motor
//  Mirror của audio_pipeline() bên Pi (pipeline.py)

#include <Arduino.h>
#include "config.h"
#include "audio_sender.h"      // I2S + USB CDC framing
#include "command_handler.h"   // UART JSON parser + motor dispatch
#include "motor.h"             // motor stubs

// ─── Diagnostics ─────────────────────────────────────────────────────────────
static void print_banner() {
    // Serial ở đây là USB CDC (ARDUINO_USB_CDC_ON_BOOT=1)
    Serial0.println("  ESP32-S3 Robot Voice Controller");
    Serial0.println("  I2S -> USB CDC -> Pi STT -> UART JSON");
    Serial0.println("========================================");
    Serial0.printf("  Flash  : 16 MB\n");
    Serial0.printf("  PSRAM  : 8 MB (OPI)\n");
    Serial0.printf("  I2S    : BCK=%d WS=%d DIN=%d SR=%d Hz\n",
                  PIN_I2S_BCK, PIN_I2S_WS, PIN_I2S_DATA_IN, AUDIO_SAMPLE_RATE);
    Serial0.printf("  UART   : RX=%d TX=%d @ %d baud\n",
                  PIN_UART_RX, PIN_UART_TX, UART_BAUD);
    Serial0.printf("  Frame  : %d bytes (%d samples)\n", FRAME_BYTES, FRAME_SAMPLES);
    Serial0.println("========================================");
}

// ─── setup() ─────────────────────────────────────────────────────────────────
void setup() {
    // USB CDC — dùng làm audio stream + debug log
    // Không cần Serial.begin() khi ARDUINO_USB_CDC_ON_BOOT=1,
    // nhưng gọi để set timeout chờ host connect
    Serial0.begin(115200);   // debug log riêng — xem qua UART0 pin TX=43
    Serial.begin(0);
    delay(1500);    // chờ PC/Pi mở cổng CDC

    print_banner();

    motor_init();
    audio_init();
    command_init();

    Serial0.println("[BOOT] Ready.");
}

// ─── loop() ──────────────────────────────────────────────────────────────────
void loop() {
    // 1. Đọc I2S → đóng gói frame → gửi Pi qua USB CDC
    audio_tick();

    // 2. Nhận JSON từ Pi qua UART → dispatch motor
    command_tick();

    // Không delay — audio_tick() đã block tối đa 100ms chờ DMA
}

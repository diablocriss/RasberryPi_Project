#pragma once
#include <Arduino.h>
#include <driver/i2s.h>
#include "config.h"

// ─── Khởi tạo I2S ────────────────────────────────────────────────────────────
inline void audio_init() {
    i2s_config_t i2s_cfg = {
        .mode                 = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate          = AUDIO_SAMPLE_RATE,
        .bits_per_sample      = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format       = I2S_CHANNEL_FMT_ONLY_RIGHT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags     = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count        = 4,
        .dma_buf_len          = FRAME_SAMPLES,
        .use_apll             = false,
        .tx_desc_auto_clear   = false,
        .fixed_mclk           = 0,
    };
    i2s_pin_config_t pin_cfg = {
        .mck_io_num   = I2S_PIN_NO_CHANGE,
        .bck_io_num   = PIN_I2S_BCK,
        .ws_io_num    = PIN_I2S_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num  = PIN_I2S_DATA_IN,
    };
    i2s_driver_install(I2S_PORT, &i2s_cfg, 0, NULL);
    i2s_set_pin(I2S_PORT, &pin_cfg);
    i2s_zero_dma_buffer(I2S_PORT);
}

// ─── Tính checksum (khớp compute_checksum trong usb_cdc_audio.py) ────────────
inline uint8_t compute_checksum(const uint8_t* data, uint16_t len) {
    uint32_t s = 0;
    for (uint16_t i = 0; i < len; i++) s += data[i];
    return (uint8_t)(s & 0xFF);
}

// ─── Đóng gói và gửi 1 frame qua USB CDC ─────────────────────────────────────
//  Format: [0xAA][0x55][len_lo][len_hi][payload × len][checksum]
inline void send_audio_frame(const uint8_t* payload, uint16_t len) {
    uint8_t header[4] = {
        FRAME_HEADER_0,
        FRAME_HEADER_1,
        (uint8_t)(len & 0xFF),
        (uint8_t)((len >> 8) & 0xFF),
    };
    Serial.write(header, 4);          // Serial = USB CDC trên S3
    Serial.write(payload, len);
    Serial.write(compute_checksum(payload, len));
}

// ─── Đọc 1 frame I2S rồi gửi đi ─────────────────────────────────────────────
static int16_t _i2s_buf[FRAME_SAMPLES];

inline void audio_tick() {
    size_t bytes_read = 0;
    esp_err_t err = i2s_read(I2S_PORT, _i2s_buf, FRAME_BYTES,
                             &bytes_read, pdMS_TO_TICKS(100));
    if (err != ESP_OK || bytes_read == 0) return;

    send_audio_frame((const uint8_t*)_i2s_buf, (uint16_t)bytes_read);
}

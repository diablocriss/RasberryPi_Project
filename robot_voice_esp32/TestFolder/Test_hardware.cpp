//  ╔══════════════════════════════════════════════════════╗
//  ║   INMP441 MIC TEST — ESP32-S3                       ║
//  ║   Hiển thị dB meter + waveform trên Serial Monitor  ║
//  ╚══════════════════════════════════════════════════════╝
//  Pin: SCK=17  WS=18  SD=16  L/R=GND

#include <Arduino.h>
#include <driver/i2s.h>
#include <math.h>

// ─── Pin & I2S config ────────────────────────────────────────────────────────
#define PIN_BCK         17
#define PIN_WS          18
#define PIN_DATA_IN     16
#define I2S_PORT        I2S_NUM_0
#define SAMPLE_RATE     16000
#define FRAME_SAMPLES   256

// ─── Hiển thị ────────────────────────────────────────────────────────────────
#define DB_MIN          -60.0f      // dB sàn (im lặng)
#define DB_MAX            0.0f      // dB đỉnh (clip)
#define BAR_WIDTH          40       // độ rộng thanh bar
#define PRINT_INTERVAL_MS  80       // refresh ~12fps

// ─── Buffer ──────────────────────────────────────────────────────────────────
static int16_t _buf[FRAME_SAMPLES];

// ─── I2S init ────────────────────────────────────────────────────────────────
void i2s_init() {
    i2s_config_t cfg = {
        .mode                 = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate          = SAMPLE_RATE,
        .bits_per_sample      = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format       = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags     = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count        = 4,
        .dma_buf_len          = FRAME_SAMPLES,
        .use_apll             = false,
    };
    i2s_pin_config_t pins = {
        .mck_io_num   = I2S_PIN_NO_CHANGE,
        .bck_io_num   = PIN_BCK,
        .ws_io_num    = PIN_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num  = PIN_DATA_IN,
    };
    i2s_driver_install(I2S_PORT, &cfg, 0, NULL);
    i2s_set_pin(I2S_PORT, &pins);
    i2s_zero_dma_buffer(I2S_PORT);
}

// ─── Tính RMS và đổi sang dB ─────────────────────────────────────────────────
float calc_db(const int16_t* samples, int count) {
    double sum = 0;
    for (int i = 0; i < count; i++) {
        sum += (double)samples[i] * samples[i];
    }
    double rms = sqrt(sum / count);
    if (rms < 1.0) return DB_MIN;
    // 32768 = full scale int16
    return 20.0f * log10f((float)rms / 32768.0f);
}

// ─── Vẽ thanh dB ─────────────────────────────────────────────────────────────
void print_db_bar(float db) {
    // Clamp
    if (db < DB_MIN) db = DB_MIN;
    if (db > DB_MAX) db = DB_MAX;

    int filled = (int)((db - DB_MIN) / (DB_MAX - DB_MIN) * BAR_WIDTH);

    // Màu zone: xanh / vàng / đỏ
    // Serial Monitor thường không hỗ trợ ANSI color
    // nhưng VS Code terminal và PlatformIO monitor thì có
    String bar = "";
    for (int i = 0; i < BAR_WIDTH; i++) {
        if (i < filled) {
            if (i < BAR_WIDTH * 0.6)      bar += "█";   // xanh zone
            else if (i < BAR_WIDTH * 0.85) bar += "▓";   // vàng zone
            else                           bar += "░";   // đỏ zone (clip)
        } else {
            bar += " ";
        }
    }

    // Waveform mini: lấy 1 sample mỗi 16 để vẽ oscilloscope
    String wave = "";
    for (int i = 0; i < FRAME_SAMPLES; i += 16) {
        int v = map(_buf[i], -32768, 32767, 0, 8);
        wave += (char)('0' + v);
    }

    // In 1 dòng, dùng \r để overwrite
    Serial.printf("\r  dB: [%s] %+6.1f dB   wave: %s   ",
                  bar.c_str(), db, wave.c_str());
}

// ─── Peak hold ───────────────────────────────────────────────────────────────
static float _peak_db   = DB_MIN;
static uint32_t _peak_t = 0;
#define PEAK_HOLD_MS 2000

void print_stats(float db) {
    uint32_t now = millis();
    if (db > _peak_db) {
        _peak_db = db;
        _peak_t  = now;
    }
    // decay sau 2s
    if (now - _peak_t > PEAK_HOLD_MS) {
        _peak_db -= 0.5f;
        if (_peak_db < DB_MIN) _peak_db = DB_MIN;
    }
    print_db_bar(db);
    Serial.printf(" peak: %+5.1f dB", _peak_db);
}

// ─── setup / loop ─────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(0);
    delay(1500);

    Serial.println("\n\n");
    Serial.println("╔══════════════════════════════════════════╗");
    Serial.println("║  INMP441 Mic Test  |  ESP32-S3           ║");
    Serial.printf ("║  SCK=%d  WS=%d  SD=%d  SR=%dHz       ║\n",
                   PIN_BCK, PIN_WS, PIN_DATA_IN, SAMPLE_RATE);
    Serial.println("╚══════════════════════════════════════════╝");
    Serial.println("  Nói vào mic để thấy thanh dB thay đổi");
    Serial.println("  Gõ lệnh: 'info' để xem chi tiết frame\n");

    i2s_init();
    Serial.println("[I2S] Ready.\n");
}

static uint32_t _last_print = 0;
static uint32_t _frame_count = 0;
static bool _show_info = false;

void loop() {
    // ── Đọc lệnh từ Serial Monitor ──
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        if (cmd == "info") _show_info = !_show_info;
        if (cmd == "reset_peak") _peak_db = DB_MIN;
    }

    // ── Đọc I2S ──
    size_t bytes_read = 0;
    i2s_read(I2S_PORT, _buf, sizeof(_buf), &bytes_read, pdMS_TO_TICKS(50));
    if (bytes_read == 0) return;
    _frame_count++;

    // ── In dB bar ──
    uint32_t now = millis();
    if (now - _last_print < PRINT_INTERVAL_MS) return;
    _last_print = now;

    float db = calc_db(_buf, bytes_read / 2);
    print_stats(db);

    // ── Chế độ info ──
    if (_show_info) {
        Serial.println();
        int16_t vmin = _buf[0], vmax = _buf[0];
        for (int i = 1; i < (int)(bytes_read/2); i++) {
            if (_buf[i] < vmin) vmin = _buf[i];
            if (_buf[i] > vmax) vmax = _buf[i];
        }
        Serial.printf("  [INFO] samples=%d  min=%d  max=%d  frames_total=%lu\n",
                      (int)(bytes_read/2), vmin, vmax, _frame_count);
    }
}

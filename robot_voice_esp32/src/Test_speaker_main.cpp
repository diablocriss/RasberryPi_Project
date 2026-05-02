//  SAM TTS — ESP32-S3 N16R8 + MAX98357A
//  Không dùng AudioTools → tránh global constructor crash
//  SAM viết vào I2SPrint (subclass Print) → raw ESP-IDF I2S driver
//
//  BCLK=17  LRC=18  DIN=15
//  Lệnh: <text>  :speed N  :pitch N  :voice <sam|elf|robot|oldlady|et>  :test  :info

#include <Arduino.h>
#include <driver/i2s.h>
#include "sam_arduino.h"

// ─── Pin ─────────────────────────────────────────────────────────────────────
#define PIN_BCLK     17
#define PIN_LRC      18
#define PIN_DIN      15
#define I2S_PORT     I2S_NUM_0

// SAM xuất 8-bit unsigned PCM @ 22050Hz mono
#define SAM_SR       22050
#define SAM_BITS     8
#define SAM_CH       1

// ─── Custom Print → I2S ──────────────────────────────────────────────────────
// SAM gọi write(buf, len) với dữ liệu 8-bit unsigned.
// MAX98357A cần 16-bit signed → convert inline.
class I2SPrint : public Print {
public:
    size_t write(uint8_t b) override {
        return write(&b, 1);
    }
    size_t write(const uint8_t* buf, size_t len) override {
        // Convert block: uint8 → int16
        // (sample - 128) << 8  →  maps [0,255] → [-32768,32512]
        static int16_t tmp[1024];
        size_t sent = 0;
        while (sent < len) {
            size_t n = min(len - sent, (size_t)256);
            for (size_t i = 0; i < n; i++)
                tmp[i] = (int16_t)((int)buf[sent+i] - 128) << 7;
            size_t written = 0;
            i2s_write(I2S_PORT, tmp, n * 2, &written, pdMS_TO_TICKS(200));
            sent += n;
        }
        return sent;
    }
};

// ─── Globals — chỉ là POD/pointer, không có constructor phức tạp ──────────────
static I2SPrint  i2s_print;   // không có constructor body → an toàn
static SAM*      p_sam = nullptr;

static uint8_t g_speed = 72, g_pitch = 64, g_throat = 128, g_mouth = 128;
static String  g_voice = "sam";

// ─── Preset ───────────────────────────────────────────────────────────────────
struct VP { const char* n; uint8_t sp,pi,th,mo; };
static const VP VOICES[] = {
    {"sam",     72, 64,128,128},
    {"elf",     72, 64,110,160},
    {"robot",   92, 60,190,190},
    {"oldlady", 82, 32,145,145},
    {"et",     100, 64,150,200},
};

static void apply_voice(const char* name) {
    for (auto& v : VOICES) {
        if (strcmp(v.n, name) == 0) {
            g_speed=v.sp; g_pitch=v.pi; g_throat=v.th; g_mouth=v.mo;
            p_sam->setSpeed(g_speed);    p_sam->setPitch(g_pitch);
            p_sam->setThroat(g_throat);  p_sam->setMouth(g_mouth);
            g_voice = name;
            Serial.printf("[voice] %s  spd=%d pitch=%d\n",name,g_speed,g_pitch);
            return;
        }
    }
    Serial.printf("[voice] unknown '%s'\n", name);
}

// ─── I2S init ─────────────────────────────────────────────────────────────────
static void i2s_init() {
    i2s_config_t cfg = {
        .mode                 = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate          = SAM_SR,
        .bits_per_sample      = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format       = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags     = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count        = 8,
        .dma_buf_len          = 512,
        .use_apll             = false,
        .tx_desc_auto_clear   = true,
    };
    i2s_pin_config_t pins = {
        .mck_io_num   = I2S_PIN_NO_CHANGE,
        .bck_io_num   = PIN_BCLK,
        .ws_io_num    = PIN_LRC,
        .data_out_num = PIN_DIN,
        .data_in_num  = I2S_PIN_NO_CHANGE,
    };
    i2s_driver_install(I2S_PORT, &cfg, 0, NULL);
    i2s_set_pin(I2S_PORT, &pins);
    i2s_zero_dma_buffer(I2S_PORT);
    Serial.printf("[I2S] OK  BCLK=%d LRC=%d DIN=%d @ %dHz\n",
                  PIN_BCLK, PIN_LRC, PIN_DIN, SAM_SR);
}

// ─── Phát ─────────────────────────────────────────────────────────────────────
static void speak(const char* text) {
    if (!text || !*text) return;
    Serial.printf("\n>> \"%s\"  [%s spd=%d pitch=%d]\n",
                  text, g_voice.c_str(), g_speed, g_pitch);
    uint32_t t0 = millis();
    p_sam->say(text);
    Serial.printf("   done %ums  heap=%uKB\n",
                  (unsigned)(millis()-t0), esp_get_free_heap_size()/1024);
}

// ─── Lệnh ─────────────────────────────────────────────────────────────────────
static String _buf;

static void handle_cmd(const String& s) {
    if (s.startsWith(":speed "))
        { g_speed=(uint8_t)constrain(s.substring(7).toInt(),0,255);
          p_sam->setSpeed(g_speed); Serial.printf("[cmd] speed=%d\n",g_speed); }
    else if (s.startsWith(":pitch "))
        { g_pitch=(uint8_t)constrain(s.substring(7).toInt(),0,255);
          p_sam->setPitch(g_pitch); Serial.printf("[cmd] pitch=%d\n",g_pitch); }
    else if (s.startsWith(":voice "))
        { String n=s.substring(7); n.trim(); apply_voice(n.c_str()); }
    else if (s==":test")
        speak("The quick brown fox jumps over the lazy dog");
    else if (s==":info")
        Serial.printf("  %s spd=%d pitch=%d throat=%d mouth=%d  heap=%uKB\n",
                      g_voice.c_str(),g_speed,g_pitch,g_throat,g_mouth,
                      esp_get_free_heap_size()/1024);
    else
        Serial.println("  :speed N  :pitch N  :voice <sam|elf|robot|oldlady|et>  :test  :info");
}

// ─── setup / loop ─────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(2000);
    Serial.println("\n[SAM TTS] init...");

    i2s_init();

    // SAM tạo sau I2S, nhận I2SPrint làm output
    p_sam = new SAM(i2s_print);

    apply_voice("sam");
    Serial.println("[SAM TTS] ready — type text + Enter");
    speak("Hello. S A M is ready.");
}

void loop() {
    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n' || c == '\r') {
            _buf.trim();
            if (_buf.length()) {
                _buf.startsWith(":") ? handle_cmd(_buf) : speak(_buf.c_str());
                _buf = "";
            }
        } else if (_buf.length() < 200) _buf += c;
    }
}
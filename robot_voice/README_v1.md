# Robot Head Version 1.0

Voice-controlled robot head running on Raspberry Pi 4 with I2S microphone (INMP441) and I2S amplifier (MAX98357A).

## What it does

Listens for voice commands → transcribes speech → maps to robot actions → sends UART JSON to ESP32 motor controller → speaks audio feedback.

```
Voice → INMP441 mic → Vosk STT → FSD command tree → UART → ESP32 → Motors
                                                    ↓
                                          Edge TTS / Piper → MAX98357 speaker
```

---

## Advantages

| # | Advantage | Detail |
|---|-----------|--------|
| 1 | **Fully offline capable** | Vosk STT + Piper TTS work without internet — robot runs in any environment |
| 2 | **High-quality neural voice** | Edge TTS (Microsoft Jenny) sounds natural, not robotic |
| 3 | **No USB audio adapter** | I2S hardware connects directly to GPIO — cleaner wiring, no latency from USB |
| 4 | **Dual TTS fallback** | Auto-selects Edge TTS (cloud) when online, falls back to Piper (offline) |
| 5 | **WiFi captive portal** | Change WiFi without keyboard — connect to `RobotAP`, open browser, done |
| 6 | **Safe dry-run mode** | Test full voice pipeline without motors moving (`ROBOT_DRY_RUN=1`) |
| 7 | **Startup greeting** | Robot speaks on boot so you know it's ready |
| 8 | **Lightweight** | Vosk small model (~40MB), runs well on Pi 4 without GPU |

---

## Disadvantages

| # | Disadvantage | Detail |
|---|--------------|--------|
| 1 | **Always listening** | No wake word — Vosk transcribes every sound, increases false triggers |
| 2 | **Limited STT accuracy** | Small Vosk model has reduced vocabulary and struggles with accents or noise |
| 3 | **Edge TTS needs internet** | Cloud voice is unavailable offline; Piper fallback is lower quality |
| 4 | **Fixed ALSA device** | `plughw:2,0` is hardcoded — changing audio hardware requires code edit |
| 5 | **No natural language** | FSD tree matches keywords only — "please move forward slowly" may not resolve |
| 6 | **STT latency ~0.5–1s** | Vosk processes frames after silence, not real-time streaming |
| 7 | **PyAudio incompatible** | I2S capture uses `arecord` subprocess — PyAudio could not see the I2S input device |
| 8 | **Single language** | English only — changing language requires a different Vosk model |

---

## Hardware

| Component | Connection |
|-----------|-----------|
| INMP441 I2S Mic | GPIO18 (BCLK), GPIO19 (LRCLK), GPIO20 (SD) |
| MAX98357A I2S Amp | GPIO18 (BCLK), GPIO19 (LRCLK), GPIO21 (DIN) |
| ESP32 Motor Controller | UART `/dev/ttyUSB0` @ 115200 baud |

## Quick Start

```bash
cd /home/phuong/robot_voice
PYTHONUNBUFFERED=1 ROBOT_WORKFLOW=pi_audio ROBOT_DRY_RUN=1 .venv/bin/python3 -u src/main.py
```

## Test Scripts

```bash
python3 scripts/test_speaker.py          # tone test
python3 scripts/test_mic_rms.py          # mic level check
python3 scripts/test_tts.py "Hello"      # Piper TTS
python3 scripts/test_edge_tts.py "Hello" # Edge TTS
```

## WiFi Portal

When the Pi has no WiFi:
1. Connect to hotspot `RobotAP` (password: `robot1234`)
2. Open `http://10.42.0.1` in browser
3. Select network and enter password

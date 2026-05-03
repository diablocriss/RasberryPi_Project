# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A voice-controlled robot system with two subsystems:
- **`robot_voice/`** — Python controller running on Raspberry Pi 4 (also runnable on Windows for dev/testing). Handles audio capture, speech-to-text, command resolution via an FSD tree, text-to-speech feedback, and UART output to the motor controller.
- **`robot_voice_esp32/`** — C++ firmware for ESP32-S3 motor controller. Receives JSON packets over UART (115200 baud) and drives motors. Built with PlatformIO (board: `esp32-s3-devkitc-1`, upload port: COM15).

## Development Commands

### Windows (robot_voice/)

```powershell
# Install dependencies
py -3 Process.py --install

# Run full test suite + all example commands
py -3 Process.py --all-commands

# Run single-command smoke test
py -3 Process.py --smoke

# Run tests directly
cd robot_voice
pytest -q

# Compile-check all source and tests
python -m compileall -q src tests

# Run a single test file
pytest tests/unit/test_fsd_tree.py -q
```

### Raspberry Pi Deployment & Runtime

```powershell
# Deploy from Windows to Pi (192.168.1.66)
.\robot_voice\scripts\deploy.ps1 -Password "1"
```

```bash
# On the Pi — one-time setup check
bash scripts/pi_process.sh check

# Dry-run workflows (no UART output sent)
bash scripts/pi_process.sh text          # Text commands
bash scripts/pi_process.sh usb           # USB CDC audio
bash scripts/pi_process.sh pi-audio      # I2S microphone

# Live workflow (real motor output)
bash scripts/pi_process.sh pi-audio-live

# Verbose output
VERBOSE=1 bash scripts/pi_process.sh check
```

### ESP32 Firmware

```bash
# Build and upload via PlatformIO
pio run -t upload

# Monitor serial output
pio device monitor --baud 115200
```

## Architecture

### Python (robot_voice/src/)

`main.py` dispatches into one of six workflow modes set by the `ROBOT_WORKFLOW` env var:

| Mode | Description |
|------|-------------|
| `text_hybrid` | Text input → FSD tree → UART JSON (default dry-run dev mode) |
| `usb_cdc` | USB CDC audio frames → STT → FSD → UART |
| `pi_audio` | I2S microphone → STT → FSD → UART |
| `ai_fsd` | I2S + TASX GGUF model before keyword fallback |
| `keyword` | I2S + keyword FSD only (no AI) |
| `phase1` | Legacy mode |

**core/** — Command resolution engine:
- `fsd_tree.py` — Maps spoken phrases (e.g. "move forward") to JSON motor packets. The FSD tree is the primary command routing mechanism.
- `fsd_ai.py` + `tasx_adapter.py` — Optional AI overlay using a TASX GGUF model via llama.cpp, runs before FSD keyword matching in `ai_fsd` mode.
- `command_builder.py` / `command_validator.py` — Construct and validate JSON before UART send.

**stt/** and **tts/** — Routing layers with online/offline fallback:
- STT: Deepgram (cloud, requires `DEEPGRAM_API_KEY`) or Vosk (offline). `router.py` auto-selects based on network and API key availability.
- TTS: Microsoft Edge (cloud) or Piper (local). `router.py` auto-selects similarly.

**audio/** — Hardware abstraction:
- `pipeline_i2s.py` — Modern I2S microphone pipeline (INMP441 → Deepgram/Vosk).
- `pipeline.py` — Legacy USB CDC audio pipeline.
- `vad.py` — Voice activity detection gates audio before STT processing.
- PCM target format: 16-bit signed, 16 kHz, mono.

**comm/** — Hardware output:
- `uart.py` — Sends JSON packets at 115200 baud. `ROBOT_DRY_RUN=1` prints instead of sending (default on Windows).

### ESP32 (robot_voice_esp32/src/)

Receives JSON over UART, parses with ArduinoJson, and drives DC motors. `Test_speaker_main.cpp` implements SAM TTS output to the MAX98357 I2S amplifier.

## Key Environment Variables

Copy `robot_voice/.env.example` and customize:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ROBOT_WORKFLOW` | `text_hybrid` | Active workflow mode |
| `ROBOT_DRY_RUN` | `1` | Print JSON instead of sending via UART |
| `ROBOT_UART_PORT` | `/dev/ttyUSB0` (Pi) / `COM3` (Win) | UART device |
| `ROBOT_DEFAULT_SPEED` | `120` | Default motor speed |
| `ROBOT_DEFAULT_MOVE_TIME_MS` | `1000` | Default move duration (ms) |
| `ROBOT_AUDIO_HARDWARE_PROFILE` | `i2s_inmp441_max98357` | Audio hardware profile |
| `DEEPGRAM_API_KEY` | — | Required for cloud STT |
| `STT_MODE` / `TTS_MODE` | `auto` | Force `cloud` or `local` |
| `AI_ENABLED` | `1` | Enable TASX AI model |
| `AI_MODEL_PATH` | `models/tasx-cmd-0.5b-q4_k_m.gguf` | GGUF model path |
| `AI_CONFIDENCE_THRESHOLD` | `0.7` | Minimum AI confidence before FSD fallback |

## Hardware Reference

- **Pi**: Raspberry Pi 4 at `phuong@192.168.1.66`
- **I2S mic**: INMP441 — see `docs/I2S_WIRING.md` for GPIO pinout
- **I2S amp**: MAX98357 (BCLK=17, LRC=18, DIN=15 on ESP32)
- **ESP32**: ESP32-S3 DevKit-C-1 (16MB flash), COM15 on Windows

## Tests

Tests live in `robot_voice/tests/`. Integration tests (`tests/integration/`) require hardware or live API keys and are skipped in dry-run CI. Unit tests in `tests/unit/` run fully offline.

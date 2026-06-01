# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Three subsystems live in this repo:

- **`robot_voice/`** — Python controller running on Raspberry Pi 4 (also runnable on Windows for dev/testing). Handles audio capture, speech-to-text, command resolution via an FSD tree, text-to-speech feedback, and UART output to the motor controller.
- **`AppBookingResPi4/`** — Lightweight C HTTP booking-reservation server for Raspberry Pi 4. SQLite persistence, embedded HTML dashboard. Its compiled `.so` is also loaded by `robot_voice/src/db/booking_bridge.py` via ctypes so the robot can query room bookings at runtime.

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
- `ollama_pipeline.py` / `optimized_pipeline.py` — Experimental Ollama-based NLU pipelines.
- `context_manager.py` — Tracks multi-turn command context across utterances.
- `response_handler.py` — Formats TTS responses based on command outcomes.

**intent/** — Lightweight ML intent classifier:
- `train.py` — Trains a classifier from `training_data.json`.
- `classifier.py` + `preprocess.py` — Run-time classification.
- The web trainer UI (`web_trainer/`) provides a browser-based editor for `training_data.json`.

**stt/** — STT routing layer (online/offline):
- Deepgram (cloud, `DEEPGRAM_API_KEY`), Vosk (offline), or MoonShine (offline, `moonshine_stt.py`). `router.py` auto-selects.

**tts/** — TTS routing layer:
- Microsoft Edge (cloud) or Piper (local). `router.py` auto-selects.

**audio/** — Hardware abstraction:
- `pipeline_i2s.py` — Modern I2S microphone pipeline (INMP441 → Deepgram/Vosk/MoonShine).
- `pipeline_moonshine.py` — Dedicated pipeline for the MoonShine offline STT model.
- `wake_word.py` — Wake-word detection (via `arecord`) gates the STT pipeline.
- `pipeline.py` — Legacy USB CDC audio pipeline.
- `vad.py` — Voice activity detection gates audio before STT processing.
- PCM target format: 16-bit signed, 16 kHz, mono.

**comm/** — Hardware output:
- `uart.py` — Sends JSON packets at 115200 baud. `ROBOT_DRY_RUN=1` prints instead of sending (default on Windows).

**db/** — Cross-system bridge:
- `booking_bridge.py` — Loads the `AppBookingResPi4` compiled `.so` via ctypes, exposing room booking queries to the Python pipeline. Requires the C library to be compiled and the path passed via environment.

**web_trainer/** — Flask training UI:
- Start with `python -m src.web_trainer.app` (port 5000 by default). Provides dashboard, intent editor, log viewer, and live-test interface. Can also be embedded via `start_trainer()` in a background thread.

### AppBookingResPi4 (AppBookingResPi4/)

C11 HTTP server with SQLite persistence. See `AppBookingResPi4/CLAUDE.md` for the full build/deploy/architecture reference for that subsystem. Key cross-system note: edit `web/index.html` or `web/admin.html` and run `make` — the Makefile auto-converts HTML to `src/*_html.h` via `xxd`; never edit the `.h` files directly.

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

## Tests

Tests live in `robot_voice/tests/`. Two layouts coexist:
- `tests/unit/` — fully offline unit tests (FSD tree, VAD, audio utils, response handler).
- `tests/` root — additional offline tests for UART, settings, PCM, and pipelines. These also run without hardware.
- `tests/integration/` — require hardware or live API keys; skipped in dry-run CI.

Run a single test file: `pytest tests/unit/test_fsd_tree.py -q` (from `robot_voice/`).

---

## Current state

> **Update this section at the end of every sprint.**

**Last updated:** 2026-05-31
**Completed sprints:** None yet

### What exists
- [x] `robot_voice/` — full Python voice pipeline (STT, TTS, FSD, intent, web trainer)
- [x] `AppBookingResPi4/` — C HTTP booking server with SQLite and embedded dashboard
- [x] `robot_voice/src/db/booking_bridge.py` — ctypes bridge linking both subsystems
- [x] Planner-Executor workflow scaffolded (`.claude/`, `.plans/`, `skills/`)

### Known issues / tech debt
_None documented yet_

### Decisions made (summary)
| Decision | Chosen | Rejected | Sprint |
|----------|--------|----------|--------|
| _None yet_ | | | |

### What NOT to regenerate
_Populate after first sprint_

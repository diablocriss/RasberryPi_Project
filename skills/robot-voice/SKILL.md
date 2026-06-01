# Skill: robot-voice

> Python voice-command controller for Raspberry Pi 4.
> Last updated: 2026-05-31 | Confidence: high | Status: active

---

## Purpose
Python voice-command controller running on Raspberry Pi 4.
Audio → STT → FSD/Intent → JSON → UART → motor controller.

## When to use
Any task inside `robot_voice/src/` or `robot_voice/tests/`.

## Key files

| File | Role |
|------|------|
| `src/main.py` | Entry point — dispatches by `ROBOT_WORKFLOW` env var |
| `src/core/fsd_tree.py` | Primary command router: phrase → JSON motor packet |
| `src/core/fsd_ai.py` + `tasx_adapter.py` | TASX GGUF AI overlay (ai_fsd mode) |
| `src/core/command_builder.py` / `command_validator.py` | Build & validate JSON before UART |
| `src/core/context_manager.py` | Multi-turn command context |
| `src/core/response_handler.py` | Format TTS response strings |
| `src/stt/router.py` | Auto-selects Deepgram / Vosk / MoonShine |
| `src/tts/router.py` | Auto-selects Edge TTS / Piper |
| `src/audio/pipeline_i2s.py` | Modern I2S pipeline (INMP441) |
| `src/audio/wake_word.py` | Wake-word gate via `arecord` |
| `src/audio/vad.py` | Voice activity detection |
| `src/comm/uart.py` | UART output (dry-run safe) |
| `src/db/booking_bridge.py` | ctypes bridge to AppBookingResPi4 .so |
| `src/intent/classifier.py` | Run-time ML intent classifier |
| `src/intent/train.py` | Train classifier from training_data.json |
| `src/web_trainer/app.py` | Flask UI for editing training_data.json |
| `src/config/settings.py` | All env-var config in one place |

## Workflow modes (`ROBOT_WORKFLOW`)

| Mode | Pipeline |
|------|----------|
| `text_hybrid` | Text input → FSD → UART (default dev mode) |
| `pi_audio` | I2S mic → STT → FSD → UART |
| `ai_fsd` | I2S → TASX AI → FSD fallback → UART |
| `keyword` | I2S → FSD keyword only (no AI) |
| `usb_cdc` | USB CDC audio → STT → FSD → UART |
| `phase1` | Legacy single-shot mode |

## Build / test commands (run from `robot_voice/`)

```bash
python -m compileall -q src tests   # compile-check
pytest -q                           # all offline tests
pytest tests/unit/test_fsd_tree.py -q  # single file
```

## Constraints
- PCM format: 16-bit signed, 16 kHz, mono
- JSON motor packet schema: `{"cmd": "MOVE", "dir": "FORWARD", "speed": 120, "time_ms": 1000}`
- `ROBOT_DRY_RUN=1` is the default on Windows — never sends real UART
- Do NOT add a new STT engine without adding a `router.py` fallback path

## Known gotchas
_Fill in after first sprint_

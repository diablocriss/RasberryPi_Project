# Repository Guidelines

## Project Structure & Module Organization
This repository contains the Raspberry Pi voice controller and ESP32 motor firmware. `robot_voice/` holds the Python app: runtime modules in `src/`, tests in `tests/`, deployment helpers in `scripts/`, configuration examples in `.env.example` and `configs/`, and local model placeholders in `models/`. `robot_voice_esp32/` is the PlatformIO firmware project, with source sketches in `src/`, hardware tests in `Test/`, and board settings in `platformio.ini`. Shared architecture and wiring notes live in `docs/`.

## Build, Test, and Development Commands
From `robot_voice/`, use:

```powershell
py -3 Process.py --install
py -3 Process.py --all-commands
py -3 Process.py --smoke
pytest -q
python -m compileall -q src tests
```

`--install` prepares dependencies, `--all-commands` runs compile checks, tests, and dry-run command flows, and `--smoke` validates one quick workflow. Deploy to the Pi with `.\scripts\deploy.ps1 -Password "1"`, then run `bash scripts/pi_process.sh check` on the Pi. From `robot_voice_esp32/`, use `pio run`, `pio run -t upload`, and `pio device monitor --baud 115200`.

## Coding Style & Naming Conventions
Use Python 3 with 4-space indentation, `snake_case` modules and functions, and `PascalCase` classes. Keep hardware boundaries explicit: audio in `src/audio/`, UART and USB transport in `src/comm/`, command resolution in `src/core/`, STT in `src/stt/`, and TTS in `src/tts/`. For firmware, follow PlatformIO/Arduino conventions and keep board constants near `platformio.ini` or dedicated config headers.

## Testing Guidelines
Python tests use `pytest`; name files `test_<module>.py`. Keep deterministic unit tests in `robot_voice/tests/unit/`; place hardware, serial, STT, and TTS checks in `tests/integration/` and skip cleanly when devices or API keys are unavailable. Run `pytest -q` and `python -m compileall -q src tests` before submitting Python changes.

## Commit & Pull Request Guidelines
Git history uses short imperative subjects, for example `Fix AI resolver on aarch64 Pi 4` and `Add AI FSD resolver for robot voice`. Keep subjects specific and under one line. Pull requests should describe the affected workflow, list commands run, call out hardware checks, and mention configuration or wiring changes. Include serial logs only when they clarify behavior.

## Security & Configuration Tips
Never commit real `.env` files, API keys, generated `.pio/`, `.venv/`, logs, or large model binaries. Start with `ROBOT_DRY_RUN=1`; use `ROBOT_DRY_RUN=0` only when the ESP32 motor controller is connected and safety behavior is verified.

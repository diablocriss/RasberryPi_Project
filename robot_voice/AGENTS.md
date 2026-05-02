# Repository Guidelines

## Project Structure & Module Organization
This is a Python robot voice-control project. Runtime code lives in `src/`, with `src/main.py` as the entry point. Audio framing and PCM handling are in `src/audio/`, serial and USB CDC communication are in `src/comm/`, runtime configuration is in `src/config/`, command resolution is in `src/core/`, speech-to-text logic is in `src/stt/`, and text-to-speech output is in `src/tts/`. Deployment helpers live in `scripts/`; `scripts/deploy.ps1` is the current PowerShell deployment script. Model or recognizer assets belong in `model/`. There is no committed `tests/` directory yet; add one at the repository root when introducing automated tests.

## Build, Test, and Development Commands
Create and activate a virtual environment before installing dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the original text workflow:

```powershell
py src/main.py
```

Run the USB CDC audio workflow:

```powershell
$env:ROBOT_WORKFLOW = "usb_cdc"
py src/main.py
```

Use `.\scripts\deploy.ps1` for deployment once target paths and device settings are confirmed.

## Coding Style & Naming Conventions
Use Python 3 style with 4-space indentation, descriptive `snake_case` names for functions and modules, and `PascalCase` for classes such as `FsdTree`. Keep hardware boundaries explicit: parsing belongs in `audio`, serial transport in `comm`, and behavior mapping in `core`. Prefer small functions with typed configuration values sourced from `src/config/settings.py`. Do not commit generated `__pycache__/` files or local virtual environments.

## Testing Guidelines
No test framework is currently configured. For new logic, add `pytest` tests under `tests/` and name files `test_<module>.py`. Prioritize deterministic tests for `FsdTree` command resolution, PCM conversion, frame parsing, checksum validation, and UART dry-run output. Hardware-dependent tests should use fakes or fixtures rather than requiring connected ESP32 devices.

## Commit & Pull Request Guidelines
The current history uses concise, imperative commit messages, for example `Create robot voice project structure`. Continue that style: `Add USB CDC frame checksum tests`, `Refine UART dry-run logging`. Pull requests should describe the workflow affected, list test results or manual hardware checks, mention required environment variables, and link related issues when available.

## Security & Configuration Tips
Keep `.env` local and avoid committing secrets or machine-specific device ports. Document required variables in `README.md` when adding new configuration. Use `ROBOT_DRY_RUN=1` when validating command generation without sending UART packets to hardware.

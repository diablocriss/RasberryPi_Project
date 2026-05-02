#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/phuong/robot_voice}"
RUN_MODE="${1:-check}"

cd "$PROJECT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "[pi-process] Creating virtual environment"
  python3 -m venv --system-site-packages .venv
fi

# shellcheck disable=SC1091
. .venv/bin/activate

echo "[pi-process] Installing requirements"
python -m pip install -r requirements.txt

if [[ ! -f ".env" ]]; then
  echo "[pi-process] Creating .env from .env.example"
  cp .env.example .env
fi

export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

echo "[pi-process] Running compile check"
python -m compileall -q src tests

echo "[pi-process] Running tests"
python -m pytest -q

echo "[pi-process] Checking serial devices"
if ls /dev/ttyACM* /dev/ttyUSB* >/dev/null 2>&1; then
  ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true
else
  echo "[pi-process] No /dev/ttyACM* or /dev/ttyUSB* devices detected"
fi

case "$RUN_MODE" in
  check)
    echo "[pi-process] Check complete"
    ;;
  text)
    echo "[pi-process] Running text workflow dry-run"
    ROBOT_WORKFLOW=text_hybrid ROBOT_DRY_RUN=1 python src/main.py
    ;;
  usb)
    echo "[pi-process] Running USB CDC workflow in dry-run mode"
    ROBOT_WORKFLOW=usb_cdc ROBOT_DRY_RUN=1 python src/main.py
    ;;
  live)
    echo "[pi-process] Running USB CDC workflow with real UART output"
    ROBOT_WORKFLOW=usb_cdc ROBOT_DRY_RUN=0 python src/main.py
    ;;
  *)
    echo "Usage: $0 [check|text|usb|live]" >&2
    exit 2
    ;;
esac

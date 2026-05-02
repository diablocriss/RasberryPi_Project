#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/phuong/robot_voice}"
RUN_MODE="${1:-check}"
VERBOSE="${VERBOSE:-0}"

cd "$PROJECT_DIR"
echo "[pi-process] Project: $PROJECT_DIR"
echo "[pi-process] Mode: $RUN_MODE"

if [[ ! -d ".venv" ]]; then
  echo "[pi-process] Creating virtual environment"
  python3 -m venv --system-site-packages .venv
fi

# shellcheck disable=SC1091
. .venv/bin/activate

echo "[pi-process] Checking requirements"
if [[ "$VERBOSE" == "1" ]]; then
  python -m pip install -r requirements.txt
else
  python -m pip install -q -r requirements.txt
fi

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
SERIAL_FOUND=0
if compgen -G "/dev/ttyACM*" >/dev/null || compgen -G "/dev/ttyUSB*" >/dev/null; then
  SERIAL_FOUND=1
  ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true
else
  echo "[pi-process] No /dev/ttyACM* or /dev/ttyUSB* devices detected"
  echo "[pi-process] Connect ESP32 USB data cable, then rerun: ls -l /dev/ttyACM* /dev/ttyUSB*"
fi

if command -v lsusb >/dev/null 2>&1; then
  echo "[pi-process] USB devices:"
  lsusb
fi

if [[ "$RUN_MODE" == "usb" || "$RUN_MODE" == "live" ]] && [[ "$SERIAL_FOUND" == "0" ]]; then
  echo "[pi-process] Cannot start $RUN_MODE mode without an ESP32 serial device" >&2
  exit 3
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

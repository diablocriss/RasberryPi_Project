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

echo "[pi-process] Checking audio devices"
if command -v arecord >/dev/null 2>&1; then
  CAPTURE_DEVICES="$(arecord -l 2>/dev/null || true)"
  if printf '%s\n' "$CAPTURE_DEVICES" | grep -q '^card '; then
    echo "[pi-process] Capture devices:"
    printf '%s\n' "$CAPTURE_DEVICES"
  else
    echo "[pi-process] No ALSA capture devices detected"
    echo "[pi-process] Connect a USB microphone or enable/configure an I2S microphone"
  fi
else
  echo "[pi-process] arecord not installed; install alsa-utils to inspect microphones"
fi

if command -v aplay >/dev/null 2>&1; then
  PLAYBACK_DEVICES="$(aplay -l 2>/dev/null || true)"
  if printf '%s\n' "$PLAYBACK_DEVICES" | grep -q '^card '; then
    echo "[pi-process] Playback devices:"
    printf '%s\n' "$PLAYBACK_DEVICES"
  else
    echo "[pi-process] No ALSA playback devices detected"
    echo "[pi-process] Connect a USB speaker or enable/configure Pi audio output"
  fi
else
  echo "[pi-process] aplay not installed; install alsa-utils to inspect speakers"
fi

if command -v arecord >/dev/null 2>&1; then
  echo "[pi-process] ALSA device hints:"
  arecord -L | sed -n '1,20p' || true
fi

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
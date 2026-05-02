# Raspberry Pi Robot Voice Project

Voice-controlled robot prototype using a Windows development workflow, a Raspberry Pi runtime controller, and ESP32 hardware endpoints.

## Overview

The project turns spoken or typed commands into compact robot-control JSON packets.

```text
Voice / text command
-> Raspberry Pi command pipeline
-> FSD command resolver
-> UART JSON packet
-> ESP32 motor / actuator controller
```

The real hardware path uses two ESP32 boards:

```text
ESP32 #1:
  I2S microphone -> 16 kHz 16-bit mono PCM -> USB CDC frames

Raspberry Pi:
  USB CDC frame parser -> STT -> command resolver -> UART JSON

ESP32 #2:
  UART JSON -> motor / actuator control
```

## Repository Layout

```text
robot_voice/
  Python Raspberry Pi / Windows command pipeline
  USB CDC audio frame parser
  STT integration
  UART JSON sender
  Windows test runners

robot_voice_esp32/
  ESP32 / PlatformIO firmware experiments
  audio sender and command handler code
  motor-control test code
```

## Main Features

- Text-command workflow for safe Windows development.
- USB CDC audio workflow for Raspberry Pi hardware testing.
- Deepgram STT support for 16 kHz linear PCM audio.
- Robust USB CDC packet parser with checksum validation and partial-read handling.
- UART dry-run mode to validate robot commands without moving hardware.
- Unit tests for command resolution, UART dry-run output, PCM conversion, settings, and USB CDC frame parsing.
- Deployment script for `phuong@192.168.1.66`.

## Supported Commands

Current command examples:

```text
move forward
move foward
go forward
forward
foward
move backward
go backward
backward
move left
turn left
left
move right
turn right
right
speed up
slow down
emergency stop
stop
```

Example output:

```json
{"cmd":"MOVE","dir":"FORWARD","speed":120,"time_ms":1000}
```

## Windows Development

Use Windows for editing, tests, and dry-run command validation.

```powershell
cd robot_voice
py -3 Process.py --install
py -3 Process.py --all-commands
```

PowerShell alternative:

```powershell
cd robot_voice
.\Process.ps1 -Install
.\Process.ps1 -AllCommands
```

These commands run compile checks, unit tests, and the full text-command dry-run workflow.

## Raspberry Pi Runtime

Deploy from Windows:

```powershell
cd robot_voice
.\scripts\deploy.ps1 -Password "1"
```

Run on the Pi:

```bash
cd /home/phuong/robot_voice
. .venv/bin/activate
ROBOT_WORKFLOW=usb_cdc ROBOT_DRY_RUN=1 python3 src/main.py
```

One-time Pi setup/check runner:

```bash
cd /home/phuong/robot_voice
bash scripts/pi_process.sh check
```

Runner modes:

```text
check  create venv, install requirements, create .env, run tests, list serial devices
text   run checks, then start text workflow dry-run
usb    run checks, then start USB CDC workflow dry-run
live   run checks, then start USB CDC workflow with real UART output
```

The runner is quiet by default. Use `VERBOSE=1` when you need full `pip` output:

```bash
VERBOSE=1 bash scripts/pi_process.sh check
```

`usb` and `live` modes stop early if no `/dev/ttyACM*` or `/dev/ttyUSB*` device is detected.

Keep `ROBOT_DRY_RUN=1` until command output is correct. Set `ROBOT_DRY_RUN=0` only when the ESP32 motor controller is connected and ready.

## Runtime Configuration

Common environment variables:

```text
ROBOT_WORKFLOW=phase1 | text_hybrid | usb_cdc
ROBOT_DRY_RUN=1
ROBOT_AUDIO_CDC_PORT=/dev/ttyACM0
ROBOT_AUDIO_CDC_BAUDRATE=921600
ROBOT_UART_PORT=/dev/ttyUSB0
ROBOT_UART_BAUDRATE=115200
ROBOT_DEFAULT_SPEED=120
ROBOT_DEFAULT_MOVE_TIME_MS=1000
DEEPGRAM_API_KEY=...
DEEPGRAM_LANGUAGE=en-US
```

Use `robot_voice/.env.example` as the template for local configuration. Do not commit real `.env` files.

## Safety

The Raspberry Pi handles soft real-time command processing. The ESP32 motor controller should still enforce hardware safety:

```text
reject invalid JSON
clamp speed values
prioritize emergency stop
stop motors on UART timeout
limit actuator timing
```

## Current Hardware Status

The Raspberry Pi software path has been deployed and tested. Hardware USB serial devices must be connected before running the full audio/UART workflow:

```bash
ls -l /dev/ttyACM* /dev/ttyUSB*
```

If no serial devices appear, connect the ESP32 boards or check USB cable/data support.

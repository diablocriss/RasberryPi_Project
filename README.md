# Raspberry Pi Robot Voice Project

Voice-controlled robot prototype using a Windows development workflow, a Raspberry Pi 4 all-in-one voice controller, and an ESP32 motor controller.

## Overview

The target system turns spoken commands into compact robot-control JSON packets. The Raspberry Pi owns voice input, speech recognition, command resolution, spoken feedback, and UART output. The ESP32 remains focused on motor control and hard real-time safety.

```text
Voice command
-> Raspberry Pi audio capture
-> STT router: Deepgram cloud or Vosk offline
-> FSD command resolver
-> JSON command builder
-> UART /dev/ttyUSB0
-> ESP32 motor safety + driver
-> DC motors
```

Full architecture diagram: [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)

I2S wiring diagram: [docs/I2S_WIRING.md](docs/I2S_WIRING.md)

## Repository Layout

```text
robot_voice/
  Python Raspberry Pi / Windows command pipeline
  command resolver and UART JSON sender
  Deepgram STT module
  USB CDC parser from the earlier ESP32 microphone design
  Windows and Pi test runners

robot_voice_esp32/
  ESP32 / PlatformIO firmware experiments
  UART command handling
  motor-control test code

docs/
  system design and architecture diagrams
```

## Main Features

- Text-command workflow for safe Windows development.
- Raspberry Pi one-time setup/check runner.
- INMP441 I2S microphone and MAX98357 I2S amplifier target hardware.
- Deepgram STT support for 16 kHz linear PCM audio.
- Command resolver with common aliases and typo tolerance.
- UART dry-run mode to validate robot commands without moving hardware.
- ESP32 motor controller boundary for hard real-time safety.
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

One-time Pi setup/check runner:

```bash
cd /home/phuong/robot_voice
bash scripts/pi_process.sh check
```

Runner modes:

```text
check  create venv, install requirements, create .env, run tests, list devices
text   run checks, then start text workflow dry-run
usb    run checks, then start legacy USB CDC workflow dry-run
live   run checks, then start legacy USB CDC workflow with real UART output
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
ROBOT_AUDIO_HARDWARE_PROFILE=i2s_inmp441_max98357
ROBOT_AUDIO_INPUT_DEVICE=default
ROBOT_AUDIO_OUTPUT_DEVICE=default
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

## Current Implementation Status

Implemented now:

- Windows and Pi text-command dry-run.
- Deepgram STT module.
- UART JSON sender.
- Legacy USB CDC audio parser.
- Pi setup/check runner.
- Automated tests.

Planned next from the all-in-one Pi design:

- Pi-local USB/I2S microphone capture.
- STT router: Deepgram cloud or Vosk offline.
- TTS router: Piper offline or Edge TTS cloud.
- Pi audio playback for command feedback.
- `ROBOT_WORKFLOW=pi_audio`.

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

The Raspberry Pi software path has been deployed and tested. Hardware USB serial devices must be connected before running UART motor output:

```bash
ls -l /dev/ttyACM* /dev/ttyUSB*
```

If no serial devices appear, connect the ESP32 motor controller or check USB cable/data support.

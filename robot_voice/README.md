# Robot Voice Control

This project keeps the original Phase 1 text workflow and adds a USB CDC audio streaming workflow for the real hardware path.

## Workflows

Original Phase 1:

```text
text input -> FSD tree -> UART print
```

Run:

```powershell
py src/main.py
```

USB CDC audio workflow:

```text
ESP32 #1:
  I2S mic -> 16 kHz 16-bit mono PCM -> framed USB CDC packets

Raspberry Pi:
  USB CDC -> frame parser -> PCM buffer
  -> lightweight STT / keyword detection
  -> FSD tree
  -> compact JSON command over UART

ESP32 #2:
  JSON command -> motor / actuator control
```

Run:

```powershell
$env:ROBOT_WORKFLOW = "usb_cdc"
py src/main.py
```

## ESP32 #1 Audio Packet Protocol

Audio format:

```text
sample rate: 16000 Hz
bits:        16
channels:    mono
frame size:  512-1024 bytes
transport:   USB CDC, not USB Audio Class
baud:        921600
```

Frame format:

```text
0xAA 0x55
length_low
length_high
payload PCM bytes
checksum
```

Checksum:

```text
sum(payload bytes) & 0xFF
```

The Raspberry Pi parser continuously searches for the `0xAA 0x55` header, validates the payload length, verifies checksum, and skips corrupted frames so it can recover after packet loss or stream misalignment.

## Raspberry Pi Pipeline

Implemented path:

```text
read_frame()
-> pcm_to_array()
-> stt_process()
-> FsdTree.resolve_command()
-> UartClient.send_json()
```

The current STT processor streams 16 kHz linear PCM to Deepgram. Set `DEEPGRAM_API_KEY` before running `ROBOT_WORKFLOW=usb_cdc`.

## Runtime Settings

```text
ROBOT_WORKFLOW=phase1              original text workflow
ROBOT_WORKFLOW=usb_cdc             USB CDC audio workflow
ROBOT_AUDIO_CDC_PORT=/dev/ttyACM0  ESP32 #1 USB CDC port
ROBOT_AUDIO_CDC_BAUDRATE=921600    ESP32 #1 USB CDC baud
ROBOT_UART_PORT=COM3               ESP32 #2 UART port
ROBOT_UART_BAUDRATE=115200         ESP32 #2 UART baud
ROBOT_DRY_RUN=1                    print JSON UART packets instead of sending
ROBOT_DEFAULT_SPEED=120            default motor speed
ROBOT_DEFAULT_MOVE_TIME_MS=1000    default move duration
DEEPGRAM_API_KEY=...               Deepgram API key for USB CDC workflow
DEEPGRAM_LANGUAGE=en-US            STT language
```

## Development Split

Windows development:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ROBOT_WORKFLOW = "text_hybrid"
$env:ROBOT_DRY_RUN = "1"
py src/main.py
pytest -q
```

Raspberry Pi deployment:

```powershell
.\scripts\deploy.ps1 -Password "1"
```

Raspberry Pi runtime:

```bash
cd /home/phuong/robot_voice
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m pytest -q
ROBOT_WORKFLOW=usb_cdc ROBOT_DRY_RUN=1 python3 src/main.py
```

One-time Pi setup/check runner:

```bash
cd /home/phuong/robot_voice
bash scripts/pi_process.sh check
```

Use `text`, `usb`, or `live` instead of `check` to start the text dry-run, USB CDC dry-run, or real UART mode after setup.

## Safety Notes

The Pi is the soft real-time processor. ESP32 #2 remains responsible for hard real-time motor control and should locally enforce:

```text
invalid JSON rejection
speed clamping
emergency stop priority
motor stop on UART timeout
actuator timing limits
```

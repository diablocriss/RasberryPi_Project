# Robot Voice Control

Python command pipeline for the Raspberry Pi robot voice controller. This package supports safe text-command testing today and is being moved toward a Raspberry Pi all-in-one audio design.

Full target architecture: [../docs/SYSTEM_DESIGN.md](../docs/SYSTEM_DESIGN.md)

## Workflows

Text dry-run workflow:

```text
text input -> FSD tree -> UART dry-run print
```

Run on Windows:

```powershell
py -3 Process.py --all-commands
```

Run manually:

```powershell
$env:ROBOT_WORKFLOW = "text_hybrid"
$env:ROBOT_DRY_RUN = "1"
py src/main.py
```

Legacy USB CDC audio workflow:

```text
ESP32 #1 or USB CDC source:
  16 kHz 16-bit mono PCM -> framed USB CDC packets

Raspberry Pi:
  USB CDC -> frame parser -> PCM buffer
  -> Deepgram STT
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

Target Pi-local audio workflow:

```text
USB/I2S microphone on Pi
-> PyAudio/ALSA capture
-> STT router: Deepgram cloud or Vosk offline
-> FSD tree
-> UART JSON to ESP32 motor controller
-> TTS router: Piper offline or Edge TTS cloud
-> Pi speaker output
```

This target workflow is documented but not fully implemented yet.

## USB CDC Packet Protocol

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

The parser searches for the `0xAA 0x55` header, validates payload length, verifies checksum, and tolerates partial serial reads.

## Raspberry Pi Pipeline

Implemented path:

```text
read_frame()
-> pcm_to_array()
-> stt_process()
-> FsdTree.resolve_command()
-> UartClient.send_json()
```

The current STT processor streams 16 kHz linear PCM to Deepgram. Set `DEEPGRAM_API_KEY` before running the USB CDC workflow.

## Runtime Settings

```text
ROBOT_WORKFLOW=phase1              original text workflow
ROBOT_WORKFLOW=text_hybrid         text workflow with JSON commands
ROBOT_WORKFLOW=usb_cdc             legacy USB CDC audio workflow
ROBOT_AUDIO_CDC_PORT=/dev/ttyACM0  USB CDC audio source
ROBOT_AUDIO_CDC_BAUDRATE=921600    USB CDC baud
ROBOT_UART_PORT=/dev/ttyUSB0       ESP32 motor UART port on Pi
ROBOT_UART_BAUDRATE=115200         ESP32 motor UART baud
ROBOT_DRY_RUN=1                    print JSON UART packets instead of sending
ROBOT_DEFAULT_SPEED=120            default motor speed
ROBOT_DEFAULT_MOVE_TIME_MS=1000    default move duration
DEEPGRAM_API_KEY=...               Deepgram API key
DEEPGRAM_LANGUAGE=en-US            STT language
```

## Development Split

Windows development:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py -3 Process.py --all-commands
```

Raspberry Pi deployment:

```powershell
.\scripts\deploy.ps1 -Password "1"
```

Raspberry Pi one-time setup/check runner:

```bash
cd /home/phuong/robot_voice
bash scripts/pi_process.sh check
```

Use `text`, `usb`, or `live` instead of `check` to start the text dry-run, USB CDC dry-run, or real UART mode after setup.

The runner uses quiet dependency checks by default. Use `VERBOSE=1 bash scripts/pi_process.sh check` for full `pip` output. `usb` and `live` modes stop early if no `/dev/ttyACM*` or `/dev/ttyUSB*` device is detected.

## Safety Notes

The Pi is the soft real-time processor. ESP32 #2 remains responsible for hard real-time motor control and should locally enforce:

```text
invalid JSON rejection
speed clamping
emergency stop priority
motor stop on UART timeout
actuator timing limits
```

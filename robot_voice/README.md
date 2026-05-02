# Robot Voice Control

Python command pipeline for the Raspberry Pi robot voice controller. This package supports safe text-command testing today and is being moved toward a Raspberry Pi all-in-one audio design.

Full target architecture: [../docs/SYSTEM_DESIGN.md](../docs/SYSTEM_DESIGN.md)

I2S wiring diagram: [../docs/I2S_WIRING.md](../docs/I2S_WIRING.md)

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

Pi-local audio workflow:

```text
INMP441 I2S microphone on Pi
-> PyAudio/ALSA capture
-> STT router: Deepgram cloud or Vosk offline
-> AI FSD resolver: TASX-Cmd-0.5B via llama.cpp
-> keyword FSD fallback
-> UART JSON to ESP32 motor controller
-> TTS router: Piper offline or Edge TTS cloud
-> Pi speaker output
```

Run:

```bash
ROBOT_WORKFLOW=pi_audio ROBOT_DRY_RUN=1 python src/main.py
```

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
ROBOT_WORKFLOW=pi_audio            Pi I2S audio workflow
ROBOT_WORKFLOW=ai_fsd              Pi I2S audio workflow with AI FSD
ROBOT_WORKFLOW=keyword             Pi I2S audio workflow with keyword FSD only
ROBOT_AUDIO_HARDWARE_PROFILE=i2s_inmp441_max98357
ROBOT_AUDIO_INPUT_DEVICE=default   ALSA capture device for INMP441
ROBOT_AUDIO_OUTPUT_DEVICE=default  ALSA playback device for MAX98357
ROBOT_AUDIO_CDC_PORT=/dev/ttyACM0  USB CDC audio source
ROBOT_AUDIO_CDC_BAUDRATE=921600    USB CDC baud
ROBOT_UART_PORT=/dev/ttyUSB0       ESP32 motor UART port on Pi
ROBOT_UART_BAUDRATE=115200         ESP32 motor UART baud
ROBOT_DRY_RUN=1                    print JSON UART packets instead of sending
ROBOT_DEFAULT_SPEED=120            default motor speed
ROBOT_DEFAULT_MOVE_TIME_MS=1000    default move duration
DEEPGRAM_API_KEY=...               Deepgram API key
DEEPGRAM_LANGUAGE=en-US            STT language
AI_ENABLED=1                       enable TASX AI resolver before keyword fallback
AI_MODEL_PATH=models/tasx-cmd-0.5b-q4_k_m.gguf
AI_CONFIDENCE_THRESHOLD=0.7
AI_TIMEOUT_MS=800
```

## AI FSD Setup

Install and download the TASX GGUF model on the Pi:

```bash
cd /home/phuong/robot_voice
pip install llama-cpp-python --extra-index-url https://www.piwheels.org/simple
mkdir -p models
wget -O models/tasx-cmd-0.5b-q4_k_m.gguf https://huggingface.co/ReXeeD/TASX-Cmd-0.5B-GGUF/resolve/main/tasx-cmd-0.5b-q4_k_m.gguf
```

Start the I2S pipeline with AI enabled:

```bash
ROBOT_WORKFLOW=ai_fsd ROBOT_DRY_RUN=1 python src/main.py
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

Use `text`, `usb`, `pi-audio`, `pi-audio-live`, or `live` instead of `check` to start the text dry-run, USB CDC dry-run, Pi I2S dry-run, Pi I2S real UART mode, or USB CDC real UART mode after setup.

The runner uses quiet dependency checks by default. Use `VERBOSE=1 bash scripts/pi_process.sh check` for full `pip` output. `usb`, `live`, and `pi-audio-live` modes stop early if no `/dev/ttyACM*` or `/dev/ttyUSB*` device is detected.

## Safety Notes

The Pi is the soft real-time processor. ESP32 #2 remains responsible for hard real-time motor control and should locally enforce:

```text
invalid JSON rejection
speed clamping
emergency stop priority
motor stop on UART timeout
actuator timing limits
```

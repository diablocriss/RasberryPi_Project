# System Design: Raspberry Pi All-in-One Voice Controller

This document describes the target architecture for the robot voice-control system. The Raspberry Pi 4 owns voice capture, speech recognition, command resolution, text-to-speech feedback, and UART command output. ESP32 #2 is kept narrow: motor control and hardware safety.

## Target Flow

```mermaid
flowchart TB
    subgraph USER["User Interaction"]
        Voice["Voice Command<br/>'move forward'"]
        Feedback["Audio Feedback<br/>'Executing move forward'"]
    end

    subgraph RASPBERRY_PI["Raspberry Pi 4 - All-in-One Controller"]
        direction TB

        subgraph AUDIO_HARDWARE["I2S Audio Hardware on Pi"]
            MIC_USB["INMP441 I2S Mic<br/>GPIO18/19/21<br/>16kHz/16bit"]
            SPEAKER_3MM["MAX98357 I2S Amp<br/>GPIO18/19/20<br/>Speaker Output"]
            AUDIO_DEVICE["ALSA I2S Devices<br/>capture + playback"]
        end

        subgraph AUDIO_CAPTURE["Audio Capture Layer"]
            PYAUDIO_CAPTURE["PyAudio Capture<br/>Streaming Callback"]
            PCM_BUFFER["PCM Buffer<br/>512-1024 bytes<br/>Queue"]
        end

        subgraph STT_LAYER["Speech to Text Layer"]
            STT_ROUTER{"STT Router<br/>Auto-detect"}
            DEEPGRAM["Deepgram Cloud<br/>High Accuracy"]
            VOSK["Vosk Offline<br/>Lightweight"]
            STT_QUEUE["Text Queue"]
        end

        subgraph FSD_LAYER["Command Resolution"]
            FSD_TREE["FSD Tree<br/>Keyword Matching"]
            COMMAND_BUILDER["JSON Builder"]
        end

        subgraph TTS_LAYER["Text to Speech Layer"]
            TTS_ROUTER{"TTS Router<br/>Auto-detect"}
            PIPER["Piper TTS<br/>Offline"]
            EDGE["Edge TTS<br/>Cloud"]
            AUDIO_PLAYER["Audio Player<br/>PyAudio Output"]
        end

        subgraph CONTROL["Control Layer"]
            UART_CLIENT["UART Client<br/>/dev/ttyUSB0"]
            MAIN_PIPELINE["Main Pipeline"]
            SETTINGS["Settings"]
        end
    end

    subgraph ESP32_MOTOR["ESP32 #2 - Motor Control Only"]
        UART_RX["UART Receiver<br/>115200 baud"]
        JSON_PARSER["JSON Parser"]
        SAFETY["Safety Check"]
        MOTOR_DRIVER["Motor Driver"]
    end

    subgraph HARDWARE["Hardware Output"]
        MOTORS["DC Motors"]
    end

    Voice --> MIC_USB
    MIC_USB --> AUDIO_DEVICE
    AUDIO_DEVICE --> PYAUDIO_CAPTURE
    PYAUDIO_CAPTURE --> PCM_BUFFER
    PCM_BUFFER --> STT_ROUTER

    STT_ROUTER --> DEEPGRAM
    STT_ROUTER --> VOSK
    DEEPGRAM --> STT_QUEUE
    VOSK --> STT_QUEUE
    STT_QUEUE --> FSD_TREE

    FSD_TREE --> COMMAND_BUILDER
    COMMAND_BUILDER --> UART_CLIENT
    COMMAND_BUILDER --> TTS_ROUTER

    TTS_ROUTER --> PIPER
    TTS_ROUTER --> EDGE
    PIPER --> AUDIO_PLAYER
    EDGE --> AUDIO_PLAYER
    AUDIO_PLAYER --> SPEAKER_3MM
    SPEAKER_3MM --> Feedback

    UART_CLIENT --> UART_RX
    UART_RX --> JSON_PARSER
    JSON_PARSER --> SAFETY
    SAFETY --> MOTOR_DRIVER
    MOTOR_DRIVER --> MOTORS

    classDef pi fill:#4caf50,stroke:#1b5e20,color:#fff
    classDef cloud fill:#2196f3,stroke:#0d47a1,color:#fff
    classDef local fill:#9c27b0,stroke:#4a148c,color:#fff
    classDef esp32 fill:#ff9800,stroke:#e65100,color:#000
    classDef hardware fill:#f44336,stroke:#b71c1c,color:#fff

    class RASPBERRY_PI,AUDIO_HARDWARE,AUDIO_CAPTURE,STT_LAYER,FSD_LAYER,TTS_LAYER,CONTROL pi
    class DEEPGRAM,EDGE cloud
    class VOSK,PIPER local
    class ESP32_MOTOR esp32
    class HARDWARE,MOTORS hardware
```

## Component Responsibilities

| Layer | Responsibility | Preferred implementation |
| --- | --- | --- |
| Audio hardware | Capture user voice and play feedback | INMP441 I2S microphone and MAX98357 I2S amplifier |
| Audio capture | Stream 16 kHz 16-bit mono PCM into a queue | PyAudio / ALSA |
| STT router | Select online or offline speech recognition | Deepgram if key/network available, otherwise Vosk |
| Command resolution | Convert recognized text into robot command JSON | `FsdTree.resolve_command()` |
| TTS router | Speak feedback after command resolution | Piper offline, Edge TTS cloud fallback/option |
| UART client | Send compact JSON command to motor controller | `/dev/ttyUSB0` at 115200 baud |
| ESP32 motor | Enforce hard real-time motor safety | JSON parser, timeout stop, speed clamp |

## Current Implementation Status

Implemented now:

- Text command dry-run on Windows and Raspberry Pi.
- FSD command resolver with common aliases and typo tolerance for `foward`.
- UART JSON output with dry-run mode.
- Deepgram streaming STT module.
- USB CDC frame parser from the previous ESP32 microphone design.
- One-time Pi runner: `scripts/pi_process.sh`.
- Unit tests for command resolution, UART dry-run, settings, PCM, and USB CDC frames.

Target additions from this design:

- Pi-local microphone capture through ALSA/PyAudio.
- STT router that chooses Deepgram or Vosk.
- TTS router that chooses Piper or Edge TTS.
- Audio playback through Pi audio output.
- A new `pi_audio` runtime mode that replaces the older ESP32 USB CDC microphone path.

Hardware wiring: [I2S_WIRING.md](I2S_WIRING.md).

## Development Plan

1. Add an audio device probe to `pi_process.sh` using `arecord -l` and `aplay -l`.
2. Add `src/audio/pi_capture.py` for USB/ALSA microphone capture.
3. Add `src/stt/router.py` with Deepgram-first and Vosk fallback behavior.
4. Add `src/tts/router.py` with Piper-first and Edge fallback behavior.
5. Add a `ROBOT_WORKFLOW=pi_audio` pipeline.
6. Keep `ROBOT_DRY_RUN=1` until STT, command output, and TTS feedback are verified.
7. Enable `ROBOT_DRY_RUN=0` only after ESP32 motor firmware safety checks are validated.

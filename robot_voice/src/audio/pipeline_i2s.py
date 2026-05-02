from audio.i2s_capture import I2SMicrophone
from audio.i2s_config import from_settings
from comm.uart import UartClient
from config.settings import Settings
from core.fsd_tree import FsdTree
from stt.router import STTRouter
from tts.router import TTSRouter


def run_i2s_pipeline(settings: Settings | None = None) -> None:
    settings = settings or Settings()
    config = from_settings(settings)
    microphone = I2SMicrophone(config)
    stt = STTRouter(settings)
    tts = TTSRouter(settings)
    command_tree = FsdTree(settings)
    uart = UartClient(settings)

    print("[I2S] Pipeline started")
    for frame in microphone.frames():
        text = stt.transcribe(frame)
        if not text:
            continue
        command = command_tree.resolve_command(text)
        if command:
            uart.send_json(command)
            tts.say(f"Executing {text}")
        else:
            tts.say("Command not recognized")

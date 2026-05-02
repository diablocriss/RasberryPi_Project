from audio.i2s_capture import I2SMicrophone
from audio.i2s_config import from_settings
from comm.uart import UartClient
from config.settings import Settings
from core.command_validator import CommandValidator
from core.context_manager import ContextManager
from core.fsd_ai import TASXResolver
from core.fsd_tree import FsdTree
from stt.router import STTRouter
from tts.router import TTSRouter


def run_i2s_pipeline(settings: Settings | None = None) -> None:
    settings = settings or Settings()
    ai_resolver = TASXResolver(settings.ai_model_path) if settings.ai_enabled else None
    context_manager = ContextManager(settings.ai_context_history)
    command_validator = CommandValidator()
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

        command = None
        if ai_resolver is not None:
            ai_command, confidence = ai_resolver.resolve(text)
            if ai_command and confidence >= settings.ai_confidence_threshold:
                ai_command = context_manager.handle_contextual(text, ai_command)
                ok, reason = command_validator.validate(ai_command)
                if ok:
                    command = command_validator.sanitize(ai_command)
                else:
                    print(f"[AI FSD] Rejected unsafe command: {reason}")

        if command is None:
            command = command_tree.resolve_command(text)

        if command:
            uart.send_json(command)
            context_manager.add_command(command)
            tts.say(f"Executing {text}")
        else:
            tts.say("Command not recognized")

import os

from comm.uart import UartClient
from config.settings import Settings
from config.version import VERSION
from core.fsd_tree import FsdTree
from stt.listener import Listener
from tts.speaker import Speaker


def run_phase1() -> None:
    settings = Settings()
    listener = Listener(settings)
    speaker = Speaker(settings)
    command_tree = FsdTree()
    uart = UartClient(settings)

    text = listener.listen()
    action = command_tree.resolve(text)

    if action:
        uart.send(action)
        speaker.say(f"Command sent: {action}")
    else:
        speaker.say("Command not recognized")


def run_hybrid_workflow() -> None:
    from audio.pipeline import audio_pipeline

    print(f"RUN VERSION {VERSION}")
    print("FILE:", os.path.abspath(__file__))
    print("=== ESP32 I2S -> USB CDC Frames -> Pi STT/FSD -> UART JSON ===")
    audio_pipeline()


def run_text_hybrid_workflow() -> None:
    settings = Settings()
    listener = Listener(settings)
    speaker = Speaker(settings)
    command_tree = FsdTree(settings)
    uart = UartClient(settings)

    print(f"RUN VERSION {VERSION}")
    print("FILE:", os.path.abspath(__file__))
    print("=== ESP32 Audio -> Pi FSD -> UART Control ===")
    print(f"UART: {settings.uart_port} @ {settings.uart_baudrate} baud")
    print(f"Dry run: {settings.dry_run}")
    print("Type 'exit' to quit\n")

    while True:
        text = listener.listen()

        if text.lower() == "exit":
            print("Exiting...")
            break

        command = command_tree.resolve_command(text)

        print("\n[DEBUG]")
        print(f"Input  : {text}")
        print(f"Command: {command}")

        if command:
            uart.send_json(command)
            speaker.say(f"Command sent: {command['cmd']}")
        else:
            rejected = command_tree.reject(text)
            print(f"Reject : {rejected}")
            speaker.say("Command not recognized")

        print("-" * 30)


def main() -> None:
    from audio.pipeline_i2s import run_i2s_pipeline

    workflow = os.getenv("ROBOT_WORKFLOW", "phase1").lower()
    if workflow in {"usb_cdc", "audio", "hybrid"}:
        run_hybrid_workflow()
    elif workflow in {"ai_fsd", "ai"}:
        run_i2s_pipeline(Settings())
    elif workflow == "keyword":
        settings = Settings()
        object.__setattr__(settings, "ai_enabled", False)
        run_i2s_pipeline(settings)
    elif workflow in {"pi_audio", "i2s"}:
        run_i2s_pipeline()
    elif workflow in {"text_hybrid", "robot", "uart"}:
        run_text_hybrid_workflow()
    else:
        run_phase1()


if __name__ == "__main__":
    main()

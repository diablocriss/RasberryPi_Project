from stt.listener import Listener
from tts.speaker import Speaker
from core.fsd_tree import FsdTree
from comm.uart import UartClient
from config.settings import Settings


def main() -> None:
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


if __name__ == "__main__":
    main()

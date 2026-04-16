from config.settings import Settings


class Listener:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def listen(self) -> str:
        return input("Voice command text: ").strip()

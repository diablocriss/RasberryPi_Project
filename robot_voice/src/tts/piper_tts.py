from config.settings import Settings


class PiperTTS:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def say(self, text: str) -> None:
        print(f"[PiperTTS pending] {text}")

from config.settings import Settings


class EdgeTTS:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def say(self, text: str) -> None:
        print(f"[EdgeTTS pending] {text}")

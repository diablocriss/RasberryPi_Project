from config.settings import Settings
from tts.edge_tts import EdgeTTS
from tts.piper_tts import PiperTTS
from utils.network import has_internet


class TTSRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.mode = getattr(settings, "tts_mode", "auto")
        self._engine = self._select_engine()

    def _select_engine(self):
        if self.mode == "cloud":
            return EdgeTTS(self.settings)
        if self.mode == "local":
            return PiperTTS(self.settings)
        if has_internet():
            return EdgeTTS(self.settings)
        return PiperTTS(self.settings)

    def say(self, text: str) -> None:
        self._engine.say(text)

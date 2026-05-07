from config.settings import Settings
from stt.vosk_stt import VoskSTT
from utils.network import has_internet


class STTRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.mode = getattr(settings, "stt_mode", "auto")
        self._engine = self._select_engine()

    def _select_engine(self):
        if self.mode == "cloud":
            from stt.deepgram_stt import DeepgramSTT
            return DeepgramSTT(self.settings)
        if self.mode == "local":
            return VoskSTT(self.settings)
        if self.settings.deepgram_api_key and has_internet():
            from stt.deepgram_stt import DeepgramSTT
            return DeepgramSTT(self.settings)
        return VoskSTT(self.settings)

    def transcribe(self, pcm: bytes) -> str | None:
        return self._engine.transcribe(pcm)

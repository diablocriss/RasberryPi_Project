from config.settings import Settings
from stt.processor import stt_get_text, stt_init, stt_send


class DeepgramSTT:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._started = False

    def _ensure_started(self) -> None:
        if not self._started:
            stt_init(self.settings.deepgram_api_key, self.settings.deepgram_language)
            self._started = True

    def transcribe(self, pcm: bytes) -> str | None:
        self._ensure_started()
        stt_send(pcm)
        return stt_get_text()

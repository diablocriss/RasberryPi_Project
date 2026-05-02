from config.settings import Settings


class VoskSTT:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._recognizer = None

    def _ensure_loaded(self) -> None:
        if self._recognizer is not None:
            return
        try:
            import vosk  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("Vosk is required for offline STT. Install vosk and a model under models/vosk/.") from exc
        raise NotImplementedError("Vosk model loading is planned but not configured yet")

    def transcribe(self, pcm: bytes) -> str | None:
        self._ensure_loaded()
        return None

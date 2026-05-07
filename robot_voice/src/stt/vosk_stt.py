import json
import os

from config.settings import Settings

_DEFAULT_MODEL_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "models", "vosk"
)


def _find_model(model_dir: str) -> str:
    if os.path.isfile(os.path.join(model_dir, "conf", "model.conf")):
        return model_dir
    for entry in sorted(os.listdir(model_dir)):
        candidate = os.path.join(model_dir, entry)
        if os.path.isdir(candidate) and os.path.isfile(
            os.path.join(candidate, "conf", "model.conf")
        ):
            return candidate
    raise RuntimeError(f"No Vosk model found under: {model_dir}")


class VoskSTT:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._recognizer = None
        self._sample_rate = getattr(settings, "audio_sample_rate", 16000)

    def _ensure_loaded(self) -> None:
        if self._recognizer is not None:
            return
        try:
            import vosk
        except ImportError as exc:
            raise RuntimeError(
                "Vosk is required for offline STT. Run: pip install vosk"
            ) from exc

        vosk.SetLogLevel(-1)
        model_dir = _find_model(_DEFAULT_MODEL_DIR)
        print(f"[STT] Loading Vosk model from {model_dir}")
        model = vosk.Model(model_dir)
        self._recognizer = vosk.KaldiRecognizer(model, self._sample_rate)
        self._recognizer.SetWords(False)
        print("[STT] Vosk model loaded")

    def transcribe(self, pcm: bytes) -> str | None:
        self._ensure_loaded()
        if self._recognizer.AcceptWaveform(pcm):
            result = json.loads(self._recognizer.Result())
            text = result.get("text", "").strip()
            if text:
                print(f"[STT] '{text}'")
            return text if text else None
        return None

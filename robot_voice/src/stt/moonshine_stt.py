import logging
import re

import numpy as np

logger = logging.getLogger(__name__)


class MoonShineSTT:
    def __init__(self, config: dict) -> None:
        self._language = config.get("moonshine", {}).get("language", "en")
        self._transcriber = None

    def _load(self) -> None:
        if self._transcriber is not None:
            return
        from moonshine_voice import Transcriber, get_model_for_language
        logger.info("Loading MoonShine model (language=%s)…", self._language)
        model_path, model_arch = get_model_for_language(self._language)
        logger.info("Model: path=%s  arch=%s", model_path, model_arch)
        self._transcriber = Transcriber(model_path=model_path, model_arch=model_arch)
        logger.info("MoonShine ready")

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe float32 16 kHz mono audio. Returns normalised lowercase text."""
        self._load()
        if audio is None or len(audio) == 0:
            return ""

        audio = audio.astype(np.float32)
        if np.abs(audio).max() > 1.0:
            audio = audio / 32768.0

        try:
            transcript = self._transcriber.transcribe_without_streaming(
                audio.tolist(), sample_rate=16000
            )
            texts = [line.text for line in transcript.lines if (line.text or "").strip()]
            return _normalise(" ".join(texts))
        except Exception:
            logger.exception("MoonShine transcription failed")
            return ""


def _normalise(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s']", "", text)
    return " ".join(text.split())

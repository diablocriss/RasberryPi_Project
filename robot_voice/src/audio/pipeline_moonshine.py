"""MoonShine voice pipeline: VAD → STT → response → TTS."""

import logging
import time
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = Path(__file__).parent.parent.parent / "configs" / "moonshine_config.yaml"


def _load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


class PipelineOrchestrator:
    def __init__(self, config: dict) -> None:
        from audio.wake_word import AudioCapture
        from core.response_handler import ResponseHandler
        from stt.moonshine_stt import MoonShineSTT
        from tts.tts_engine import TTSEngine

        self._capture = AudioCapture(config)
        self._stt = MoonShineSTT(config)
        self._response = ResponseHandler()
        self._tts = TTSEngine(config)

        # Pre-warm MoonShine so the first transcription doesn't pay the
        # ~5–10s lazy-load cost mid-conversation.
        self._stt._load()

    def _speak(self, text: str) -> None:
        """Pause the mic while TTS plays — the I2S card is shared, so
        a live arecord attenuates aplay output."""
        self._capture.pause()
        try:
            self._tts.say(text)
        finally:
            self._capture.resume()

    def run(self) -> None:
        logger.info("Pipeline started.")

        with self._capture:
            self._speak("Hello, I am robot assistant, how can I help?")

            while True:
                logger.info("Listening…")

                # ── 1. Wait for voice, record utterance ───────────────────
                audio = self._capture.record_utterance()
                # Start the "Total" timer AFTER recording so it measures
                # only post-record processing (STT + response + TTS).
                t_rec = time.perf_counter()

                if len(audio) == 0:
                    continue

                # ── 2. Transcribe ─────────────────────────────────────────
                text = self._stt.transcribe(audio)
                t_stt = time.perf_counter()
                logger.info("\033[33mSTT %.3fs: %r\033[0m", t_stt - t_rec, text)

                if not text:
                    logger.info("No speech recognised, back to listening.")
                    continue

                # ── 3. Respond ────────────────────────────────────────────
                reply = self._response.process(text)
                logger.info("Reply: %r", reply)

                # ── 4. Speak ──────────────────────────────────────────────
                self._speak(reply)
                t_end = time.perf_counter()
                logger.info("Total: %.3fs", t_end - t_rec)


def run_moonshine_pipeline(config_path: Path | None = None) -> None:
    config = _load_config(config_path or _DEFAULT_CONFIG)
    pipeline = PipelineOrchestrator(config)
    try:
        pipeline.run()
    except KeyboardInterrupt:
        logger.info("Shutdown.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    run_moonshine_pipeline()

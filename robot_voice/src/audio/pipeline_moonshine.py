"""MoonShine voice pipeline: VAD -> STT -> response -> TTS."""

import logging
import os
from pathlib import Path
import time

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = Path(__file__).parent.parent.parent / "configs" / "moonshine_config.yaml"
_DEFAULT_BOOKING_ROOT = Path.home() / "AppBookingResPi4"


def _load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


class PipelineOrchestrator:
    def __init__(self, config: dict) -> None:
        from audio.wake_word import AudioCapture
        from core.db_worker import DBWorker
        from core.response_handler import ResponseHandler
        from stt.moonshine_stt import MoonShineSTT
        from tts.tts_engine import TTSEngine

        self._capture = AudioCapture(config)
        self._stt = MoonShineSTT(config)
        self._db_worker = None

        lib_path = Path(os.getenv("ROBOT_BOOKING_LIB", str(_DEFAULT_BOOKING_ROOT / "libbooking.so"))).expanduser()
        db_path = Path(os.getenv("ROBOT_BOOKING_DB", str(_DEFAULT_BOOKING_ROOT / "hotel.db"))).expanduser()
        if lib_path.exists():
            try:
                self._db_worker = DBWorker(lib_path, db_path)
            except Exception:
                logger.exception("Booking DB worker disabled")
        else:
            logger.info("Booking DB worker disabled; shared library not found at %s", lib_path)

        self._response = ResponseHandler(db_worker=self._db_worker)
        self._tts = TTSEngine(config)

        self._stt._load()

    def _speak(self, text: str) -> None:
        """Pause the mic while TTS plays because the I2S card is shared."""
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
                logger.info("Listening...")
                audio = self._capture.record_utterance()
                t_rec = time.perf_counter()

                if len(audio) == 0:
                    continue

                text = self._stt.transcribe(audio)
                t_stt = time.perf_counter()
                logger.info("\033[33mSTT %.3fs: %r\033[0m", t_stt - t_rec, text)

                if not text:
                    logger.info("No speech recognised, back to listening.")
                    continue

                reply = self._response.process(text)
                logger.info("Reply: %r", reply)
                self._speak(reply)
                t_end = time.perf_counter()
                logger.info("Total: %.3fs", t_end - t_rec)

    def close(self) -> None:
        if self._db_worker is not None:
            self._db_worker.shutdown()


def run_moonshine_pipeline(config_path: Path | None = None) -> None:
    config = _load_config(config_path or _DEFAULT_CONFIG)
    pipeline = PipelineOrchestrator(config)
    try:
        pipeline.run()
    except KeyboardInterrupt:
        logger.info("Shutdown.")
    finally:
        pipeline.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    run_moonshine_pipeline()

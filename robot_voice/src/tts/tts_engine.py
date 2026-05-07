import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class TTSEngine:
    def __init__(self, config: dict) -> None:
        tts = config.get("tts", {})
        self._voice = tts.get("voice", "en-US-JennyNeural")
        self._rate = tts.get("rate", "-20%")
        self._volume = float(tts.get("volume", 2.0))
        self._device = config.get("audio", {}).get("device", "plughw:2,0")

    def say(self, text: str) -> None:
        logger.info("\033[35m[TTS] %s\033[0m", text)
        asyncio.run(self._speak(text))

    async def _speak(self, text: str) -> None:
        import edge_tts

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            mp3 = Path(f.name)

        try:
            communicate = edge_tts.Communicate(text, self._voice, rate=self._rate)
            await communicate.save(str(mp3))
            # ffmpeg decodes MP3 to s16/22050/mono on stdout, piped to aplay.
            # Matches the loudness of the original two-step path (mpg123 was
            # noticeably quieter) without the intermediate .raw file.
            ff_cmd = ["ffmpeg", "-loglevel", "error", "-i", str(mp3)]
            if abs(self._volume - 1.0) > 1e-3:
                ff_cmd += ["-af", f"volume={self._volume}"]
            ff_cmd += ["-f", "s16le", "-ar", "22050", "-ac", "1", "-"]
            decoder = subprocess.Popen(
                ff_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["aplay", "-q", "-D", self._device,
                 "-f", "S16_LE", "-r", "22050", "-c", "1"],
                stdin=decoder.stdout, stderr=subprocess.DEVNULL,
            )
            decoder.stdout.close()
            decoder.wait()
        except Exception:
            logger.exception("TTS playback failed")
        finally:
            mp3.unlink(missing_ok=True)

import asyncio
import subprocess
import tempfile
from pathlib import Path

from config.settings import Settings

_ALSA_DEVICE = "plughw:2,0"
_VOICE = "en-US-JennyNeural"


class EdgeTTS:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def say(self, text: str) -> None:
        print(f"[TTS] {text}")
        asyncio.run(self._speak(text))

    async def _speak(self, text: str) -> None:
        import edge_tts

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            mp3_path = Path(f.name)

        raw_path = mp3_path.with_suffix(".raw")
        try:
            communicate = edge_tts.Communicate(text, _VOICE, rate="-20%")
            await communicate.save(str(mp3_path))
            subprocess.run(
                ["ffmpeg", "-i", str(mp3_path), "-f", "s16le", "-ar", "22050", "-ac", "1", str(raw_path)],
                stderr=subprocess.DEVNULL, check=True,
            )
            subprocess.run(
                ["aplay", "-D", _ALSA_DEVICE, "-r", "22050", "-f", "S16_LE", "-c", "1", "-q", str(raw_path)],
                stderr=subprocess.DEVNULL,
            )
        finally:
            mp3_path.unlink(missing_ok=True)
            raw_path.unlink(missing_ok=True)

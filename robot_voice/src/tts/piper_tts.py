import subprocess
from pathlib import Path

from config.settings import Settings

_MODELS_DIR = Path(__file__).resolve().parents[2] / "models" / "piper"
_PIPER_BIN = _MODELS_DIR / "piper" / "piper"
_MODEL = _MODELS_DIR / "en_US-lessac-medium.onnx"
_ALSA_DEVICE = "plughw:2,0"
_SAMPLE_RATE = 22050


class PiperTTS:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def say(self, text: str) -> None:
        print(f"[TTS] {text}")
        piper = subprocess.Popen(
            [str(_PIPER_BIN), "--model", str(_MODEL), "--output_raw", "--length_scale", "1.5"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={"LD_LIBRARY_PATH": str(_PIPER_BIN.parent)},
        )
        aplay = subprocess.Popen(
            ["aplay", "-D", _ALSA_DEVICE, "-r", str(_SAMPLE_RATE), "-f", "S16_LE", "-c", "1", "-q"],
            stdin=piper.stdout,
            stderr=subprocess.DEVNULL,
        )
        piper.stdin.write(text.encode())
        piper.stdin.close()
        piper.wait()
        aplay.wait()

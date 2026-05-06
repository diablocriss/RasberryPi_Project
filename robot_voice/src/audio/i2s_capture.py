from collections.abc import Iterator
import subprocess

import numpy as np

from audio.i2s_config import I2SConfig

_HW_RATE = 48000
_HW_CHANNELS = 2
_HW_DEVICE = "plughw:2,0"


class I2SMicrophone:
    def __init__(self, config: I2SConfig | None = None) -> None:
        self.config = config or I2SConfig()
        self._process: subprocess.Popen | None = None
        self._bytes_per_frame = (
            self.config.frames_per_buffer * _HW_CHANNELS * 4  # S32_LE = 4 bytes
        )

    def open(self) -> None:
        self._process = subprocess.Popen(
            [
                "arecord",
                "-D", _HW_DEVICE,
                "-f", "S32_LE",
                "-r", str(_HW_RATE),
                "-c", str(_HW_CHANNELS),
                "-q",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def read(self) -> bytes:
        if self._process is None:
            self.open()
        raw = self._process.stdout.read(self._bytes_per_frame)
        if not raw:
            raise RuntimeError("arecord stream ended unexpectedly")
        return self._convert(raw)

    def _convert(self, raw: bytes) -> bytes:
        """Convert S32_LE 48kHz stereo → S16_LE target-rate mono."""
        samples = np.frombuffer(raw, dtype=np.int32).reshape(-1, _HW_CHANNELS)
        mono = samples[:, 0]
        target_rate = self.config.mic_sample_rate
        if _HW_RATE != target_rate:
            ratio = _HW_RATE // target_rate
            mono = mono[::ratio]
        return (mono >> 16).astype(np.int16).tobytes()

    def frames(self) -> Iterator[bytes]:
        while True:
            yield self.read()

    def close(self) -> None:
        if self._process is not None:
            self._process.terminate()
            self._process.wait()
            self._process = None

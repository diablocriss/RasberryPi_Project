from __future__ import annotations

from utils.audio_utils import rms_int16


class VoiceActivityDetector:
    def __init__(self, threshold: float = 500.0) -> None:
        self.threshold = threshold

    def is_voice(self, pcm: bytes) -> bool:
        return rms_int16(pcm) >= self.threshold


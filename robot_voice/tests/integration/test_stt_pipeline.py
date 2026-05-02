import pytest

from stt.vosk_stt import VoskSTT
from config.settings import Settings


def test_vosk_requires_optional_dependency_when_used():
    stt = VoskSTT(Settings())
    with pytest.raises((RuntimeError, NotImplementedError)):
        stt.transcribe(b"\x00\x00")

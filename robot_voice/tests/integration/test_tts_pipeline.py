from tts.piper_tts import PiperTTS
from config.settings import Settings


def test_piper_placeholder_prints(capsys):
    PiperTTS(Settings()).say("hello")
    assert "hello" in capsys.readouterr().out

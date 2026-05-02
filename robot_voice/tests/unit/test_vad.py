from audio.vad import VoiceActivityDetector


def test_vad_rejects_silence():
    detector = VoiceActivityDetector(threshold=1)
    assert detector.is_voice(b"\x00\x00" * 32) is False


def test_vad_accepts_loud_sample():
    detector = VoiceActivityDetector(threshold=100)
    assert detector.is_voice((1000).to_bytes(2, "little", signed=True) * 32) is True

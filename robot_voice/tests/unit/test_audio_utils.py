from utils.audio_utils import int16_samples, rms_int16


def test_int16_samples():
    assert list(int16_samples((1).to_bytes(2, "little", signed=True))) == [1]


def test_rms_int16_silence():
    assert rms_int16(b"\x00\x00" * 4) == 0.0

from config import settings
from config.settings import Settings


def test_default_uart_port_is_platform_specific(monkeypatch):
    monkeypatch.delenv("ROBOT_UART_PORT", raising=False)
    monkeypatch.setattr(settings.os, "name", "posix")

    assert Settings().uart_port == "/dev/ttyUSB0"

    monkeypatch.setattr(settings.os, "name", "nt")

    assert Settings().uart_port == "COM3"


def test_default_i2s_audio_settings(monkeypatch):
    monkeypatch.delenv("ROBOT_AUDIO_INPUT_DEVICE", raising=False)
    monkeypatch.delenv("ROBOT_AUDIO_OUTPUT_DEVICE", raising=False)
    monkeypatch.delenv("ROBOT_AUDIO_HARDWARE_PROFILE", raising=False)

    current = Settings()

    assert current.audio_input_device == "default"
    assert current.audio_output_device == "default"
    assert current.audio_hardware_profile == "i2s_inmp441_max98357"

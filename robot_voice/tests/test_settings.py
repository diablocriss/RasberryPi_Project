from config import settings
from config.settings import Settings


def test_default_uart_port_is_platform_specific(monkeypatch):
    monkeypatch.delenv("ROBOT_UART_PORT", raising=False)
    monkeypatch.setattr(settings.os, "name", "posix")

    assert Settings().uart_port == "/dev/ttyUSB0"

    monkeypatch.setattr(settings.os, "name", "nt")

    assert Settings().uart_port == "COM3"

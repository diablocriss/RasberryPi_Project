from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    uart_port: str = "COM3"
    uart_baudrate: int = 115200
    language: str = "en"

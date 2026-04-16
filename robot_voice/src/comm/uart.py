from config.settings import Settings


class UartClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, message: str) -> None:
        print(f"UART -> {self.settings.uart_port}: {message}")

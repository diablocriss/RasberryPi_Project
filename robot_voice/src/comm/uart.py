import json
from typing import Any

from config.settings import Settings


class UartClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._serial = None

    def send(self, message: str) -> None:
        print(f"UART -> {self.settings.uart_port}: {message}")

    def send_json(self, command: dict[str, Any]) -> None:
        packet = json.dumps(command, separators=(",", ":")) + "\n"

        if self.settings.dry_run:
            print(f"UART dry-run -> {self.settings.uart_port}: {packet.strip()}")
            return

        serial_port = self._get_serial()
        serial_port.write(packet.encode("utf-8"))
        serial_port.flush()

    def _get_serial(self):
        if self._serial is not None:
            return self._serial

        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("pyserial is required when ROBOT_DRY_RUN=0") from exc

        self._serial = serial.Serial(
            port=self.settings.uart_port,
            baudrate=self.settings.uart_baudrate,
            timeout=self.settings.uart_timeout_s,
        )
        return self._serial

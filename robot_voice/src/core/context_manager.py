from collections import deque
from typing import Any

from config.settings import Settings
from core.command_validator import CommandValidator

Command = dict[str, Any]


class ContextManager:
    def __init__(self, max_history: int = 10) -> None:
        self._history: deque[Command] = deque(maxlen=max_history)
        self._validator = CommandValidator()

    def add_command(self, command: Command) -> None:
        if command:
            self._history.append(dict(command))

    def get_last_command(self) -> Command | None:
        if not self._history:
            return None
        return dict(self._history[-1])

    def get_history(self, n: int = 5) -> list[Command]:
        return [dict(command) for command in list(self._history)[-n:]]

    def handle_contextual(self, text: str, ai_result: Command | None) -> Command | None:
        normalized = " ".join(text.lower().split())

        if "stop" in normalized:
            return {"cmd": "STOP", "reason": "URGENT"}

        last_command = self.get_last_command()
        if last_command and self._is_repeat(normalized):
            return last_command

        if last_command and "faster" in normalized:
            return self._scale_speed(last_command, 1.2)

        if last_command and "slower" in normalized:
            return self._scale_speed(last_command, 0.8)

        return ai_result

    def _is_repeat(self, text: str) -> bool:
        return text in {"again", "repeat", "do that again", "same again"} or "do that again" in text

    def _scale_speed(self, command: Command, multiplier: float) -> Command:
        settings = Settings()
        updated = dict(command)
        current_speed = updated.get("speed", settings.default_speed)
        try:
            updated["speed"] = int(current_speed * multiplier)
        except TypeError:
            updated["speed"] = settings.default_speed
        return self._validator.sanitize(updated)

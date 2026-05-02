from typing import Any

from core.tasx_adapter import MAX_SPEED, MAX_TIME_MS, MIN_SPEED, MIN_TIME_MS, VALID_COMMANDS, VALID_DIRECTIONS

Command = dict[str, Any]


class CommandValidator:
    def validate(self, command: Command) -> tuple[bool, str | None]:
        if not isinstance(command, dict):
            return False, "command must be a JSON object"

        cmd = command.get("cmd")
        if cmd not in VALID_COMMANDS:
            return False, f"unsupported command: {cmd}"

        if cmd in {"MOVE", "TURN"}:
            if command.get("dir") not in VALID_DIRECTIONS:
                return False, "missing or invalid direction"
            if not self._in_range(command.get("speed"), MIN_SPEED, MAX_SPEED):
                return False, "speed outside safe range"
            if not self._in_range(command.get("time_ms"), MIN_TIME_MS, MAX_TIME_MS):
                return False, "time_ms outside safe range"

        if cmd == "SPEED":
            if "delta" in command and not isinstance(command["delta"], int):
                return False, "speed delta must be an integer"
            if "speed" in command and not self._in_range(command["speed"], MIN_SPEED, MAX_SPEED):
                return False, "speed outside safe range"

        return True, None

    def sanitize(self, command: Command) -> Command:
        cmd = command.get("cmd")
        if cmd == "MOVE" or cmd == "TURN":
            return {
                "cmd": cmd,
                "dir": str(command.get("dir", "")).upper(),
                "speed": self._clamp(command.get("speed"), MIN_SPEED, MAX_SPEED, 120),
                "time_ms": self._clamp(command.get("time_ms"), MIN_TIME_MS, MAX_TIME_MS, 1000),
            }
        if cmd == "STOP":
            return {"cmd": "STOP", "reason": str(command.get("reason", "USER_COMMAND"))}
        if cmd == "SPEED":
            if "delta" in command:
                return {"cmd": "SPEED", "delta": self._clamp(command.get("delta"), -255, 255, 0)}
            return {"cmd": "SPEED", "speed": self._clamp(command.get("speed"), MIN_SPEED, MAX_SPEED, 120)}
        return {}

    def _in_range(self, value: Any, min_value: int, max_value: int) -> bool:
        return isinstance(value, int) and min_value <= value <= max_value

    def _clamp(self, value: Any, min_value: int, max_value: int, default: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = default
        return max(min_value, min(number, max_value))

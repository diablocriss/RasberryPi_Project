from typing import Any

from config.settings import Settings

Command = dict[str, Any]

VALID_COMMANDS = {"MOVE", "TURN", "STOP", "SPEED"}
VALID_DIRECTIONS = {"FORWARD", "BACKWARD", "LEFT", "RIGHT"}
MIN_SPEED = 0
MAX_SPEED = 255
MIN_TIME_MS = 100
MAX_TIME_MS = 5000


def adapt_tasx_output(tasx_json: list[dict]) -> Command:
    settings = Settings()
    if not tasx_json:
        return {}

    action = tasx_json[0]
    raw_cmd = str(action.get("cmd", ""))
    if raw_cmd.upper() in VALID_COMMANDS:
        return normalize_parameters(action, settings)

    tasx_cmd = raw_cmd.lower()

    if tasx_cmd == "move_forward":
        return normalize_parameters({"cmd": "MOVE", "dir": "FORWARD"}, settings)
    if tasx_cmd == "move_backward":
        return normalize_parameters({"cmd": "MOVE", "dir": "BACKWARD"}, settings)
    if tasx_cmd == "rotate_left":
        return normalize_parameters({"cmd": "TURN", "dir": "LEFT"}, settings)
    if tasx_cmd == "rotate_right":
        return normalize_parameters({"cmd": "TURN", "dir": "RIGHT"}, settings)
    if tasx_cmd in {"stop", "e_stop"}:
        reason = "EMERGENCY" if tasx_cmd == "e_stop" else "USER_COMMAND"
        return {"cmd": "STOP", "reason": reason}
    if tasx_cmd == "set_speed":
        return _adapt_speed(action, settings)

    return {}


def validate_command(cmd: Command) -> bool:
    if not isinstance(cmd, dict):
        return False

    command = cmd.get("cmd")
    if command not in VALID_COMMANDS:
        return False

    if command in {"MOVE", "TURN"}:
        if cmd.get("dir") not in VALID_DIRECTIONS:
            return False
        if not _int_in_range(cmd.get("speed"), MIN_SPEED, MAX_SPEED):
            return False
        if not _int_in_range(cmd.get("time_ms"), MIN_TIME_MS, MAX_TIME_MS):
            return False

    if command == "SPEED" and "delta" in cmd:
        return isinstance(cmd["delta"], int)

    return True


def normalize_parameters(cmd: Command, settings: Settings | None = None) -> Command:
    settings = settings or Settings()
    normalized = dict(cmd)
    if "cmd" in normalized:
        normalized["cmd"] = str(normalized["cmd"]).upper()
    if "dir" in normalized:
        normalized["dir"] = str(normalized["dir"]).upper()

    if normalized.get("cmd") in {"MOVE", "TURN"}:
        normalized["speed"] = _clamp_int(
            normalized.get("speed", settings.default_speed),
            MIN_SPEED,
            MAX_SPEED,
            settings.default_speed,
        )
        normalized["time_ms"] = _clamp_int(
            normalized.get("time_ms", settings.default_move_time_ms),
            MIN_TIME_MS,
            MAX_TIME_MS,
            settings.default_move_time_ms,
        )

    return normalized


def _adapt_speed(action: Command, settings: Settings) -> Command:
    level = str(action.get("level", "normal")).lower()
    if level == "slow":
        return {"cmd": "SPEED", "delta": -20}
    if level == "fast":
        return {"cmd": "SPEED", "delta": 20}
    return {"cmd": "SPEED", "speed": settings.default_speed}


def _clamp_int(value: Any, min_value: int, max_value: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(min_value, min(number, max_value))


def _int_in_range(value: Any, min_value: int, max_value: int) -> bool:
    return isinstance(value, int) and min_value <= value <= max_value

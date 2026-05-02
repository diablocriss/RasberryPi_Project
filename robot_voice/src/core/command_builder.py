from typing import Any

from config.settings import Settings


def move(direction: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings()
    return {"cmd": "MOVE", "dir": direction, "speed": settings.default_speed, "time_ms": settings.default_move_time_ms}


def turn(direction: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings()
    return {"cmd": "TURN", "dir": direction, "speed": settings.default_speed, "time_ms": settings.default_move_time_ms}


def stop(reason: str = "USER_COMMAND") -> dict[str, Any]:
    return {"cmd": "STOP", "reason": reason}


def speed(delta: int) -> dict[str, Any]:
    return {"cmd": "SPEED", "delta": delta}


def reject(text: str) -> dict[str, Any]:
    return {"cmd": "REJECT", "reason": "UNKNOWN_COMMAND", "text": text}

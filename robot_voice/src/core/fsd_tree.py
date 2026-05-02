from typing import Any

from config.settings import Settings

Command = dict[str, Any]


class FsdTree:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.commands = {
            "forward": "MOVE_FORWARD",
            "backward": "MOVE_BACKWARD",
            "left": "TURN_LEFT",
            "right": "TURN_RIGHT",
            "stop": "STOP",
        }
        self.command_packets: dict[str, Command] = {
            "move forward": self._move("FORWARD"),
            "move foward": self._move("FORWARD"),
            "go forward": self._move("FORWARD"),
            "forward": self._move("FORWARD"),
            "foward": self._move("FORWARD"),
            "move backward": self._move("BACKWARD"),
            "go backward": self._move("BACKWARD"),
            "backward": self._move("BACKWARD"),
            "move left": self._turn("LEFT"),
            "turn left": self._turn("LEFT"),
            "left": self._turn("LEFT"),
            "move right": self._turn("RIGHT"),
            "turn right": self._turn("RIGHT"),
            "right": self._turn("RIGHT"),
            "speed up": {"cmd": "SPEED", "delta": 10},
            "slow down": {"cmd": "SPEED", "delta": -10},
            "emergency stop": {"cmd": "STOP", "reason": "EMERGENCY"},
            "stop": {"cmd": "STOP", "reason": "USER_COMMAND"},
        }

    def resolve(self, text: str) -> str | None:
        normalized = text.lower()
        for keyword, action in self.commands.items():
            if keyword in normalized:
                return action
        return None

    def resolve_command(self, text: str) -> Command | None:
        normalized = " ".join(text.lower().split())
        for phrase, command in self.command_packets.items():
            if phrase in normalized:
                return dict(command)
        return None

    def reject(self, text: str) -> Command:
        return {"cmd": "REJECT", "reason": "UNKNOWN_COMMAND", "text": text}

    def _move(self, direction: str) -> Command:
        return {
            "cmd": "MOVE",
            "dir": direction,
            "speed": self.settings.default_speed,
            "time_ms": self.settings.default_move_time_ms,
        }

    def _turn(self, direction: str) -> Command:
        return {
            "cmd": "TURN",
            "dir": direction,
            "speed": self.settings.default_speed,
            "time_ms": self.settings.default_move_time_ms,
        }

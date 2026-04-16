class FsdTree:
    def __init__(self) -> None:
        self.commands = {
            "forward": "MOVE_FORWARD",
            "backward": "MOVE_BACKWARD",
            "left": "TURN_LEFT",
            "right": "TURN_RIGHT",
            "stop": "STOP",
        }

    def resolve(self, text: str) -> str | None:
        normalized = text.lower()
        for keyword, action in self.commands.items():
            if keyword in normalized:
                return action
        return None

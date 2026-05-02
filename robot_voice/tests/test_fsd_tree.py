from config.settings import Settings
from core.fsd_tree import FsdTree


def test_resolve_all_example_commands():
    tree = FsdTree(Settings())

    cases = {
        "move forward": {"cmd": "MOVE", "dir": "FORWARD", "speed": 120, "time_ms": 1000},
        "move foward": {"cmd": "MOVE", "dir": "FORWARD", "speed": 120, "time_ms": 1000},
        "go forward": {"cmd": "MOVE", "dir": "FORWARD", "speed": 120, "time_ms": 1000},
        "forward": {"cmd": "MOVE", "dir": "FORWARD", "speed": 120, "time_ms": 1000},
        "foward": {"cmd": "MOVE", "dir": "FORWARD", "speed": 120, "time_ms": 1000},
        "move backward": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 120, "time_ms": 1000},
        "go backward": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 120, "time_ms": 1000},
        "backward": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 120, "time_ms": 1000},
        "move left": {"cmd": "TURN", "dir": "LEFT", "speed": 120, "time_ms": 1000},
        "turn left": {"cmd": "TURN", "dir": "LEFT", "speed": 120, "time_ms": 1000},
        "left": {"cmd": "TURN", "dir": "LEFT", "speed": 120, "time_ms": 1000},
        "move right": {"cmd": "TURN", "dir": "RIGHT", "speed": 120, "time_ms": 1000},
        "turn right": {"cmd": "TURN", "dir": "RIGHT", "speed": 120, "time_ms": 1000},
        "right": {"cmd": "TURN", "dir": "RIGHT", "speed": 120, "time_ms": 1000},
        "speed up": {"cmd": "SPEED", "delta": 10},
        "slow down": {"cmd": "SPEED", "delta": -10},
        "emergency stop": {"cmd": "STOP", "reason": "EMERGENCY"},
        "stop": {"cmd": "STOP", "reason": "USER_COMMAND"},
    }

    for text, expected in cases.items():
        assert tree.resolve_command(text) == expected


def test_resolve_move_forward_command():
    tree = FsdTree(Settings())

    command = tree.resolve_command("please move forward")

    assert command == {
        "cmd": "MOVE",
        "dir": "FORWARD",
        "speed": 120,
        "time_ms": 1000,
    }


def test_resolve_stop_command():
    tree = FsdTree(Settings())

    command = tree.resolve_command("stop now")

    assert command == {"cmd": "STOP", "reason": "USER_COMMAND"}


def test_reject_unknown_command():
    tree = FsdTree(Settings())

    rejected = tree.reject("dance")

    assert rejected == {"cmd": "REJECT", "reason": "UNKNOWN_COMMAND", "text": "dance"}

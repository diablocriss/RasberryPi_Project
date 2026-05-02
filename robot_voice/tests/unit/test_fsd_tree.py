from core import command_builder


def test_command_builder_move():
    assert command_builder.move("FORWARD")["cmd"] == "MOVE"


def test_command_builder_stop():
    assert command_builder.stop("EMERGENCY") == {"cmd": "STOP", "reason": "EMERGENCY"}

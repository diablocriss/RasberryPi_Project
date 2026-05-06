from src.core.optimized_pipeline import OptimizedRobotPipeline


def test_common_rule_fixes():
    pipeline = OptimizedRobotPipeline()

    assert pipeline.process("go ahead") == {
        "cmd": "MOVE",
        "dir": "FORWARD",
        "speed": 150,
        "time_ms": 500,
    }
    assert pipeline.process("go back") == {
        "cmd": "MOVE",
        "dir": "BACKWARD",
        "speed": 100,
        "time_ms": 500,
    }
    assert pipeline.process("reverse") == {
        "cmd": "MOVE",
        "dir": "BACKWARD",
        "speed": 100,
        "time_ms": 500,
    }
    assert pipeline.process("halt") == {"cmd": "STOP", "time_ms": 0}
    assert pipeline.process("freeze") == {"cmd": "STOP", "time_ms": 0}


def test_speed_context_adjustments():
    pipeline = OptimizedRobotPipeline()

    assert pipeline.process("go ahead")["speed"] == 150
    assert pipeline.process("faster") == {
        "cmd": "MOVE",
        "dir": "FORWARD",
        "speed": 200,
        "time_ms": 300,
    }
    assert pipeline.process("slow down") == {
        "cmd": "MOVE",
        "dir": "FORWARD",
        "speed": 170,
        "time_ms": 300,
    }


def test_spin_commands_have_meaningful_rotation_time():
    pipeline = OptimizedRobotPipeline()

    assert pipeline.process("spin left")["time_ms"] >= 500
    assert pipeline.process("spin right")["time_ms"] >= 500

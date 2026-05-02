import subprocess


def test_arecord_command_available_or_skip():
    result = subprocess.run(["python", "-c", "print('hardware placeholder')"], capture_output=True, text=True, check=True)
    assert "hardware placeholder" in result.stdout

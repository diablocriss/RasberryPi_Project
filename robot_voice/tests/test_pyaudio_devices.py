import pytest

from audio.pyaudio_devices import device_index


class FakePyAudio:
    def __init__(self, devices):
        self.devices = devices

    def get_device_count(self):
        return len(self.devices)

    def get_device_info_by_index(self, index):
        return self.devices[index]


def test_default_device_uses_pyaudio_default():
    assert device_index(FakePyAudio([]), "default", input_device=True) is None
    assert device_index(FakePyAudio([]), "", input_device=False) is None


def test_input_device_name_matches_capture_device():
    audio = FakePyAudio(
        [
            {"name": "speaker", "maxInputChannels": 0, "maxOutputChannels": 1},
            {"name": "inmp441", "maxInputChannels": 1, "maxOutputChannels": 0},
        ]
    )

    assert device_index(audio, "inmp441", input_device=True) == 1


def test_output_device_name_matches_playback_device():
    audio = FakePyAudio(
        [
            {"name": "inmp441", "maxInputChannels": 1, "maxOutputChannels": 0},
            {"name": "max98357", "maxInputChannels": 0, "maxOutputChannels": 1},
        ]
    )

    assert device_index(audio, "max98357", input_device=False) == 1


def test_wrong_direction_device_is_rejected():
    audio = FakePyAudio([{"name": "max98357", "maxInputChannels": 0, "maxOutputChannels": 1}])

    with pytest.raises(RuntimeError, match="input device not found: max98357"):
        device_index(audio, "max98357", input_device=True)

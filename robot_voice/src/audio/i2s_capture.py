from collections.abc import Iterator

from audio.i2s_config import I2SConfig


class I2SMicrophone:
    def __init__(self, config: I2SConfig | None = None) -> None:
        self.config = config or I2SConfig()
        self._audio = None
        self._stream = None

    def open(self) -> None:
        try:
            import pyaudio
        except ImportError as exc:
            raise RuntimeError("PyAudio is required for I2S microphone capture") from exc

        self._audio = pyaudio.PyAudio()
        self._stream = self._audio.open(
            format=pyaudio.paInt16,
            channels=self.config.channels,
            rate=self.config.mic_sample_rate,
            input=True,
            frames_per_buffer=self.config.frames_per_buffer,
        )

    def read(self) -> bytes:
        if self._stream is None:
            self.open()
        return self._stream.read(self.config.frames_per_buffer, exception_on_overflow=False)

    def frames(self) -> Iterator[bytes]:
        while True:
            yield self.read()

    def close(self) -> None:
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        if self._audio is not None:
            self._audio.terminate()
            self._audio = None

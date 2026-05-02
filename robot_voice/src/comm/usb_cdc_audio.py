from config.settings import Settings

HEADER = b"\xAA\x55"


class FrameError(Exception):
    pass


class UsbCdcAudioReader:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._serial = None

    def read_frame(self) -> bytes:
        serial_port = self._get_serial()
        return read_frame(
            serial_port,
            min_payload_bytes=self.settings.audio_frame_min_bytes,
            max_payload_bytes=self.settings.audio_frame_max_bytes,
        )

    def _get_serial(self):
        if self._serial is not None:
            return self._serial

        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("pyserial is required for USB CDC audio input") from exc

        self._serial = serial.Serial(
            self.settings.audio_cdc_port,
            self.settings.audio_cdc_baudrate,
            timeout=self.settings.audio_cdc_timeout_s,
        )
        return self._serial


def build_packet(data: bytes) -> bytes:
    length = len(data)
    return HEADER + length.to_bytes(2, "little") + data + bytes([compute_checksum(data)])


def compute_checksum(data: bytes) -> int:
    return sum(data) & 0xFF


def verify_checksum(data: bytes, checksum: bytes) -> bool:
    return len(checksum) == 1 and compute_checksum(data) == checksum[0]


def read_frame(stream, min_payload_bytes: int = 1, max_payload_bytes: int = 1024) -> bytes:
    while True:
        _sync_to_header(stream)

        length_bytes = _read_exact(stream, 2)

        length = int.from_bytes(length_bytes, "little")
        if length < min_payload_bytes or length > max_payload_bytes:
            continue

        payload = _read_exact(stream, length)
        checksum = _read_exact(stream, 1)

        if verify_checksum(payload, checksum):
            return payload


def _sync_to_header(stream) -> None:
    matched = 0

    while matched < len(HEADER):
        byte = stream.read(1)
        if not byte:
            raise TimeoutError("Timed out waiting for USB CDC audio frame header")

        if byte == HEADER[matched : matched + 1]:
            matched += 1
            continue

        matched = 1 if byte == HEADER[:1] else 0


def _read_exact(stream, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size

    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            raise TimeoutError("Timed out reading USB CDC audio frame data")
        chunks.append(chunk)
        remaining -= len(chunk)

    return b"".join(chunks)

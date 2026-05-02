from comm.usb_cdc_audio import build_packet, compute_checksum, read_frame, verify_checksum


class ChunkedStream:
    def __init__(self, data: bytes, chunk_size: int = 1) -> None:
        self._data = bytearray(data)
        self._chunk_size = chunk_size

    def read(self, size: int) -> bytes:
        if not self._data:
            return b""
        count = min(size, self._chunk_size, len(self._data))
        result = self._data[:count]
        del self._data[:count]
        return bytes(result)


def test_build_packet_and_read_frame():
    payload = b"\x01\x02\x03\x04"
    stream = ChunkedStream(b"noise" + build_packet(payload), chunk_size=2)

    assert read_frame(stream, min_payload_bytes=1, max_payload_bytes=8) == payload


def test_checksum_helpers():
    payload = b"abc"
    checksum = bytes([compute_checksum(payload)])

    assert verify_checksum(payload, checksum)
    assert not verify_checksum(payload, b"\x00")

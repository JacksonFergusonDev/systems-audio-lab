import numpy as np
import pytest
from sysaudio import config, daq


class FakeSerial:
    """Replays queued responses to each read, recording what was written."""

    def __init__(self, responses: list[bytes]) -> None:
        self.responses = responses
        self.written: list[bytes] = []
        self.resets = 0
        self.is_open = True

    def reset_input_buffer(self) -> None:
        self.resets += 1

    def write(self, data: bytes) -> None:
        self.written.append(data)

    def read(self, n: int) -> bytes:
        return self.responses.pop(0)[:n]

    def close(self) -> None:
        self.is_open = False


def _device(responses: list[bytes]) -> tuple[daq.DAQInterface, FakeSerial]:
    device = daq.DAQInterface()
    fake = FakeSerial(responses)
    device.ser = fake  # type: ignore[assignment]
    return device, fake


def test_capture_burst_decodes_little_endian() -> None:
    samples = np.arange(config.BURST_SAMPLES, dtype="<u2")
    device, fake = _device([samples.tobytes()])

    np.testing.assert_array_equal(device.capture_burst(), samples)
    assert fake.written == [b"s"]


def test_capture_burst_short_read_raises() -> None:
    device, _ = _device([b"\x00" * 10])
    with pytest.raises(OSError, match="Incomplete read"):
        device.capture_burst()


def test_stream_skips_short_read_and_resyncs() -> None:
    block = np.full(config.LIVE_SAMPLES, 7, dtype="<u2").tobytes()
    device, fake = _device([b"\x01" * 5, block])

    chunk = next(device.stream_generator())

    np.testing.assert_array_equal(chunk, 7)
    assert fake.written == [b"v", b"v"]
    assert fake.resets == 2  # once on start, once after the short read


def test_requires_connection() -> None:
    with pytest.raises(AttributeError):
        daq.DAQInterface().capture_burst()

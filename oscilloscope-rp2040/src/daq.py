import serial
import time
import numpy as np
from . import config


class DAQInterface:
    def __init__(self, port=config.SERIAL_PORT, baud=config.BAUD_RATE):
        self.port = port
        self.baud = baud
        self.ser = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=config.TIMEOUT)
            time.sleep(2)  # Allow MCU reset/stabilization
            self.ser.reset_input_buffer()
        except serial.SerialException as e:
            raise IOError(f"Could not connect to DAQ on {self.port}: {e}")

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def capture_burst(self, samples=config.BURST_SAMPLES) -> np.ndarray:
        """
        Sends 's' command, reads binary block, returns uint16 array.
        """
        self.ser.reset_input_buffer()
        self.ser.write(b"s")

        expected_bytes = samples * 2
        raw = self.ser.read(expected_bytes)

        if len(raw) != expected_bytes:
            raise IOError(
                f"Incomplete read: Got {len(raw)} bytes, expected {expected_bytes}"
            )

        return np.frombuffer(raw, dtype="<u2")

    def stream_generator(self, chunk_size=config.LIVE_SAMPLES):
        """
        Yields chunks of data for live plotting.
        """
        self.ser.reset_input_buffer()
        while True:
            self.ser.write(b"v")
            raw = self.ser.read(chunk_size * 2)

            if len(raw) != chunk_size * 2:
                continue

            yield np.frombuffer(raw, dtype="<u2")

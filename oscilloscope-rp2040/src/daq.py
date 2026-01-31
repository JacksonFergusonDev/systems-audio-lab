import time
from typing import Any, Generator, Optional, Type

import numpy as np
import serial

from . import config


class DAQInterface:
    """
    Manages serial communication with the RP2040 data acquisition firmware.

    Implements the context manager protocol for automatic connection handling,
    ensuring resources are released properly.

    Attributes
    ----------
    port : str
        The serial port path (e.g., '/dev/tty.usbmodem...').
    baud : int
        The baud rate for communication.
    ser : Optional[serial.Serial]
        The underlying pySerial object, or None if not connected.
    """

    def __init__(
        self, port: str = config.SERIAL_PORT, baud: int = config.BAUD_RATE
    ) -> None:
        self.port = port
        self.baud = baud
        self.ser: Optional[serial.Serial] = None

    def __enter__(self) -> "DAQInterface":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        self.disconnect()

    def connect(self) -> None:
        """
        Establishes the serial connection and waits for MCU stabilization.

        Raises
        ------
        IOError
            If the serial port cannot be opened or configured.
        """
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=config.TIMEOUT)
            time.sleep(2)  # Allow MCU reset/stabilization
            self.ser.reset_input_buffer()
        except serial.SerialException as e:
            raise IOError(f"Could not connect to DAQ on {self.port}: {e}")

    def disconnect(self) -> None:
        """Closes the serial connection if it is currently open."""
        if self.ser and self.ser.is_open:
            self.ser.close()

    def capture_burst(self, samples: int = config.BURST_SAMPLES) -> np.ndarray:
        """
        Sends the burst command ('s') and retrieves a synchronous block of data.

        Parameters
        ----------
        samples : int, optional
            The number of samples to capture. Defaults to config.BURST_SAMPLES.

        Returns
        -------
        np.ndarray
            (samples,) array of uint16 raw ADC values.

        Raises
        ------
        IOError
            If the number of bytes read does not match the expected count.
        AttributeError
            If the serial connection is not established.
        """
        if self.ser is None:
            raise AttributeError("Serial device not connected.")

        self.ser.reset_input_buffer()
        self.ser.write(b"s")

        expected_bytes = samples * 2
        raw = self.ser.read(expected_bytes)

        if len(raw) != expected_bytes:
            raise IOError(
                f"Incomplete read: Got {len(raw)} bytes, expected {expected_bytes}"
            )

        return np.frombuffer(raw, dtype="<u2")

    def stream_generator(
        self, chunk_size: int = config.LIVE_SAMPLES
    ) -> Generator[np.ndarray, None, None]:
        """
        Yields continuous chunks of data for live plotting or processing.

        Sends the stream command ('v') and enters a loop yielding data blocks.
        The loop continues indefinitely until the generator is closed.

        Parameters
        ----------
        chunk_size : int, optional
            The number of samples per yielded chunk. Defaults to config.LIVE_SAMPLES.

        Yields
        ------
        np.ndarray
            (chunk_size,) array of uint16 raw ADC values.
        """
        if self.ser is None:
            raise AttributeError("Serial device not connected.")

        self.ser.reset_input_buffer()
        while True:
            self.ser.write(b"v")
            raw = self.ser.read(chunk_size * 2)

            if len(raw) != chunk_size * 2:
                continue

            yield np.frombuffer(raw, dtype="<u2")

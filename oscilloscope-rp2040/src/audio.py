import sys
from typing import Any, Optional

import numpy as np

try:
    import sounddevice as sd
except ImportError:
    print("❌ Missing dependency: sounddevice")
    print("   Install via: pip install sounddevice")
    sys.exit(1)


def generate_log_sweep(
    f_start: float, f_end: float, duration: float, fs: int, amp: float
) -> np.ndarray:
    """
    Generates a logarithmic sine sweep array.

    Parameters
    ----------
    f_start : float
        Starting frequency in Hz. Must be > 0.
    f_end : float
        Ending frequency in Hz. Must be > f_start.
    duration : float
        Duration of the sweep in seconds.
    fs : int
        Sampling rate in Hz.
    amp : float
        Peak amplitude (0.0 to 1.0).

    Returns
    -------
    np.ndarray
        (N,) array of float32 samples where N = duration * fs.

    Raises
    ------
    ValueError
        If f_start is not strictly positive or if f_start >= f_end.
    """
    if not (0 < f_start < f_end):
        raise ValueError("Require 0 < f_start < f_end")

    n = int(round(duration * fs))
    t = np.arange(n, dtype=np.float64) / fs

    # Log sweep math: phase(t) = (2*pi*f1/log(R)) * (R^t - 1)
    R = (f_end / f_start) ** (1.0 / duration)
    B = 2.0 * np.pi * f_start / np.log(R)
    phase = B * (R**t - 1.0)

    return (amp * np.sin(phase)).astype(np.float32)


def generate_wave_block(
    shape: str, t: np.ndarray, f_hz: float, amp: float
) -> np.ndarray:
    """
    Stateless waveform generator for block-based processing.

    Parameters
    ----------
    shape : str
        Waveform shape. Options: 'sine', 'square', 'saw', 'triangle', 'noise'.
    t : np.ndarray
        Time array in seconds.
    f_hz : float
        Frequency in Hz.
    amp : float
        Peak amplitude (0.0 to 1.0).

    Returns
    -------
    np.ndarray
        Array of float32 samples with the same shape as t.

    Raises
    ------
    ValueError
        If the shape string is not recognized.
    """
    phase = 2.0 * np.pi * f_hz * t

    if shape == "sine":
        x = np.sin(phase)
    elif shape == "square":
        x = np.sign(np.sin(phase))
    elif shape == "saw":
        x = 2.0 * (t * f_hz - np.floor(0.5 + t * f_hz))
    elif shape == "triangle":
        x = 2.0 * np.abs(2.0 * (t * f_hz - np.floor(t * f_hz + 0.5))) - 1.0
    elif shape == "noise":
        x = np.random.uniform(-1.0, 1.0, size=t.shape[0])
    else:
        raise ValueError(f"Unknown shape: {shape}")

    return (x * amp).astype(np.float32)


class ContinuousOscillator:
    """
    Context manager for infinite audio playback using sounddevice.

    Attributes
    ----------
    shape : str
        Waveform shape ('sine', 'square', etc.).
    freq : float
        Frequency in Hz.
    amp : float
        Amplitude (0.0 to 1.0).
    fs : int
        Sample rate in Hz.
    auto_start : bool
        Whether to start playback immediately upon entering context.
    """

    def __init__(
        self,
        shape: str,
        freq: float,
        amp: float,
        fs: int = 48000,
        auto_start: bool = True,
    ) -> None:
        self.shape = shape
        self.freq = freq
        self.amp = amp
        self.fs = fs
        self.auto_start = auto_start
        self._stream: Optional[sd.OutputStream] = None
        self._start_idx: int = 0

    def _callback(
        self, outdata: np.ndarray, frames: int, time_info: Any, status: Any
    ) -> None:
        """
        Internal sounddevice callback.
        """
        if status:
            print(f"[AudioStatus] {status}")

        t = (self._start_idx + np.arange(frames, dtype=np.float64)) / self.fs
        x = generate_wave_block(self.shape, t, self.freq, self.amp)

        # sounddevice expects (frames, channels)
        outdata[:, 0] = x
        self._start_idx += frames

    def play(self) -> None:
        """Manually start the stream if auto_start was False."""
        if self._stream and self._stream.stopped:
            print(f"🔊 Playing {self.shape} @ {self.freq:.1f}Hz...")
            self._stream.start()

    def __enter__(self) -> "ContinuousOscillator":
        self._stream = sd.OutputStream(
            samplerate=self.fs, channels=1, dtype="float32", callback=self._callback
        )
        if self.auto_start:
            self.play()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
        print("🔇 Audio Stopped.")


def generate_drone(
    duration: float, fs: int, amp: float, freq1: float, freq2: float
) -> np.ndarray:
    """
    Generates a sum of two sines (beats).

    Parameters
    ----------
    duration : float
        Duration in seconds.
    fs : int
        Sampling rate in Hz.
    amp : float
        Combined peak amplitude (0.0 to 1.0).
    freq1 : float
        Frequency of first sine wave in Hz.
    freq2 : float
        Frequency of second sine wave in Hz.

    Returns
    -------
    np.ndarray
        (N,) array of float32 samples.
    """
    t = np.arange(int(duration * fs)) / fs
    wave = np.sin(2 * np.pi * freq1 * t) + np.sin(2 * np.pi * freq2 * t)
    wave = (wave / 2) * amp
    return wave.astype(np.float32)


def generate_pulsing_drone(
    duration: float, fs: int, amp: float, freq: float, pulse_rate: float
) -> np.ndarray:
    """
    Generates a sine wave modulated by a slow sine LFO.

    Parameters
    ----------
    duration : float
        Duration in seconds.
    fs : int
        Sampling rate in Hz.
    amp : float
        Peak amplitude (0.0 to 1.0).
    freq : float
        Carrier frequency in Hz.
    pulse_rate : float
        LFO frequency in Hz (modulation rate).

    Returns
    -------
    np.ndarray
        (N,) array of float32 samples.
    """
    t = np.arange(int(duration * fs)) / fs
    carrier = np.sin(2 * np.pi * freq * t)
    modulator = 0.5 * (1 + np.sin(2 * np.pi * pulse_rate * t - np.pi / 2))
    return (carrier * modulator * amp).astype(np.float32)

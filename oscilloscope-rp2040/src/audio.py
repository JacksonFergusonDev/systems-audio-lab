import numpy as np
import sys

try:
    import sounddevice as sd
except ImportError:
    print("❌ Missing dependency: sounddevice")
    print("   Install via: pip install sounddevice")
    sys.exit(1)


def generate_log_sweep(f_start, f_end, duration, fs, amp):
    """
    Generates a logarithmic sine sweep array.
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
    Context manager for infinite audio playback.
    """

    def __init__(self, shape, freq, amp, fs=48000, auto_start=True):
        self.shape = shape
        self.freq = freq
        self.amp = amp
        self.fs = fs
        self.auto_start = auto_start
        self._stream = None
        self._start_idx = 0

    def _callback(self, outdata, frames, time_info, status):
        if status:
            print(f"[AudioStatus] {status}")

        t = (self._start_idx + np.arange(frames, dtype=np.float64)) / self.fs
        x = generate_wave_block(self.shape, t, self.freq, self.amp)

        # sounddevice expects (frames, channels)
        outdata[:, 0] = x
        self._start_idx += frames

    def play(self):
        """Manually start the stream if auto_start was False."""
        if self._stream and self._stream.stopped:
            print(f"🔊 Playing {self.shape} @ {self.freq:.1f}Hz...")
            self._stream.start()

    def __enter__(self):
        self._stream = sd.OutputStream(
            samplerate=self.fs, channels=1, dtype="float32", callback=self._callback
        )
        if self.auto_start:
            self.play()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._stream:
            self._stream.stop()
            self._stream.close()
        print("🔇 Audio Stopped.")

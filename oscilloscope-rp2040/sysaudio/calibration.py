import json
import os
import time
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import windows

from . import config, daq, dsp


def save_calibration(fs: float) -> None:
    """
    Saves the calibrated sampling rate to the calibration JSON file.

    Creates the parent directory for the calibration file if it does not exist.
    The file will contain the sampling rate, a timestamp, and the hardware default.

    Parameters
    ----------
    fs : float
        The calculated true sampling rate in Hz.
    """
    # 1. Create data directory if it doesn't exist yet
    os.makedirs(os.path.dirname(config.CALIBRATION_FILE_PATH), exist_ok=True)

    data = {
        "fs": fs,
        "timestamp": time.time(),
        "date_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware_default": config.FS_DEFAULT,
    }

    with open(config.CALIBRATION_FILE_PATH, "w") as f:
        json.dump(data, f, indent=4)

    print(f"💾 Calibration saved to {config.CALIBRATION_FILE_PATH}")


def load_calibration() -> Optional[float]:
    """
    Attempts to load a previously saved sampling rate from disk.

    Returns
    -------
    Optional[float]
        The cached sampling rate in Hz if the file exists and is valid.
        Returns None if the file is missing or corrupted.
    """
    if not os.path.exists(config.CALIBRATION_FILE_PATH):
        return None

    try:
        with open(config.CALIBRATION_FILE_PATH, "r") as f:
            data = json.load(f)

        fs = data.get("fs")
        date = data.get("date_str", "unknown date")
        print(f"📂 Loaded cached calibration: {fs:.1f} Hz ({date})")
        return float(fs)

    except Exception as e:
        print(f"⚠️ Could not load calibration: {e}")
        return None


def calibrate_fs_robust(visualize: bool = True) -> float:
    """
    Calculates the true sampling rate by analyzing 60Hz mains hum.

    This function captures a burst of data, identifying the mains frequency
    assuming the user is touching the input jack. It uses a weighted average
    of FFT bins around the peak for sub-bin precision.

    Parameters
    ----------
    visualize : bool, optional

        If True, plots the first few cycles of the
        captured signal for visual verification.

        Default is True.

    Returns
    -------
    float
        The calculated real sampling rate in Hz.
        Returns config.FS_DEFAULT if calibration fails or SNR is too low.
    """
    print("👉 TOUCH JACK TIP NOW for 60Hz Calibration...")

    try:
        # 1. Capture
        with daq.DAQInterface() as device:
            raw = device.capture_burst()
            voltages = dsp.raw_to_volts(raw)

        # 2. AC Couple
        ac_signal = dsp.remove_dc(voltages)

        # 3. FFT Analysis
        n = len(ac_signal)
        windowed = ac_signal * windows.hann(n)
        fft_mag = np.abs(np.fft.fft(windowed)[: n // 2])

        # 4. Find Peak
        peak_idx = np.argmax(fft_mag)
        peak_mag = fft_mag[peak_idx]

        # 5. Calculate SNR (exclude 10 bins around peak)
        noise_mask = np.ones(len(fft_mag), dtype=bool)
        noise_mask[max(0, int(peak_idx) - 5) : min(len(fft_mag), int(peak_idx) + 5)] = (
            False
        )
        noise_floor = np.mean(fft_mag[noise_mask])

        snr = peak_mag / noise_floor if noise_floor > 0 else 0

        print("\n--- DIAGNOSTICS ---")
        print(f"Signal Strength (SNR): {snr:.1f}x noise floor")

        if snr < 10:
            print("❌ WARNING: Signal too weak! Touch the jack firmly.")
            return float(config.FS_DEFAULT)

        # 6. Weighted Average for Precision
        win_idxs = np.arange(peak_idx - 2, peak_idx + 3)
        # Boundary check
        valid_idxs = win_idxs[(win_idxs >= 0) & (win_idxs < len(fft_mag))]

        precise_idx = np.sum(valid_idxs * fft_mag[valid_idxs]) / np.sum(
            fft_mag[valid_idxs]
        )

        # 7. Calculate Real FS: Fs = (Target_Freq * N) / Peak_Index
        real_fs = (60.0 * n) / precise_idx
        print(f"Calculated FS:       {real_fs:.1f} Hz")

        if visualize:
            plt.figure(figsize=(10, 3))
            samples_per_cycle = int(real_fs / 60)
            plt.plot(ac_signal[: samples_per_cycle * 5], color="cyan")
            plt.title("Visual Check: Clean 60Hz Sine Waves?")
            plt.grid(True, alpha=0.3)
            plt.show()

        return float(real_fs)

    except Exception as e:
        print(f"❌ Calibration Failed: {e}")
        return float(config.FS_DEFAULT)

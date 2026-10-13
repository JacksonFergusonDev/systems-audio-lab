import json
import os
import time

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import windows

from . import audio, config, daq, dsp


def save_calibration(fs: float, method: str = "mains_60hz") -> None:
    """
    Save the calibrated sampling rate to the calibration JSON file.

    Creates the parent directory for the calibration file if it does not exist.
    The file will contain the sampling rate, a timestamp, and the hardware default.

    Parameters
    ----------
    fs : float
        The calculated true sampling rate in Hz.
    method : str, optional
        How `fs` was derived (e.g. "mains_60hz", "reference_tone_1000hz").
    """
    # 1. Create data directory if it doesn't exist yet
    os.makedirs(os.path.dirname(config.CALIBRATION_FILE_PATH), exist_ok=True)

    data = {
        "fs": fs,
        "timestamp": time.time(),
        "date_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware_default": config.FS_DEFAULT,
        "method": method,
    }

    with open(config.CALIBRATION_FILE_PATH, "w") as f:
        json.dump(data, f, indent=4)

    print(f"💾 Calibration saved to {config.CALIBRATION_FILE_PATH}")


def load_calibration() -> float | None:
    """
    Load a previously saved sampling rate from disk if available.

    Returns
    -------
    Optional[float]
        The cached sampling rate in Hz if the file exists and is valid.
        Returns None if the file is missing or corrupted.
    """
    if not os.path.exists(config.CALIBRATION_FILE_PATH):
        return None

    try:
        with open(config.CALIBRATION_FILE_PATH) as f:
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
    Calculate the true sampling rate by analyzing 60Hz mains hum.

    Mains hum is a weak reference: the grid wanders by a few hundredths of a
    hertz and a 16k-sample burst holds only ~10 cycles at low SNR. Prefer
    `calibrate_fs_with_tone` when a sound card is available.

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
        peak_idx = int(np.argmax(fft_mag))
        peak_mag = fft_mag[peak_idx]

        # 5. Calculate SNR (exclude 10 bins around peak)
        noise_mask = np.ones(len(fft_mag), dtype=bool)
        noise_mask[max(0, peak_idx - 5) : min(len(fft_mag), peak_idx + 5)] = False
        noise_floor = np.mean(fft_mag[noise_mask])

        # Peak bin vs. mean of all other bins. This includes the FFT's
        # processing gain (~39 dB for 16k points), so it is NOT a time-domain
        # SNR; it only checks that a clear 60 Hz line is present.
        peak_ratio = peak_mag / noise_floor if noise_floor > 0 else 0

        print("\n--- DIAGNOSTICS ---")
        print(f"Spectral peak-to-floor ratio: {peak_ratio:.1f}x (not SNR)")

        if peak_ratio < 10:
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


def fs_from_reference_tone(
    signal_arr: np.ndarray,
    fs_assumed: float,
    f_ref: float,
    n_harmonics: int = 1,
) -> tuple[float, float]:
    """
    Derive the true sampling rate from a capture of a known reference tone.

    If a tone of true frequency `f_ref` measures `f_meas` under an assumed
    rate, the true rate is ``fs_assumed * f_ref / f_meas``. A sound card's
    crystal clock (typically +/-50 ppm) makes its tones a far better reference
    than mains hum.

    Parameters
    ----------
    signal_arr : np.ndarray
        Burst capture of the reference tone.
    fs_assumed : float
        Sampling rate that was assumed when the capture was made.
    f_ref : float
        True frequency of the reference tone in Hz.
    n_harmonics : int, optional
        Harmonics included in the frequency fit (use > 1 for non-sine tones).

    Returns
    -------
    Tuple[float, float]
        (fs_true, std) in Hz, where std propagates the frequency fit's bound.
    """
    f_meas, f_std = dsp.estimate_tone_frequency(
        signal_arr, fs_assumed, f_ref, n_harmonics
    )
    fs_true = fs_assumed * f_ref / f_meas
    return float(fs_true), float(fs_true * f_std / f_meas)


def calibrate_fs_with_tone(
    f_ref: float = 1000.0, amp: float = 0.5, settle_s: float = 0.5
) -> float:
    """
    Calibrate the sampling rate by capturing a sound-card reference tone.

    Plays a sine of `f_ref` through the host audio output (loop it back into
    the DAQ input), captures a burst, and saves the derived rate.

    Parameters
    ----------
    f_ref : float, optional
        Reference tone frequency in Hz.
    amp : float, optional
        Digital amplitude of the tone (0.0 to 1.0).
    settle_s : float, optional
        Seconds to let playback settle before capturing.

    Returns
    -------
    float
        The calibrated sampling rate in Hz.
    """
    with audio.ContinuousOscillator("sine", f_ref, amp):
        time.sleep(settle_s)
        with daq.DAQInterface() as device:
            volts = dsp.raw_to_volts(device.capture_burst())

    fs_true, fs_std = fs_from_reference_tone(volts, config.FS_DEFAULT, f_ref)
    print(f"Calibrated FS: {fs_true:.1f} +/- {fs_std:.1f} Hz (ref {f_ref:.0f} Hz)")
    save_calibration(fs_true, method=f"reference_tone_{f_ref:.0f}hz")
    return fs_true
